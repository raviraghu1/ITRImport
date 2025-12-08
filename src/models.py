"""
Data models for ITR Economics data extraction.

Per Constitution Principle III (Structured Data Model):
- Time series data with proper date indexing
- Sector/market categorization
- Forecast ranges with confidence bounds
- Rate-of-change metrics as separate fields
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from enum import Enum


class Sector(Enum):
    """ITR Economics report sectors."""
    CORE = "core"
    FINANCIAL = "financial"
    CONSTRUCTION = "construction"
    MANUFACTURING = "manufacturing"


class BusinessPhase(Enum):
    """ITR Business Cycle Phases."""
    PHASE_A = "A"  # Recovery
    PHASE_B = "B"  # Accelerating Growth
    PHASE_C = "C"  # Slowing Growth
    PHASE_D = "D"  # Recession


@dataclass
class SourceMetadata:
    """
    Source traceability metadata.

    Per Constitution Principle II (Source Traceability):
    Every data point must link back to its source.
    """
    pdf_filename: str
    page_number: int
    extraction_timestamp: datetime
    report_period: str  # e.g., "March 2024"

    def to_dict(self) -> dict:
        return {
            "pdf_filename": self.pdf_filename,
            "page_number": self.page_number,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "report_period": self.report_period
        }


@dataclass
class ForecastRange:
    """Forecast with min/max bounds."""
    year: int
    metric_type: str  # "12/12", "12MMA", "12MMT", "3MMA"
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_point: Optional[float] = None  # Single point estimate if no range

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "metric_type": self.metric_type,
            "value_min": self.value_min,
            "value_max": self.value_max,
            "value_point": self.value_point
        }


@dataclass
class EconomicSeries:
    """
    An economic data series from ITR reports.

    Per Constitution Principle I (Data Fidelity):
    Preserve original values, units, and precision.
    """
    series_id: str  # Unique identifier
    series_name: str  # e.g., "US Industrial Production"
    sector: Sector
    unit: str  # e.g., "Index, 2017=100", "Billions of Dollars", "Percent"

    # Current data
    current_value: Optional[float] = None
    current_period: Optional[str] = None  # e.g., "January 2024"

    # Rate of change metrics
    rate_12_12: Optional[float] = None  # 12-month vs year ago
    rate_3_12: Optional[float] = None   # 3-month vs year ago
    rate_1_12: Optional[float] = None   # 1-month vs year ago

    # Business cycle phase
    current_phase: Optional[BusinessPhase] = None
    forecast_phase_2024: Optional[BusinessPhase] = None
    forecast_phase_2025: Optional[BusinessPhase] = None
    forecast_phase_2026: Optional[BusinessPhase] = None

    # Forecasts
    forecasts: list[ForecastRange] = field(default_factory=list)

    # Highlights/key points from the report
    highlights: list[str] = field(default_factory=list)
    management_objective: Optional[str] = None

    # Source tracking
    source: Optional[SourceMetadata] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "series_id": self.series_id,
            "series_name": self.series_name,
            "sector": self.sector.value,
            "unit": self.unit,
            "current_value": self.current_value,
            "current_period": self.current_period,
            "rate_of_change": {
                "12_12": self.rate_12_12,
                "3_12": self.rate_3_12,
                "1_12": self.rate_1_12
            },
            "business_cycle": {
                "current_phase": self.current_phase.value if self.current_phase else None,
                "forecast_2024": self.forecast_phase_2024.value if self.forecast_phase_2024 else None,
                "forecast_2025": self.forecast_phase_2025.value if self.forecast_phase_2025 else None,
                "forecast_2026": self.forecast_phase_2026.value if self.forecast_phase_2026 else None
            },
            "forecasts": [f.to_dict() for f in self.forecasts],
            "highlights": self.highlights,
            "management_objective": self.management_objective,
            "source": self.source.to_dict() if self.source else None
        }


@dataclass
class AtAGlanceSummary:
    """Summary table from At-a-Glance sections."""
    sector: Sector
    report_period: str
    series_phases: dict[str, dict]  # series_name -> {current_phase, forecast_phases}
    source: Optional[SourceMetadata] = None

    def to_dict(self) -> dict:
        return {
            "sector": self.sector.value,
            "report_period": self.report_period,
            "series_phases": self.series_phases,
            "source": self.source.to_dict() if self.source else None
        }
