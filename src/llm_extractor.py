"""
LLM-powered extraction for ITR Economics data.

Uses Azure OpenAI GPT-4 to intelligently extract structured data
from PDF text, including charts context and tables.
"""

import os
import json
import re
from typing import Optional
from dataclasses import dataclass
import httpx
from datetime import datetime

from .models import Sector, BusinessPhase


@dataclass
class LLMConfig:
    """Configuration for Azure OpenAI."""
    endpoint: str
    api_key: str
    api_version: str = "2025-01-01-preview"
    deployment: str = "gpt-4.1"
    max_tokens: int = 4000
    temperature: float = 0.1  # Low temperature for consistent extraction


class LLMExtractor:
    """LLM-powered extraction for ITR Economics reports."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize with Azure OpenAI configuration."""
        if config:
            self.config = config
        else:
            # Default configuration - requires environment variables
            api_key = os.getenv("AZURE_OPENAI_KEY")
            if not api_key:
                raise ValueError(
                    "AZURE_OPENAI_KEY environment variable is required. "
                    "Set it with: export AZURE_OPENAI_KEY='your-key-here'"
                )
            self.config = LLMConfig(
                endpoint=os.getenv(
                    "AZURE_OPENAI_ENDPOINT",
                    "https://gptproductsearch.openai.azure.com/openai/deployments/gpt-4.1/chat/completions"
                ),
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
            )

        self.client = httpx.Client(timeout=60.0)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make a call to Azure OpenAI."""
        url = f"{self.config.endpoint}?api-version={self.config.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key
        }

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        try:
            response = self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM call error: {e}")
            return ""

    def extract_series_data(self, page_text: str, series_name: str) -> dict:
        """Extract structured series data from page text using LLM."""

        system_prompt = """You are an expert at extracting structured economic data from ITR Economics Trends Reports.
Extract the following information and return it as valid JSON:

1. series_name: The exact name of the economic series
2. unit: The unit of measurement (e.g., "Index, 2017=100", "Billions of Dollars")
3. current_value: The most recent value mentioned
4. current_period: The period for the current value (e.g., "January 2024")
5. current_phase: The current business cycle phase (A, B, C, or D)
6. forecasts: Array of forecast objects with {year, rate_12_12, value_12mma}
7. highlights: Array of key bullet points (max 5)
8. management_objective: The ITR Management Objective text
9. overview: Summary of the OVERVIEW or HIGHLIGHTS section
10. data_trend: Description of the data trend

Return ONLY valid JSON, no markdown formatting or explanation."""

        user_prompt = f"""Extract structured data for the series "{series_name}" from this text:

{page_text[:6000]}

Return JSON with all available fields. Use null for missing values."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            # Clean up response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response as JSON: {response[:200]}")
            return {}

    def extract_forecast_table(self, page_text: str) -> dict:
        """Extract forecast table data using LLM."""

        system_prompt = """You are extracting forecast data from ITR Economics reports.
Find the FORECAST section and extract the yearly forecasts.

Return JSON in this exact format:
{
    "forecasts": [
        {"year": 2024, "rate_12_12": -3.6, "value": 99.2},
        {"year": 2025, "rate_12_12": 2.0, "value": 101.2},
        {"year": 2026, "rate_12_12": 1.7, "value": 102.8}
    ],
    "metric_type": "12MMA" or "12MMT" or "3MMA"
}

The rate_12_12 is the year-over-year percentage change.
The value is the absolute forecast value (12MMA, 12MMT, or 3MMA).
Return ONLY valid JSON."""

        user_prompt = f"""Extract the forecast table from this ITR Economics page:

{page_text[:4000]}

Find the years (2024, 2025, 2026, 2027), their 12/12 rates (percentage), and their forecast values."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {"forecasts": [], "metric_type": "unknown"}

    def extract_at_a_glance(self, page_text: str) -> dict:
        """Extract At-a-Glance summary table data."""

        system_prompt = """You are extracting the At-a-Glance summary from ITR Economics reports.
This is a summary table showing multiple economic series and their business cycle phases.

Return JSON in this format:
{
    "sector": "core" or "financial" or "construction" or "manufacturing",
    "summary_text": "The summary paragraph before the table",
    "series_phases": [
        {
            "series_name": "US Industrial Production",
            "current_phase": "C",
            "forecast_2024": "D",
            "forecast_2025": "A",
            "forecast_2026": "B"
        }
    ]
}

Phases are: A (Recovery), B (Accelerating Growth), C (Slowing Growth), D (Recession)
Return ONLY valid JSON."""

        user_prompt = f"""Extract the At-a-Glance summary data from this page:

{page_text[:5000]}

Include all series mentioned with their current and forecast phases."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def extract_executive_summary(self, text: str) -> dict:
        """Extract and summarize the executive summary."""

        system_prompt = """You are summarizing the Executive Summary from an ITR Economics Trends Report.
Extract and structure the key information.

Return JSON:
{
    "author": "Name of the author",
    "title": "Title like 'One Economy - Two Directions'",
    "key_points": ["Point 1", "Point 2", ...],
    "outlook": {
        "gdp_services": "Outlook description",
        "manufacturing": "Outlook description",
        "employment": "Outlook description"
    },
    "summary": "Brief 2-3 sentence summary of the main message"
}

Return ONLY valid JSON."""

        user_prompt = f"""Summarize this Executive Summary from an ITR Economics report:

{text[:5000]}

Extract the author, key points, and outlook for different sectors."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def describe_chart_context(self, series_name: str, page_text: str, chart_type: str) -> str:
        """Generate a description of what the chart shows."""

        system_prompt = """You are describing economic charts from ITR Economics reports.
Based on the page text and chart type, describe what the chart likely shows.

Be specific about:
- What metrics are displayed
- Time period covered
- Key trends visible
- How to interpret the data

Keep the description to 2-3 sentences."""

        user_prompt = f"""Describe the {chart_type} chart for "{series_name}":

Page context:
{page_text[:3000]}

What does this chart show and what are the key takeaways?"""

        return self._call_llm(system_prompt, user_prompt)

    def interpret_chart_with_vision(self, image_base64: str, series_name: str,
                                    chart_type: str, context: str = "") -> dict:
        """Use GPT-4 Vision to interpret a chart image.

        Args:
            image_base64: Base64-encoded image data
            series_name: Name of the economic series
            chart_type: Type of chart (rate_of_change, data_trend, etc.)
            context: Optional surrounding text context

        Returns:
            Dictionary with interpretation, trends, and insights
        """
        url = f"{self.config.endpoint}?api-version={self.config.api_version}"

        system_prompt = """You are an expert economic analyst interpreting charts from ITR Economics Trends Reports.

Analyze the chart image and provide:
1. A detailed description of what the chart shows
2. The current trend direction (rising, falling, stabilizing)
3. Key inflection points or pattern changes
4. Business cycle phase indication (A=Recovery, B=Accelerating Growth, C=Slowing Growth, D=Recession)
5. Forecast direction if visible
6. Key insights for business planning

Return JSON:
{
    "description": "Detailed description of the chart",
    "trend_direction": "rising/falling/stabilizing/mixed",
    "current_phase": "A/B/C/D or null if unclear",
    "forecast_trend": "improving/declining/stable or null",
    "key_patterns": ["pattern 1", "pattern 2"],
    "business_implications": "What this means for business decisions",
    "confidence": "high/medium/low"
}"""

        user_content = [
            {
                "type": "text",
                "text": f"""Analyze this {chart_type} chart for "{series_name}" from an ITR Economics Trends Report.

{f"Context: {context[:1000]}" if context else ""}

Provide a detailed interpretation of this economic chart."""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}",
                    "detail": "high"
                }
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key
        }

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 1000,
            "temperature": 0.1
        }

        try:
            response = self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse JSON response
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)

            return json.loads(content)

        except json.JSONDecodeError:
            # Return as text interpretation if JSON parsing fails
            return {
                "description": content if 'content' in dir() else "Unable to interpret chart",
                "trend_direction": None,
                "current_phase": None,
                "confidence": "low"
            }
        except Exception as e:
            print(f"Vision interpretation error: {e}")
            return {
                "description": f"Error interpreting chart: {str(e)}",
                "trend_direction": None,
                "current_phase": None,
                "confidence": "low"
            }

    def interpret_image(self, image_base64: str, context: str = "") -> dict:
        """Use GPT-4 Vision to interpret any image from the PDF.

        Args:
            image_base64: Base64-encoded image data
            context: Optional surrounding text context

        Returns:
            Dictionary with interpretation
        """
        url = f"{self.config.endpoint}?api-version={self.config.api_version}"

        system_prompt = """You are analyzing images from ITR Economics Trends Reports.
Describe what you see in the image and explain its relevance to economic analysis.

Return JSON:
{
    "description": "What the image shows",
    "type": "chart/diagram/logo/decorative/infographic",
    "relevance": "How it relates to economic analysis",
    "key_information": ["info 1", "info 2"]
}"""

        user_content = [
            {
                "type": "text",
                "text": f"Describe this image from an ITR Economics report.{f' Context: {context[:500]}' if context else ''}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}",
                    "detail": "auto"
                }
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key
        }

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }

        try:
            response = self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)

            return json.loads(content)

        except Exception as e:
            return {
                "description": f"Unable to interpret image: {str(e)}",
                "type": "unknown",
                "relevance": "unknown"
            }

    def analyze_trends(self, series_data: list[dict]) -> dict:
        """Analyze trends across multiple series."""

        system_prompt = """You are an economic analyst reviewing ITR Economics data.
Analyze the trends across multiple economic series and provide insights.

Return JSON:
{
    "overall_outlook": "Brief overall economic outlook",
    "sectors_in_growth": ["sector names"],
    "sectors_in_decline": ["sector names"],
    "key_indicators": [
        {"indicator": "name", "signal": "positive/negative", "explanation": "why"}
    ],
    "recommendations": ["recommendation 1", "recommendation 2"]
}

Return ONLY valid JSON."""

        # Prepare summary of series data
        summary = []
        for s in series_data[:20]:  # Limit to avoid token limits
            summary.append({
                "name": s.get("series_name"),
                "sector": s.get("sector"),
                "phase": s.get("current_phase"),
                "forecasts": s.get("forecasts", [])[:3]
            })

        user_prompt = f"""Analyze these economic series and provide trend insights:

{json.dumps(summary, indent=2)}

What is the overall economic outlook based on this data?"""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def generate_overall_analysis(
        self,
        document_summary: str,
        sector_summaries: dict,
        page_summaries: list[dict]
    ) -> dict:
        """Generate overall document analysis using LLM.

        Args:
            document_summary: Brief summary of the entire document
            sector_summaries: Dictionary of sector -> summary text
            page_summaries: List of page-level summaries

        Returns:
            Dictionary with executive_summary, key_themes, recommendations
        """
        system_prompt = """You are an expert economic analyst generating an overall analysis
for an ITR Economics Trends Report. Synthesize the provided information into a comprehensive
analysis.

Return JSON:
{
    "executive_summary": "3-5 paragraph executive summary (500-1500 chars)",
    "key_themes": [
        {
            "theme_name": "Short title",
            "significance_score": 1-10,
            "frequency": number,
            "description": "2-3 sentences",
            "affected_sectors": ["sector1", "sector2"],
            "business_implications": "What this means"
        }
    ],
    "cross_sector_trends": {
        "overall_direction": "expanding/contracting/mixed/transitioning",
        "sectors_in_growth": ["sector names"],
        "sectors_in_decline": ["sector names"],
        "trend_summary": "Summary of cross-sector dynamics"
    },
    "recommendations": ["recommendation 1", "recommendation 2", ...]
}"""

        sector_context = "\n".join([
            f"- {sector}: {summary}"
            for sector, summary in sector_summaries.items()
        ])

        user_prompt = f"""Analyze this ITR Economics Trends Report:

Document Summary:
{document_summary}

Sector Summaries:
{sector_context}

Generate a comprehensive overall analysis with executive summary, themes, trends, and recommendations."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def generate_sector_analysis(
        self,
        sector: str,
        series_data: list[dict],
        page_summaries: list[dict]
    ) -> dict:
        """Generate analysis for a specific sector.

        Args:
            sector: Sector name (core, financial, construction, manufacturing)
            series_data: List of series data for this sector
            page_summaries: Page summaries for this sector

        Returns:
            Dictionary with sector analysis fields
        """
        system_prompt = """You are an expert economic analyst generating sector analysis
for an ITR Economics Trends Report.

Return JSON:
{
    "summary": "200-500 character sector summary",
    "dominant_trend": "accelerating/slowing/stable/declining/recovering",
    "leading_indicators": ["indicator1", "indicator2", "indicator3"],
    "key_insights": ["insight 1", "insight 2", ...],
    "business_phase": "A/B/C/D",
    "correlations": [
        {
            "related_sector": "sector name",
            "relationship": "leading/lagging/concurrent",
            "strength": "strong/moderate/weak",
            "description": "Brief explanation"
        }
    ]
}"""

        series_names = [s.get("series_name", "") for s in series_data[:10]]
        summaries_text = "\n".join([
            s.get("summary", "") for s in page_summaries[:5]
        ])

        user_prompt = f"""Analyze the {sector} sector from an ITR Economics Trends Report:

Series in this sector: {', '.join(series_names)}

Page summaries:
{summaries_text[:2500]}

Generate a comprehensive sector analysis."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def calculate_sentiment(
        self,
        sector_analyses: dict,
        chart_interpretations: list[dict]
    ) -> dict:
        """Calculate overall sentiment score using LLM.

        Args:
            sector_analyses: Dictionary of sector -> analysis data
            chart_interpretations: List of chart interpretation data

        Returns:
            Dictionary with sentiment score data
        """
        system_prompt = """You are an expert economic analyst calculating a sentiment score
for an ITR Economics Trends Report.

Use a 5-point scale:
1 = Strongly Bearish (severe recession indicators)
2 = Bearish (decline/contraction)
3 = Neutral (mixed signals)
4 = Bullish (growth/expansion)
5 = Strongly Bullish (strong growth indicators)

Return JSON:
{
    "score": 1-5,
    "confidence": "high/medium/low",
    "contributing_factors": [
        {
            "factor_name": "Factor description",
            "impact": "positive/negative/neutral",
            "weight": 0.0-1.0,
            "description": "Brief explanation"
        }
    ],
    "rationale": "Explanation of the score"
}"""

        sector_context = "\n".join([
            f"- {sector}: {data.get('dominant_trend', 'unknown')} trend, Phase {data.get('business_phase', '?')}"
            for sector, data in sector_analyses.items()
        ])

        trend_context = "\n".join([
            f"- {interp.get('series_name', 'Unknown')}: {interp.get('metadata', {}).get('trend_direction', 'unknown')}"
            for interp in chart_interpretations[:10]
        ])

        user_prompt = f"""Calculate the overall economic sentiment from this data:

Sector Analysis:
{sector_context}

Chart Trends:
{trend_context}

Provide a sentiment score with detailed justification."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return {"score": 3, "confidence": "low", "rationale": "Unable to calculate sentiment"}

    def identify_themes(self, insights: list[str], page_numbers: list[int]) -> list[dict]:
        """Identify recurring themes from document insights.

        Args:
            insights: List of key insights from the document
            page_numbers: List of page numbers where insights were found

        Returns:
            List of theme dictionaries
        """
        if not insights:
            return []

        system_prompt = """You are an economic analyst identifying themes in ITR Economics reports.

For each theme, provide:
- theme_name: Short title (3-5 words)
- significance_score: 1-10 importance
- frequency: Approximate number of related mentions
- description: 2-3 sentence description
- affected_sectors: List of affected sectors
- business_implications: What this means for businesses

Return JSON array of 5-7 themes."""

        user_prompt = f"""Identify key themes from these economic insights:

{chr(10).join(insights[:30])}

Return themes as a JSON array."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            themes = json.loads(response)

            # Add source pages to each theme
            for theme in themes:
                theme["source_pages"] = page_numbers[:5]

            return themes
        except json.JSONDecodeError:
            return []

    def identify_correlations(
        self,
        sector: str,
        series_data: list[dict],
        other_sectors: list[str]
    ) -> list[dict]:
        """Identify correlations between sectors.

        Args:
            sector: Current sector being analyzed
            series_data: Series data for the current sector
            other_sectors: List of other sector names

        Returns:
            List of correlation dictionaries
        """
        system_prompt = """You are an economic analyst identifying correlations between sectors.

Return JSON array of correlations:
[
    {
        "related_sector": "sector name",
        "relationship": "leading/lagging/concurrent",
        "lag_months": number or null,
        "strength": "strong/moderate/weak",
        "description": "Brief explanation"
    }
]"""

        series_names = [s.get("series_name", "") for s in series_data[:5]]

        user_prompt = f"""Identify correlations between the {sector} sector and other sectors.

{sector} sector series: {', '.join(series_names)}
Other sectors: {', '.join(other_sectors)}

Based on typical economic relationships, identify likely correlations."""

        response = self._call_llm(system_prompt, user_prompt)

        try:
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response)
        except json.JSONDecodeError:
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
