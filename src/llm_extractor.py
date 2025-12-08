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

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
