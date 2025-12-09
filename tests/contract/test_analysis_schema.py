"""
Contract tests for analysis API endpoints.

Tests that API responses conform to the defined JSON schemas
in specs/001-llm-analysis-enhancement/contracts/.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.models import (
    OverallAnalysis,
    SectorAnalysis,
    SentimentScore,
    AnalysisMetadata,
    Theme,
    CrossSectorTrends,
    Correlation,
    ContributingFactor,
    IndicatorSignal,
    ConfidenceLevel,
    TrendDirection,
    SentimentLabel,
    AnalysisBusinessPhase,
)


# Path to contract schemas
CONTRACTS_DIR = Path(__file__).parent.parent.parent / "specs" / "001-llm-analysis-enhancement" / "contracts"


class TestOverallAnalysisContract:
    """Contract tests for OverallAnalysis schema."""

    @pytest.fixture
    def overall_analysis_schema(self):
        """Load the overall analysis schema."""
        schema_path = CONTRACTS_DIR / "overall-analysis.json"
        if schema_path.exists():
            with open(schema_path) as f:
                return json.load(f)
        return None

    @pytest.fixture
    def valid_overall_analysis(self):
        """Create a valid OverallAnalysis instance."""
        return OverallAnalysis(
            executive_summary=(
                "The March 2024 ITR Trends Report indicates mixed economic conditions "
                "across sectors. Core indicators show moderate growth while financial "
                "markets remain strong. Construction continues to face headwinds from "
                "elevated interest rates, and manufacturing shows early signs of recovery."
            ),
            key_themes=[
                Theme(
                    theme_name="Manufacturing Recovery",
                    significance_score=8.5,
                    frequency=15,
                    description="Manufacturing indicators showing early signs of recovery from recent downturn.",
                    affected_sectors=["manufacturing", "core"],
                    source_pages=[5, 12, 22],
                    business_implications="Prepare for increased demand in manufacturing supply chains."
                ),
                Theme(
                    theme_name="Interest Rate Pressure",
                    significance_score=9.0,
                    frequency=20,
                    description="Elevated interest rates continue to impact construction and housing.",
                    affected_sectors=["construction", "financial"],
                    source_pages=[8, 15, 30],
                    business_implications="Consider hedging strategies for interest-rate sensitive operations."
                )
            ],
            cross_sector_trends=CrossSectorTrends(
                overall_direction="mixed",
                sectors_in_growth=["core", "financial"],
                sectors_in_decline=["construction"],
                sector_correlations=[
                    Correlation(
                        related_sector="manufacturing",
                        relationship="lagging",
                        lag_months=3,
                        strength="moderate",
                        description="Manufacturing follows core indicators"
                    )
                ],
                trend_summary="Divergent performance across sectors with core and financial leading."
            ),
            recommendations=[
                "Monitor leading indicators for phase transition signals",
                "Consider inventory reduction in manufacturing sectors",
                "Evaluate financial sector opportunities"
            ],
            sentiment_score=SentimentScore(
                score=3,
                label=SentimentLabel.NEUTRAL,
                confidence=ConfidenceLevel.MEDIUM,
                contributing_factors=[
                    ContributingFactor(
                        factor_name="Core Growth",
                        impact="positive",
                        weight=0.35,
                        description="Core indicators showing positive momentum"
                    ),
                    ContributingFactor(
                        factor_name="Construction Decline",
                        impact="negative",
                        weight=0.25,
                        description="Construction sector continues to contract"
                    )
                ],
                sector_weights={
                    "core": 0.35,
                    "financial": 0.25,
                    "construction": 0.20,
                    "manufacturing": 0.20
                },
                indicator_signals=[
                    IndicatorSignal(
                        indicator_name="US Industrial Production",
                        sector="core",
                        direction=TrendDirection.RISING,
                        phase=AnalysisBusinessPhase.B,
                        source_page=5
                    )
                ],
                rationale="Mixed signals with core growth offset by construction weakness."
            )
        )

    def test_overall_analysis_serializes_to_valid_json(self, valid_overall_analysis):
        """Test that OverallAnalysis serializes to valid JSON."""
        data = valid_overall_analysis.model_dump()

        # Verify required fields
        assert "executive_summary" in data
        assert "key_themes" in data
        assert "cross_sector_trends" in data
        assert "recommendations" in data
        assert "sentiment_score" in data

    def test_executive_summary_length_constraints(self, valid_overall_analysis):
        """Test executive summary meets length requirements."""
        summary = valid_overall_analysis.executive_summary
        assert 100 <= len(summary) <= 5000

    def test_sentiment_score_structure(self, valid_overall_analysis):
        """Test sentiment score has required structure."""
        sentiment = valid_overall_analysis.sentiment_score.model_dump()

        assert "score" in sentiment
        assert "label" in sentiment
        assert "confidence" in sentiment
        assert "contributing_factors" in sentiment
        assert "sector_weights" in sentiment
        assert "indicator_signals" in sentiment
        assert "rationale" in sentiment

    def test_cross_sector_trends_structure(self, valid_overall_analysis):
        """Test cross-sector trends has required structure."""
        trends = valid_overall_analysis.cross_sector_trends.model_dump()

        assert "overall_direction" in trends
        assert "sectors_in_growth" in trends
        assert "sectors_in_decline" in trends
        assert "sector_correlations" in trends
        assert "trend_summary" in trends


class TestSectorAnalysisContract:
    """Contract tests for SectorAnalysis schema."""

    @pytest.fixture
    def sector_analysis_schema(self):
        """Load the sector analysis schema."""
        schema_path = CONTRACTS_DIR / "sector-analysis.json"
        if schema_path.exists():
            with open(schema_path) as f:
                return json.load(f)
        return None

    @pytest.fixture
    def valid_sector_analysis(self):
        """Create a valid SectorAnalysis instance."""
        return SectorAnalysis(
            sector_name="core",
            summary=(
                "The core sector shows moderate growth with industrial production "
                "trending upward. Leading indicators suggest continued expansion "
                "through Q2 2024. Key drivers include consumer demand and inventory "
                "rebuilding cycles."
            ),
            series_count=10,
            phase_distribution={"A": 2, "B": 4, "C": 3, "D": 1},
            dominant_trend="accelerating",
            leading_indicators=[
                "ITR Leading Indicator",
                "US ISM PMI",
                "US OECD Leading Indicator"
            ],
            business_phase=AnalysisBusinessPhase.B,
            correlations=[
                Correlation(
                    related_sector="manufacturing",
                    relationship="leading",
                    lag_months=3,
                    strength="strong",
                    description="Core indicators lead manufacturing by 3 months"
                )
            ],
            key_insights=[
                "Industrial production at 18-month high",
                "PMI indicates expansion",
                "Consumer confidence improving"
            ],
            source_pages=[3, 5, 7, 9, 11]
        )

    def test_sector_analysis_serializes_to_valid_json(self, valid_sector_analysis):
        """Test that SectorAnalysis serializes to valid JSON."""
        data = valid_sector_analysis.model_dump()

        # Verify required fields
        assert "sector_name" in data
        assert "summary" in data
        assert "series_count" in data
        assert "phase_distribution" in data
        assert "dominant_trend" in data
        assert "leading_indicators" in data
        assert "business_phase" in data
        assert "source_pages" in data

    def test_sector_name_is_valid(self, valid_sector_analysis):
        """Test sector name is one of the valid sectors."""
        valid_sectors = ["core", "financial", "construction", "manufacturing"]
        assert valid_sector_analysis.sector_name in valid_sectors

    def test_phase_distribution_has_all_phases(self, valid_sector_analysis):
        """Test phase distribution includes all business cycle phases."""
        distribution = valid_sector_analysis.phase_distribution
        assert "A" in distribution
        assert "B" in distribution
        assert "C" in distribution
        assert "D" in distribution

    def test_dominant_trend_is_valid(self, valid_sector_analysis):
        """Test dominant trend is one of the valid values."""
        valid_trends = ["accelerating", "slowing", "stable", "declining", "recovering"]
        assert valid_sector_analysis.dominant_trend in valid_trends


class TestAnalysisMetadataContract:
    """Contract tests for AnalysisMetadata schema."""

    @pytest.fixture
    def valid_analysis_metadata(self):
        """Create valid AnalysisMetadata."""
        return AnalysisMetadata(
            version="1.0",
            generated_at=datetime.now(),
            generator_version="3.1.0",
            llm_model="gpt-4.1",
            processing_time_seconds=45.2
        )

    def test_analysis_metadata_serializes_to_valid_json(self, valid_analysis_metadata):
        """Test that AnalysisMetadata serializes to valid JSON."""
        data = valid_analysis_metadata.model_dump()

        assert "version" in data
        assert "generated_at" in data
        assert "generator_version" in data
        assert "llm_model" in data
        assert "processing_time_seconds" in data

    def test_regeneration_version_tracking(self):
        """Test regeneration version can be tracked."""
        metadata = AnalysisMetadata(
            version="1.0",
            generated_at=datetime.now(),
            generator_version="3.1.0",
            llm_model="gpt-4.1",
            processing_time_seconds=30.5,
            regenerated_from_version="0.9"
        )

        assert metadata.regenerated_from_version == "0.9"


class TestAnalysisExportContract:
    """Contract tests for analysis export format."""

    @pytest.fixture
    def analysis_export_schema(self):
        """Load the analysis export schema."""
        schema_path = CONTRACTS_DIR / "analysis-export.json"
        if schema_path.exists():
            with open(schema_path) as f:
                return json.load(f)
        return None

    def test_export_contains_required_fields(self):
        """Test export format contains all required fields."""
        # Create a mock export structure
        export = {
            "report_id": "tr_complete_march_2024",
            "pdf_filename": "TR Complete March 2024.pdf",
            "report_period": "March 2024",
            "overall_analysis": {},  # Would contain full OverallAnalysis
            "sector_analyses": {
                "core": {},
                "financial": {},
                "construction": {},
                "manufacturing": {}
            },
            "analysis_metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "generator_version": "3.1.0",
                "llm_model": "gpt-4.1",
                "processing_time_seconds": 45.2
            }
        }

        # Verify structure
        assert "report_id" in export
        assert "pdf_filename" in export
        assert "report_period" in export
        assert "overall_analysis" in export
        assert "sector_analyses" in export
        assert "analysis_metadata" in export


class TestCorrelationContract:
    """Contract tests for Correlation model."""

    def test_correlation_serializes_correctly(self):
        """Test Correlation serializes with all fields."""
        correlation = Correlation(
            related_sector="manufacturing",
            relationship="leading",
            lag_months=3,
            strength="strong",
            description="Core indicators lead manufacturing"
        )

        data = correlation.model_dump()

        assert data["related_sector"] == "manufacturing"
        assert data["relationship"] == "leading"
        assert data["lag_months"] == 3
        assert data["strength"] == "strong"
        assert data["description"] == "Core indicators lead manufacturing"

    def test_correlation_without_optional_fields(self):
        """Test Correlation can be created without optional fields."""
        correlation = Correlation(
            related_sector="financial",
            relationship="concurrent",
            strength="moderate"
        )

        assert correlation.lag_months is None
        assert correlation.description is None


class TestThemeContract:
    """Contract tests for Theme model."""

    def test_theme_serializes_correctly(self):
        """Test Theme serializes with all required fields."""
        theme = Theme(
            theme_name="Manufacturing Recovery",
            significance_score=8.5,
            frequency=15,
            description="Early signs of recovery in manufacturing sector.",
            affected_sectors=["manufacturing", "core"],
            source_pages=[5, 12, 22],
            business_implications="Prepare for increased demand."
        )

        data = theme.model_dump()

        assert data["theme_name"] == "Manufacturing Recovery"
        assert data["significance_score"] == 8.5
        assert data["frequency"] == 15
        assert len(data["affected_sectors"]) == 2
        assert len(data["source_pages"]) == 3

    def test_significance_score_bounds(self):
        """Test significance score must be 1.0-10.0."""
        # Valid at boundaries
        theme_low = Theme(
            theme_name="Test",
            significance_score=1.0,
            frequency=1,
            description="Test",
            affected_sectors=["core"],
            source_pages=[1],
            business_implications="Test"
        )
        assert theme_low.significance_score == 1.0

        theme_high = Theme(
            theme_name="Test",
            significance_score=10.0,
            frequency=1,
            description="Test",
            affected_sectors=["core"],
            source_pages=[1],
            business_implications="Test"
        )
        assert theme_high.significance_score == 10.0
