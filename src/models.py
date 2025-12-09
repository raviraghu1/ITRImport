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
from typing import Optional, List, Dict
from enum import Enum

from pydantic import BaseModel, Field, field_validator


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


# =============================================================================
# Analysis Models (Pydantic) - T004-T013
# =============================================================================

class ConfidenceLevel(str, Enum):
    """Confidence level for analysis results."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TrendDirection(str, Enum):
    """Direction of economic trend."""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class SentimentLabel(str, Enum):
    """5-point sentiment scale labels."""
    STRONGLY_BEARISH = "Strongly Bearish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    BULLISH = "Bullish"
    STRONGLY_BULLISH = "Strongly Bullish"


class AnalysisBusinessPhase(str, Enum):
    """Business cycle phase for analysis models."""
    A = "A"  # Recovery
    B = "B"  # Accelerating Growth
    C = "C"  # Slowing Growth
    D = "D"  # Recession


class ContributingFactor(BaseModel):
    """A factor that influenced the sentiment score."""
    factor_name: str
    impact: str = Field(description="positive, negative, or neutral")
    weight: float = Field(ge=0.0, le=1.0)
    description: str


class IndicatorSignal(BaseModel):
    """Individual economic indicator direction signal."""
    indicator_name: str
    sector: str
    direction: TrendDirection
    phase: Optional[AnalysisBusinessPhase] = None
    source_page: int


class Correlation(BaseModel):
    """Relationship between economic sectors or indicators."""
    related_sector: str
    relationship: str = Field(description="leading, lagging, or concurrent")
    lag_months: Optional[int] = None
    strength: str = Field(description="strong, moderate, or weak")
    description: Optional[str] = None


class Theme(BaseModel):
    """A recurring economic topic identified across the report."""
    theme_name: str
    significance_score: float = Field(ge=1.0, le=10.0)
    frequency: int = Field(ge=1)
    description: str
    affected_sectors: List[str]
    source_pages: List[int]
    business_implications: str


class SentimentScore(BaseModel):
    """5-point economic sentiment classification with structured context."""
    score: int = Field(ge=1, le=5)
    label: SentimentLabel
    confidence: ConfidenceLevel
    contributing_factors: List[ContributingFactor]
    sector_weights: Dict[str, float]
    indicator_signals: List[IndicatorSignal]
    rationale: str

    @field_validator('sector_weights')
    @classmethod
    def weights_sum_to_one(cls, v):
        if not v:
            return v
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f'sector_weights must sum to 1.0, got {total}')
        return v

    @field_validator('label')
    @classmethod
    def label_matches_score(cls, v, info):
        score = info.data.get('score')
        if score is None:
            return v
        score_labels = {
            1: SentimentLabel.STRONGLY_BEARISH,
            2: SentimentLabel.BEARISH,
            3: SentimentLabel.NEUTRAL,
            4: SentimentLabel.BULLISH,
            5: SentimentLabel.STRONGLY_BULLISH
        }
        expected = score_labels.get(score)
        if expected and v != expected:
            raise ValueError(f'label {v} does not match score {score}, expected {expected}')
        return v


class CrossSectorTrends(BaseModel):
    """Aggregated view of trends across all sectors."""
    overall_direction: str = Field(description="expanding, contracting, mixed, or transitioning")
    sectors_in_growth: List[str]
    sectors_in_decline: List[str]
    sector_correlations: List[Correlation]
    trend_summary: str


class SectorAnalysis(BaseModel):
    """Analysis for a specific economic sector."""
    sector_name: str
    summary: str = Field(min_length=50, max_length=2000)
    series_count: int
    phase_distribution: Dict[str, int]  # {"A": 2, "B": 3, "C": 5, "D": 2}
    dominant_trend: str = Field(description="accelerating, slowing, stable, declining, or recovering")
    leading_indicators: List[str] = Field(default_factory=list)
    business_phase: AnalysisBusinessPhase
    correlations: List[Correlation] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    source_pages: List[int]


class OverallAnalysis(BaseModel):
    """Complete document-level analysis synthesizing all economic indicators."""
    executive_summary: str = Field(min_length=100, max_length=5000)
    key_themes: List[Theme] = Field(default_factory=list)
    cross_sector_trends: CrossSectorTrends
    recommendations: List[str] = Field(default_factory=list)
    sentiment_score: SentimentScore


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis generation."""
    version: str = "1.0"
    generated_at: datetime
    generator_version: str
    llm_model: str
    processing_time_seconds: float
    regenerated_from_version: Optional[str] = None


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
