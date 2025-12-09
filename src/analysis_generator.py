"""
Analysis Generator for ITR Economics Reports.

Orchestrates the generation of overall document analysis and sector-level
analysis using LLM-powered synthesis of extracted data.

Per Constitution Principle II (Source Traceability):
All analysis includes page references back to source data.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from .models import (
    OverallAnalysis,
    SectorAnalysis,
    SentimentScore,
    AnalysisMetadata,
    Theme,
    Correlation,
    CrossSectorTrends,
    ContributingFactor,
    IndicatorSignal,
    ConfidenceLevel,
    TrendDirection,
    SentimentLabel,
    AnalysisBusinessPhase,
)


# Version tracking
__version__ = "3.1.0"

# Configure logging for analysis generation
logger = logging.getLogger(__name__)


class AnalysisGenerationError(Exception):
    """Raised when analysis generation fails."""
    pass


class AnalysisGenerator:
    """
    Orchestrates the generation of overall and sector-level analysis.

    This class aggregates data from the extracted document flow and uses
    LLM to generate comprehensive analysis including executive summaries,
    themes, trends, and sentiment scores.
    """

    SECTORS = ["core", "financial", "construction", "manufacturing"]

    def __init__(self, llm_extractor=None):
        """
        Initialize the analysis generator.

        Args:
            llm_extractor: LLMExtractor instance for generating analysis
        """
        self.llm = llm_extractor
        self.start_time = None
        self._llm_failures = 0  # Track LLM failures for confidence adjustment
        self._partial_analysis = False  # Flag for incomplete analysis

    def generate_analysis(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete analysis for a document.

        Args:
            document: Extracted document flow with series_index and document_flow

        Returns:
            Dictionary containing overall_analysis, sector_analyses, and analysis_metadata
        """
        self.start_time = time.time()
        self._llm_failures = 0
        self._partial_analysis = False

        logger.info("Starting analysis generation for report: %s", document.get("report_id", "unknown"))

        # Validate document structure (T086, T087 - edge case handling)
        validation_result = self._validate_document(document)
        if not validation_result["valid"]:
            logger.warning("Document validation issues: %s", validation_result["issues"])
            self._partial_analysis = True

        # Aggregate data from document
        logger.debug("Aggregating page summaries...")
        page_summaries = self._aggregate_page_summaries(document)
        logger.debug("Found %d page summaries", len(page_summaries))

        logger.debug("Aggregating chart interpretations...")
        chart_interpretations = self._aggregate_chart_interpretations(document)
        logger.debug("Found %d chart interpretations", len(chart_interpretations))

        logger.debug("Grouping series by sector...")
        series_by_sector = self._group_series_by_sector(document)

        # Generate sector analyses first (needed for overall analysis)
        logger.info("Generating sector analyses...")
        sector_start = time.time()
        sector_analyses = self.generate_sector_analyses(
            document, series_by_sector, page_summaries
        )
        sector_time = time.time() - sector_start
        logger.info("Sector analyses completed in %.2fs (%d sectors)", sector_time, len(sector_analyses))

        # Generate overall analysis
        logger.info("Generating overall analysis...")
        overall_start = time.time()
        overall_analysis = self.generate_overall_analysis(
            document, sector_analyses, page_summaries, chart_interpretations
        )
        overall_time = time.time() - overall_start
        logger.info("Overall analysis completed in %.2fs", overall_time)

        # Calculate processing time
        processing_time = time.time() - self.start_time
        logger.info("Total analysis generation time: %.2fs (SC-006 target: <30%% of extraction time)", processing_time)

        # Create metadata
        analysis_metadata = AnalysisMetadata(
            version="1.0",
            generated_at=datetime.now(),
            generator_version=__version__,
            llm_model=self._get_llm_model_name(),
            processing_time_seconds=round(processing_time, 2)
        )

        result = {
            "overall_analysis": overall_analysis.model_dump() if overall_analysis else None,
            "sector_analyses": {
                name: analysis.model_dump()
                for name, analysis in sector_analyses.items()
            } if sector_analyses else {},
            "analysis_metadata": analysis_metadata.model_dump()
        }

        # Log completion status
        if self._llm_failures > 0:
            logger.warning("Analysis completed with %d LLM failures (fallback used)", self._llm_failures)
        if self._partial_analysis:
            logger.warning("Analysis is partial due to document issues")

        return result

    def _validate_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate document structure for analysis (T086, T087).

        Args:
            document: Document to validate

        Returns:
            Dictionary with 'valid' boolean and 'issues' list
        """
        issues = []

        # Check for required fields
        if not document.get("document_flow"):
            issues.append("Missing document_flow")

        if not document.get("series_index"):
            issues.append("Missing series_index")

        # Check for minimum content
        document_flow = document.get("document_flow", [])
        if len(document_flow) == 0:
            issues.append("Empty document_flow - no pages extracted")
        elif len(document_flow) < 5:
            issues.append(f"Very short document ({len(document_flow)} pages) - analysis may be limited")

        # Check for missing pages (gaps in page numbers)
        page_numbers = [p.get("page_number", 0) for p in document_flow if p.get("page_number")]
        if page_numbers:
            expected_pages = set(range(min(page_numbers), max(page_numbers) + 1))
            actual_pages = set(page_numbers)
            missing_pages = expected_pages - actual_pages
            if missing_pages and len(missing_pages) > 2:
                issues.append(f"Missing pages detected: {sorted(missing_pages)[:5]}{'...' if len(missing_pages) > 5 else ''}")

        # Check for series coverage
        series_index = document.get("series_index", {})
        if len(series_index) == 0:
            issues.append("No series data found")

        # Check sector coverage
        sectors_found = set()
        for series_info in series_index.values():
            if series_info.get("sector"):
                sectors_found.add(series_info["sector"])

        missing_sectors = set(self.SECTORS) - sectors_found
        if missing_sectors:
            issues.append(f"Missing sectors: {', '.join(missing_sectors)}")

        # Check for unexpected format (no page summaries)
        pages_with_summaries = sum(1 for p in document_flow if p.get("page_summary"))
        if len(document_flow) > 0 and pages_with_summaries == 0:
            issues.append("No page summaries found - report may be in unexpected format")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def _get_llm_model_name(self) -> str:
        """Get the LLM model name from the extractor."""
        if self.llm and hasattr(self.llm, 'config'):
            return getattr(self.llm.config, 'deployment', 'unknown')
        return "unknown"

    def _aggregate_page_summaries(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Aggregate page summaries from document flow.

        Args:
            document: Extracted document flow

        Returns:
            List of page summaries with page numbers
        """
        summaries = []
        document_flow = document.get("document_flow", [])

        for page in document_flow:
            if page.get("page_summary"):
                summaries.append({
                    "page_number": page.get("page_number"),
                    "page_type": page.get("page_type"),
                    "series_name": page.get("series_name"),
                    "sector": page.get("sector"),
                    "summary": page.get("page_summary"),
                    "key_insights": page.get("key_insights", [])
                })

        return summaries

    def _aggregate_chart_interpretations(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Aggregate chart interpretations from document flow.

        Args:
            document: Extracted document flow

        Returns:
            List of chart interpretations with metadata
        """
        interpretations = []
        document_flow = document.get("document_flow", [])

        for page in document_flow:
            for block in page.get("blocks", []):
                if block.get("block_type") == "chart" and block.get("interpretation"):
                    interpretations.append({
                        "page_number": page.get("page_number"),
                        "series_name": page.get("series_name"),
                        "sector": page.get("sector"),
                        "chart_type": block.get("content", {}).get("chart_type"),
                        "interpretation": block.get("interpretation"),
                        "metadata": block.get("metadata", {})
                    })

        return interpretations

    def _group_series_by_sector(self, document: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group series data by sector.

        Args:
            document: Extracted document flow

        Returns:
            Dictionary mapping sector names to lists of series data
        """
        by_sector = {sector: [] for sector in self.SECTORS}
        series_index = document.get("series_index", {})

        for series_name, series_info in series_index.items():
            sector = series_info.get("sector")
            if sector and sector in by_sector:
                by_sector[sector].append({
                    "series_name": series_name,
                    **series_info
                })

        return by_sector

    def generate_overall_analysis(
        self,
        document: Dict[str, Any],
        sector_analyses: Dict[str, SectorAnalysis],
        page_summaries: List[Dict[str, Any]],
        chart_interpretations: List[Dict[str, Any]]
    ) -> Optional[OverallAnalysis]:
        """
        Generate overall document-level analysis.

        Args:
            document: Extracted document flow
            sector_analyses: Pre-generated sector analyses
            page_summaries: Aggregated page summaries
            chart_interpretations: Aggregated chart interpretations

        Returns:
            OverallAnalysis model or None if generation fails
        """
        if not self.llm:
            return self._generate_fallback_overall_analysis(document, sector_analyses)

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            document, sector_analyses, page_summaries
        )

        # Identify themes
        themes = self._identify_themes(document, page_summaries, chart_interpretations)

        # Generate cross-sector trends
        cross_sector_trends = self._generate_cross_sector_trends(
            sector_analyses, chart_interpretations
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            document, sector_analyses, themes
        )

        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment_score(
            sector_analyses, themes, chart_interpretations
        )

        try:
            return OverallAnalysis(
                executive_summary=executive_summary,
                key_themes=themes,
                cross_sector_trends=cross_sector_trends,
                recommendations=recommendations,
                sentiment_score=sentiment_score
            )
        except Exception as e:
            print(f"Error creating OverallAnalysis: {e}")
            return self._generate_fallback_overall_analysis(document, sector_analyses)

    def _generate_fallback_overall_analysis(
        self,
        document: Dict[str, Any],
        sector_analyses: Dict[str, SectorAnalysis]
    ) -> OverallAnalysis:
        """Generate a basic overall analysis without LLM."""
        report_period = document.get("report_period", "Unknown Period")
        sectors_covered = document.get("metadata", {}).get("sectors_covered", [])

        # Create minimal required structures
        executive_summary = (
            f"This ITR Trends Report for {report_period} covers economic analysis across "
            f"{len(sectors_covered)} sectors: {', '.join(sectors_covered) if sectors_covered else 'various sectors'}. "
            f"The report contains {document.get('metadata', {}).get('total_pages', 0)} pages with "
            f"{len(document.get('series_index', {}))} economic series analyzed."
        )

        # Ensure minimum length
        if len(executive_summary) < 100:
            executive_summary += " Please refer to individual sector analyses for detailed insights."

        cross_sector_trends = CrossSectorTrends(
            overall_direction="mixed",
            sectors_in_growth=[],
            sectors_in_decline=[],
            sector_correlations=[],
            trend_summary="Cross-sector analysis requires LLM processing for detailed insights."
        )

        sentiment_score = SentimentScore(
            score=3,
            label=SentimentLabel.NEUTRAL,
            confidence=ConfidenceLevel.LOW,
            contributing_factors=[],
            sector_weights={s: 0.25 for s in self.SECTORS},
            indicator_signals=[],
            rationale="Sentiment analysis requires LLM processing for accurate assessment."
        )

        return OverallAnalysis(
            executive_summary=executive_summary,
            key_themes=[],
            cross_sector_trends=cross_sector_trends,
            recommendations=["Review individual sector analyses for detailed insights."],
            sentiment_score=sentiment_score
        )

    def generate_sector_analyses(
        self,
        document: Dict[str, Any],
        series_by_sector: Dict[str, List[Dict[str, Any]]],
        page_summaries: List[Dict[str, Any]]
    ) -> Dict[str, SectorAnalysis]:
        """
        Generate analysis for each sector.

        Args:
            document: Extracted document flow
            series_by_sector: Series data grouped by sector
            page_summaries: Aggregated page summaries

        Returns:
            Dictionary mapping sector names to SectorAnalysis models
        """
        sector_analyses = {}

        for sector in self.SECTORS:
            series_list = series_by_sector.get(sector, [])
            if not series_list:
                continue

            sector_summaries = [
                s for s in page_summaries
                if s.get("sector") == sector
            ]

            analysis = self._generate_single_sector_analysis(
                sector, series_list, sector_summaries, document
            )
            if analysis:
                sector_analyses[sector] = analysis

        return sector_analyses

    def _generate_single_sector_analysis(
        self,
        sector: str,
        series_list: List[Dict[str, Any]],
        sector_summaries: List[Dict[str, Any]],
        document: Dict[str, Any]
    ) -> Optional[SectorAnalysis]:
        """Generate analysis for a single sector."""
        # Calculate phase distribution
        phase_distribution = self._calculate_phase_distribution(series_list, document)

        # Determine dominant trend and business phase
        dominant_trend, business_phase = self._determine_dominant_trend(phase_distribution)

        # Get source pages
        source_pages = self._extract_sector_source_pages(sector, document)

        # Generate summary using LLM or fallback
        if self.llm:
            summary = self._generate_sector_summary_llm(
                sector, series_list, sector_summaries
            )
            leading_indicators = self._identify_leading_indicators(
                sector, series_list, document
            )
            key_insights = self._extract_sector_insights(sector_summaries)
            correlations = self._identify_sector_correlations(sector, document)
        else:
            summary = self._generate_sector_summary_fallback(sector, series_list)
            leading_indicators = [s["series_name"] for s in series_list[:3]]
            key_insights = []
            correlations = []

        # Ensure summary meets minimum length
        if len(summary) < 50:
            summary = f"The {sector} sector contains {len(series_list)} economic series. {summary}"

        try:
            return SectorAnalysis(
                sector_name=sector,
                summary=summary,
                series_count=len(series_list),
                phase_distribution=phase_distribution,
                dominant_trend=dominant_trend,
                leading_indicators=leading_indicators,
                business_phase=business_phase,
                correlations=correlations,
                key_insights=key_insights,
                source_pages=source_pages
            )
        except Exception as e:
            print(f"Error creating SectorAnalysis for {sector}: {e}")
            return None

    def _calculate_phase_distribution(
        self,
        series_list: List[Dict[str, Any]],
        document: Dict[str, Any]
    ) -> Dict[str, int]:
        """Calculate the distribution of business cycle phases in a sector."""
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0}

        # Look through document_flow for phase information
        document_flow = document.get("document_flow", [])
        for page in document_flow:
            for block in page.get("blocks", []):
                metadata = block.get("metadata", {})
                phase = metadata.get("current_phase")
                if phase and phase in distribution:
                    distribution[phase] += 1

        # If no phases found, distribute evenly
        if sum(distribution.values()) == 0:
            count = len(series_list)
            distribution = {"A": count // 4, "B": count // 4, "C": count // 4, "D": count // 4}

        return distribution

    def _determine_dominant_trend(
        self, phase_distribution: Dict[str, int]
    ) -> tuple[str, AnalysisBusinessPhase]:
        """Determine the dominant trend and phase from distribution."""
        total = sum(phase_distribution.values())
        if total == 0:
            return "stable", AnalysisBusinessPhase.C

        # Find dominant phase
        dominant_phase = max(phase_distribution, key=phase_distribution.get)

        # Map phases to trends
        phase_trends = {
            "A": "recovering",
            "B": "accelerating",
            "C": "slowing",
            "D": "declining"
        }

        trend = phase_trends.get(dominant_phase, "stable")
        business_phase = AnalysisBusinessPhase(dominant_phase)

        return trend, business_phase

    def _extract_sector_source_pages(
        self, sector: str, document: Dict[str, Any]
    ) -> List[int]:
        """Extract page numbers containing sector data."""
        pages = []
        document_flow = document.get("document_flow", [])

        for page in document_flow:
            if page.get("sector") == sector:
                pages.append(page.get("page_number", 0))

        return sorted(list(set(pages)))

    def _generate_sector_summary_llm(
        self,
        sector: str,
        series_list: List[Dict[str, Any]],
        sector_summaries: List[Dict[str, Any]]
    ) -> str:
        """Generate sector summary using LLM."""
        # Prepare context
        series_names = [s["series_name"] for s in series_list]
        summaries_text = "\n".join([
            s.get("summary", "") for s in sector_summaries
        ])

        prompt = f"""Summarize the {sector} sector from an ITR Economics Trends Report.

Series in this sector: {', '.join(series_names)}

Page summaries:
{summaries_text[:3000]}

Provide a concise summary (200-500 characters) covering:
1. Current economic status
2. Key trends
3. Business implications

Return only the summary text, no formatting."""

        try:
            summary = self.llm._call_llm(
                "You are an expert economic analyst summarizing ITR Economics reports.",
                prompt
            )
            return summary.strip()
        except Exception as e:
            self._llm_failures += 1
            logger.warning("LLM failure generating %s sector summary: %s (using fallback)", sector, str(e))
            return self._generate_sector_summary_fallback(sector, series_list)

    def _generate_sector_summary_fallback(
        self, sector: str, series_list: List[Dict[str, Any]]
    ) -> str:
        """Generate basic sector summary without LLM."""
        series_names = [s["series_name"] for s in series_list[:3]]
        return (
            f"The {sector} sector analysis covers {len(series_list)} economic series "
            f"including {', '.join(series_names)}. Detailed analysis requires LLM processing."
        )

    def _identify_leading_indicators(
        self,
        sector: str,
        series_list: List[Dict[str, Any]],
        document: Dict[str, Any]
    ) -> List[str]:
        """Identify leading indicators for a sector."""
        # Known leading indicators by sector
        leading_by_sector = {
            "core": ["ITR Leading Indicator", "US ISM PMI", "US OECD Leading Indicator"],
            "financial": ["US Stock Prices", "US Government Bond Yields"],
            "construction": ["US Single-Unit Housing Starts", "US Multi-Unit Housing Starts"],
            "manufacturing": ["US Metalworking Machinery", "US Machinery New Orders"]
        }

        known_leading = leading_by_sector.get(sector, [])
        series_names = [s["series_name"] for s in series_list]

        # Return matching leading indicators
        indicators = [name for name in known_leading if name in series_names]

        # If no matches, return first 3 series
        if not indicators:
            indicators = series_names[:3]

        return indicators[:3]

    def _extract_sector_insights(
        self, sector_summaries: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key insights from sector summaries."""
        insights = []
        for summary in sector_summaries:
            insights.extend(summary.get("key_insights", []))
        return insights[:5]

    def _identify_sector_correlations(
        self, sector: str, document: Dict[str, Any]
    ) -> List[Correlation]:
        """Identify correlations between this sector and others."""
        # Pre-defined correlations based on economic relationships
        known_correlations = {
            "core": [
                Correlation(
                    related_sector="manufacturing",
                    relationship="leading",
                    lag_months=3,
                    strength="strong",
                    description="Core indicators lead manufacturing activity"
                )
            ],
            "financial": [
                Correlation(
                    related_sector="core",
                    relationship="leading",
                    lag_months=6,
                    strength="moderate",
                    description="Financial markets anticipate economic trends"
                )
            ],
            "construction": [
                Correlation(
                    related_sector="financial",
                    relationship="lagging",
                    lag_months=9,
                    strength="moderate",
                    description="Construction follows interest rate changes"
                )
            ],
            "manufacturing": [
                Correlation(
                    related_sector="core",
                    relationship="lagging",
                    lag_months=3,
                    strength="strong",
                    description="Manufacturing responds to overall economic conditions"
                )
            ]
        }

        return known_correlations.get(sector, [])

    def _generate_executive_summary(
        self,
        document: Dict[str, Any],
        sector_analyses: Dict[str, SectorAnalysis],
        page_summaries: List[Dict[str, Any]]
    ) -> str:
        """Generate executive summary using LLM."""
        report_period = document.get("report_period", "Unknown Period")

        # Prepare sector summary context
        sector_context = "\n".join([
            f"- {name}: {analysis.summary}"
            for name, analysis in sector_analyses.items()
        ])

        prompt = f"""Write an executive summary for the ITR Trends Report for {report_period}.

Sector Summaries:
{sector_context}

Write a 3-5 paragraph executive summary (500-1500 characters) that:
1. Opens with the overall economic outlook
2. Highlights key trends across sectors
3. Notes any divergences or significant patterns
4. Concludes with implications for business planning

Return only the summary text, no formatting."""

        try:
            summary = self.llm._call_llm(
                "You are an expert economic analyst writing executive summaries for ITR Economics reports.",
                prompt
            )
            return summary.strip()
        except Exception as e:
            self._llm_failures += 1
            logger.warning("LLM failure generating executive summary: %s (using fallback)", str(e))
            return f"ITR Trends Report for {report_period} provides economic analysis across {len(sector_analyses)} sectors."

    def _identify_themes(
        self,
        document: Dict[str, Any],
        page_summaries: List[Dict[str, Any]],
        chart_interpretations: List[Dict[str, Any]]
    ) -> List[Theme]:
        """Identify recurring themes across the document."""
        if not self.llm:
            return []

        # Collect all insights
        all_insights = []
        all_pages = set()

        for summary in page_summaries:
            all_insights.extend(summary.get("key_insights", []))
            if summary.get("page_number"):
                all_pages.add(summary["page_number"])

        if not all_insights:
            return []

        prompt = f"""Identify 5-7 key themes from these economic insights:

{chr(10).join(all_insights[:30])}

For each theme, provide:
1. theme_name: Short title (3-5 words)
2. significance_score: 1-10 importance
3. frequency: Approximate number of mentions
4. description: 2-3 sentence description
5. affected_sectors: List of affected sectors
6. business_implications: What this means for businesses

Return JSON array of themes."""

        try:
            response = self.llm._call_llm(
                "You are an economic analyst identifying themes in ITR Economics reports.",
                prompt
            )

            # Parse response
            import json
            import re

            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            themes_data = json.loads(response)

            themes = []
            for t in themes_data[:7]:
                try:
                    theme = Theme(
                        theme_name=t.get("theme_name", "Unknown Theme"),
                        significance_score=float(t.get("significance_score", 5.0)),
                        frequency=int(t.get("frequency", 1)),
                        description=t.get("description", ""),
                        affected_sectors=t.get("affected_sectors", []),
                        source_pages=list(all_pages)[:5],
                        business_implications=t.get("business_implications", "")
                    )
                    themes.append(theme)
                except Exception:
                    continue

            return themes

        except Exception as e:
            self._llm_failures += 1
            logger.warning("LLM failure identifying themes: %s (returning empty themes)", str(e))
            return []

    def _generate_cross_sector_trends(
        self,
        sector_analyses: Dict[str, SectorAnalysis],
        chart_interpretations: List[Dict[str, Any]]
    ) -> CrossSectorTrends:
        """Generate cross-sector trend analysis."""
        sectors_in_growth = []
        sectors_in_decline = []

        for name, analysis in sector_analyses.items():
            if analysis.dominant_trend in ["recovering", "accelerating"]:
                sectors_in_growth.append(name)
            elif analysis.dominant_trend in ["declining", "slowing"]:
                sectors_in_decline.append(name)

        # Determine overall direction
        if len(sectors_in_growth) > len(sectors_in_decline):
            overall_direction = "expanding"
        elif len(sectors_in_decline) > len(sectors_in_growth):
            overall_direction = "contracting"
        else:
            overall_direction = "mixed"

        # Collect correlations
        all_correlations = []
        for analysis in sector_analyses.values():
            all_correlations.extend(analysis.correlations)

        trend_summary = (
            f"The economy shows {overall_direction} conditions with "
            f"{len(sectors_in_growth)} sectors in growth phases and "
            f"{len(sectors_in_decline)} sectors in decline phases."
        )

        return CrossSectorTrends(
            overall_direction=overall_direction,
            sectors_in_growth=sectors_in_growth,
            sectors_in_decline=sectors_in_decline,
            sector_correlations=all_correlations[:5],
            trend_summary=trend_summary
        )

    def _generate_recommendations(
        self,
        document: Dict[str, Any],
        sector_analyses: Dict[str, SectorAnalysis],
        themes: List[Theme]
    ) -> List[str]:
        """Generate actionable recommendations."""
        if not self.llm:
            return ["Review individual sector analyses for detailed recommendations."]

        sector_context = "\n".join([
            f"- {name}: {analysis.dominant_trend} trend, Phase {analysis.business_phase.value}"
            for name, analysis in sector_analyses.items()
        ])

        theme_context = "\n".join([
            f"- {t.theme_name}: {t.business_implications}"
            for t in themes[:5]
        ])

        prompt = f"""Generate 3-5 actionable business recommendations based on:

Sector Trends:
{sector_context}

Key Themes:
{theme_context}

Provide specific, actionable recommendations for business planning.
Return as a JSON array of strings."""

        try:
            response = self.llm._call_llm(
                "You are a business strategy advisor providing recommendations based on ITR Economics analysis.",
                prompt
            )

            import json
            import re

            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            recommendations = json.loads(response)
            return recommendations[:5]

        except Exception as e:
            self._llm_failures += 1
            logger.warning("LLM failure generating recommendations: %s (using fallback)", str(e))
            return ["Monitor leading indicators for phase transition signals."]

    def _calculate_sentiment_score(
        self,
        sector_analyses: Dict[str, SectorAnalysis],
        themes: List[Theme],
        chart_interpretations: List[Dict[str, Any]]
    ) -> SentimentScore:
        """Calculate overall sentiment score."""
        # Calculate sector weights based on series count
        total_series = sum(a.series_count for a in sector_analyses.values())
        if total_series == 0:
            sector_weights = {s: 0.25 for s in self.SECTORS}
        else:
            sector_weights = {
                name: round(analysis.series_count / total_series, 2)
                for name, analysis in sector_analyses.items()
            }
            # Ensure weights sum to 1.0
            total = sum(sector_weights.values())
            if total > 0:
                sector_weights = {k: round(v / total, 2) for k, v in sector_weights.items()}

        # Calculate score based on sector trends
        trend_scores = {
            "recovering": 4,
            "accelerating": 5,
            "stable": 3,
            "slowing": 2,
            "declining": 1
        }

        weighted_score = 0
        for name, analysis in sector_analyses.items():
            weight = sector_weights.get(name, 0.25)
            trend_score = trend_scores.get(analysis.dominant_trend, 3)
            weighted_score += weight * trend_score

        # Round to nearest integer (1-5)
        final_score = max(1, min(5, round(weighted_score)))

        # Map score to label
        score_labels = {
            1: SentimentLabel.STRONGLY_BEARISH,
            2: SentimentLabel.BEARISH,
            3: SentimentLabel.NEUTRAL,
            4: SentimentLabel.BULLISH,
            5: SentimentLabel.STRONGLY_BULLISH
        }

        # Build contributing factors
        contributing_factors = []
        for name, analysis in sector_analyses.items():
            impact = "positive" if analysis.dominant_trend in ["recovering", "accelerating"] else \
                     "negative" if analysis.dominant_trend in ["declining", "slowing"] else "neutral"
            contributing_factors.append(ContributingFactor(
                factor_name=f"{name.title()} Sector Trend",
                impact=impact,
                weight=sector_weights.get(name, 0.25),
                description=f"{name.title()} sector showing {analysis.dominant_trend} trend"
            ))

        # Build indicator signals
        indicator_signals = []
        for interp in chart_interpretations[:10]:
            direction = interp.get("metadata", {}).get("trend_direction")
            if direction:
                try:
                    indicator_signals.append(IndicatorSignal(
                        indicator_name=interp.get("series_name", "Unknown"),
                        sector=interp.get("sector", "core"),
                        direction=TrendDirection(direction),
                        source_page=interp.get("page_number", 1)
                    ))
                except Exception:
                    continue

        # Determine confidence (T084 - mark as LOW when partial)
        if self._partial_analysis or self._llm_failures > 2:
            confidence = ConfidenceLevel.LOW
        elif len(sector_analyses) >= 3 and self._llm_failures == 0:
            confidence = ConfidenceLevel.HIGH
        elif len(sector_analyses) >= 2:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # Generate rationale
        sectors_summary = ", ".join([
            f"{name} ({analysis.dominant_trend})"
            for name, analysis in sector_analyses.items()
        ])
        rationale = f"Sentiment based on analysis of {len(sector_analyses)} sectors: {sectors_summary}."

        return SentimentScore(
            score=final_score,
            label=score_labels[final_score],
            confidence=confidence,
            contributing_factors=contributing_factors,
            sector_weights=sector_weights,
            indicator_signals=indicator_signals,
            rationale=rationale
        )

    def regenerate_analysis(
        self, existing_document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Regenerate analysis from existing extracted data.

        Args:
            existing_document: Document with document_flow and series_index

        Returns:
            New analysis data with updated metadata
        """
        # Store previous version
        previous_version = None
        if "analysis_metadata" in existing_document:
            previous_version = existing_document["analysis_metadata"].get("version")

        # Generate new analysis
        result = self.generate_analysis(existing_document)

        # Mark as regeneration
        if previous_version:
            result["analysis_metadata"]["regenerated_from_version"] = previous_version

        return result

    def export_analysis(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export analysis in standardized format for downstream use.

        Args:
            document: Complete document with analysis

        Returns:
            Export-formatted analysis dictionary
        """
        return {
            "report_id": document.get("report_id"),
            "pdf_filename": document.get("pdf_filename"),
            "report_period": document.get("report_period"),
            "overall_analysis": document.get("overall_analysis"),
            "sector_analyses": document.get("sector_analyses"),
            "analysis_metadata": document.get("analysis_metadata")
        }
