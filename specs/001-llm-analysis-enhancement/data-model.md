# Data Model: Enhanced LLM Analysis

**Feature**: 001-llm-analysis-enhancement
**Date**: 2025-12-09

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FlowDocument                                 │
│  (Extended - existing collection: ITRextract_Flow)                  │
├─────────────────────────────────────────────────────────────────────┤
│  report_id: str                                                      │
│  pdf_filename: str                                                   │
│  report_period: str                                                  │
│  extraction_timestamp: datetime                                      │
│  metadata: DocumentMetadata                                          │
│  document_flow: List[PageFlow]                                       │
│  series_index: Dict[str, SeriesInfo]                                │
│  aggregated_insights: AggregatedInsights                            │
│  ─────────────────────────────────────────────────────────────────  │
│  overall_analysis: OverallAnalysis        # NEW                     │
│  sector_analyses: Dict[str, SectorAnalysis]  # NEW                  │
│  analysis_metadata: AnalysisMetadata      # NEW                     │
└─────────────────────────────────────────────────────────────────────┘
           │
           ├─────────────────────────────────────┐
           │                                     │
           ▼                                     ▼
┌─────────────────────────────┐     ┌─────────────────────────────────┐
│     OverallAnalysis         │     │       SectorAnalysis            │
│  (NEW)                      │     │  (NEW)                          │
├─────────────────────────────┤     ├─────────────────────────────────┤
│  executive_summary: str     │     │  sector_name: str               │
│  key_themes: List[Theme]    │     │  summary: str                   │
│  cross_sector_trends:       │     │  series_count: int              │
│    CrossSectorTrends        │     │  phase_distribution: Dict       │
│  recommendations: List[str] │     │  dominant_trend: str            │
│  sentiment_score:           │     │  leading_indicators: List[str]  │
│    SentimentScore           │     │  business_phase: str            │
└─────────────────────────────┘     │  correlations: List[Correlation]│
           │                        │  key_insights: List[str]        │
           │                        │  source_pages: List[int]        │
           ▼                        └─────────────────────────────────┘
┌─────────────────────────────┐
│      SentimentScore         │
│  (NEW)                      │
├─────────────────────────────┤
│  score: int (1-5)           │
│  label: str                 │
│  confidence: str            │
│  contributing_factors:      │
│    List[ContributingFactor] │
│  sector_weights: Dict       │
│  indicator_signals:         │
│    List[IndicatorSignal]    │
│  rationale: str             │
└─────────────────────────────┘
```

## New Entities

### 1. OverallAnalysis

Represents the complete document-level analysis synthesizing all economic indicators.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `executive_summary` | string | Yes | 3-5 paragraph synthesis of the entire report |
| `key_themes` | List[Theme] | Yes | Top 5-10 recurring themes ranked by significance |
| `cross_sector_trends` | CrossSectorTrends | Yes | Relationships between sectors |
| `recommendations` | List[string] | Yes | 3-5 actionable business recommendations |
| `sentiment_score` | SentimentScore | Yes | Overall economic sentiment with context |

**Validation Rules**:
- `executive_summary` must be 100-2000 characters
- `key_themes` must have 5-10 items (per SC-007)
- `recommendations` must have 3-5 items

**State Transitions**: N/A (immutable after generation)

---

### 2. SentimentScore

5-point economic sentiment classification with structured context for downstream modeling.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `score` | integer | Yes | 1-5 scale (1=Strongly Bearish, 5=Strongly Bullish) |
| `label` | string | Yes | Human-readable label |
| `confidence` | string | Yes | "high", "medium", or "low" |
| `contributing_factors` | List[ContributingFactor] | Yes | Factors influencing the score |
| `sector_weights` | Dict[string, float] | Yes | Relative contribution by sector (sum=1.0) |
| `indicator_signals` | List[IndicatorSignal] | Yes | Individual indicator directions |
| `rationale` | string | Yes | LLM-generated explanation |

**Score Labels**:
| Score | Label |
|-------|-------|
| 1 | Strongly Bearish |
| 2 | Bearish |
| 3 | Neutral |
| 4 | Bullish |
| 5 | Strongly Bullish |

**Validation Rules**:
- `score` must be 1-5
- `label` must match score value
- `confidence` must be one of: "high", "medium", "low"
- `sector_weights` values must sum to 1.0 (±0.01)

---

### 3. ContributingFactor

A factor that influenced the sentiment score.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `factor_name` | string | Yes | Name of the factor |
| `impact` | string | Yes | "positive", "negative", or "neutral" |
| `weight` | float | Yes | Contribution weight (0.0-1.0) |
| `description` | string | Yes | Brief explanation |

---

### 4. IndicatorSignal

Individual economic indicator direction signal.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `indicator_name` | string | Yes | Name of the economic indicator |
| `sector` | string | Yes | Sector this indicator belongs to |
| `direction` | string | Yes | "rising", "falling", "stable" |
| `phase` | string | No | Business cycle phase (A/B/C/D) |
| `source_page` | integer | Yes | Page number in PDF |

---

### 5. SectorAnalysis

Analysis for a specific economic sector.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sector_name` | string | Yes | Sector identifier (core, financial, construction, manufacturing) |
| `summary` | string | Yes | LLM-generated sector summary (200-1000 chars) |
| `series_count` | integer | Yes | Number of series in this sector |
| `phase_distribution` | Dict[string, int] | Yes | Count of series in each phase (A/B/C/D) |
| `dominant_trend` | string | Yes | "accelerating", "slowing", "stable", "declining", "recovering" |
| `leading_indicators` | List[string] | Yes | Top 3 leading indicators for this sector |
| `business_phase` | string | Yes | Overall sector phase (A/B/C/D) |
| `correlations` | List[Correlation] | No | Relationships with other sectors |
| `key_insights` | List[string] | Yes | 3-5 sector-specific insights |
| `source_pages` | List[int] | Yes | Page numbers containing sector data |

**Sector Identifiers**:
- `core` - Primary economic indicators
- `financial` - Financial markets and prices
- `construction` - Building and construction
- `manufacturing` - Industrial manufacturing

---

### 6. Correlation

Relationship between economic sectors or indicators.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `related_sector` | string | Yes | The correlated sector name |
| `relationship` | string | Yes | "leading", "lagging", "concurrent" |
| `lag_months` | integer | No | Typical lag in months |
| `strength` | string | Yes | "strong", "moderate", "weak" |
| `description` | string | No | Explanation of the relationship |

---

### 7. Theme

A recurring economic topic identified across the report.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `theme_name` | string | Yes | Short theme title |
| `significance_score` | float | Yes | 1.0-10.0 importance score |
| `frequency` | integer | Yes | Number of mentions/occurrences |
| `description` | string | Yes | Detailed theme description |
| `affected_sectors` | List[string] | Yes | Sectors impacted by this theme |
| `source_pages` | List[int] | Yes | Pages where theme appears |
| `business_implications` | string | Yes | What this means for business decisions |

**Validation Rules**:
- `significance_score` must be 1.0-10.0
- `frequency` must be >= 1
- `affected_sectors` must contain valid sector names

---

### 8. CrossSectorTrends

Aggregated view of trends across all sectors.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `overall_direction` | string | Yes | "expanding", "contracting", "mixed", "transitioning" |
| `sectors_in_growth` | List[string] | Yes | Sectors showing growth (phases A/B) |
| `sectors_in_decline` | List[string] | Yes | Sectors showing decline (phases C/D) |
| `sector_correlations` | List[Correlation] | Yes | Cross-sector relationships |
| `trend_summary` | string | Yes | LLM-generated summary of cross-sector dynamics |

---

### 9. AnalysisMetadata

Metadata about the analysis generation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Analysis schema version (e.g., "1.0") |
| `generated_at` | datetime | Yes | When analysis was generated |
| `generator_version` | string | Yes | Software version (e.g., "3.1.0") |
| `llm_model` | string | Yes | LLM model used (e.g., "gpt-4.1") |
| `processing_time_seconds` | float | Yes | Time taken to generate analysis |
| `regenerated_from_version` | string | No | Previous version if regenerated |

---

## MongoDB Schema Extension

The existing `ITRextract_Flow` collection schema is extended with:

```javascript
{
  // ... existing fields ...

  "overall_analysis": {
    "executive_summary": { "type": "string", "required": true },
    "key_themes": {
      "type": "array",
      "items": {
        "theme_name": "string",
        "significance_score": "number",
        "frequency": "number",
        "description": "string",
        "affected_sectors": ["string"],
        "source_pages": ["number"],
        "business_implications": "string"
      },
      "minItems": 5,
      "maxItems": 10
    },
    "cross_sector_trends": {
      "overall_direction": "string",
      "sectors_in_growth": ["string"],
      "sectors_in_decline": ["string"],
      "sector_correlations": ["object"],
      "trend_summary": "string"
    },
    "recommendations": { "type": "array", "items": "string", "minItems": 3, "maxItems": 5 },
    "sentiment_score": {
      "score": { "type": "number", "minimum": 1, "maximum": 5 },
      "label": "string",
      "confidence": { "enum": ["high", "medium", "low"] },
      "contributing_factors": ["object"],
      "sector_weights": "object",
      "indicator_signals": ["object"],
      "rationale": "string"
    }
  },

  "sector_analyses": {
    "type": "object",
    "additionalProperties": {
      "sector_name": "string",
      "summary": "string",
      "series_count": "number",
      "phase_distribution": "object",
      "dominant_trend": "string",
      "leading_indicators": ["string"],
      "business_phase": "string",
      "correlations": ["object"],
      "key_insights": ["string"],
      "source_pages": ["number"]
    }
  },

  "analysis_metadata": {
    "version": "string",
    "generated_at": "date",
    "generator_version": "string",
    "llm_model": "string",
    "processing_time_seconds": "number",
    "regenerated_from_version": "string"
  }
}
```

---

## Pydantic Models (Python)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TrendDirection(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"


class BusinessPhase(str, Enum):
    A = "A"  # Recovery
    B = "B"  # Accelerating Growth
    C = "C"  # Slowing Growth
    D = "D"  # Recession


class SentimentLabel(str, Enum):
    STRONGLY_BEARISH = "Strongly Bearish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    BULLISH = "Bullish"
    STRONGLY_BULLISH = "Strongly Bullish"


class ContributingFactor(BaseModel):
    factor_name: str
    impact: str  # positive, negative, neutral
    weight: float = Field(ge=0.0, le=1.0)
    description: str


class IndicatorSignal(BaseModel):
    indicator_name: str
    sector: str
    direction: TrendDirection
    phase: Optional[BusinessPhase] = None
    source_page: int


class SentimentScore(BaseModel):
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
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f'sector_weights must sum to 1.0, got {total}')
        return v


class Correlation(BaseModel):
    related_sector: str
    relationship: str  # leading, lagging, concurrent
    lag_months: Optional[int] = None
    strength: str  # strong, moderate, weak
    description: Optional[str] = None


class Theme(BaseModel):
    theme_name: str
    significance_score: float = Field(ge=1.0, le=10.0)
    frequency: int = Field(ge=1)
    description: str
    affected_sectors: List[str]
    source_pages: List[int]
    business_implications: str


class CrossSectorTrends(BaseModel):
    overall_direction: str  # expanding, contracting, mixed, transitioning
    sectors_in_growth: List[str]
    sectors_in_decline: List[str]
    sector_correlations: List[Correlation]
    trend_summary: str


class SectorAnalysis(BaseModel):
    sector_name: str
    summary: str = Field(min_length=200, max_length=1000)
    series_count: int
    phase_distribution: Dict[str, int]  # {"A": 2, "B": 3, "C": 5, "D": 2}
    dominant_trend: str
    leading_indicators: List[str] = Field(max_length=3)
    business_phase: BusinessPhase
    correlations: List[Correlation] = []
    key_insights: List[str] = Field(min_length=3, max_length=5)
    source_pages: List[int]


class OverallAnalysis(BaseModel):
    executive_summary: str = Field(min_length=100, max_length=2000)
    key_themes: List[Theme] = Field(min_length=5, max_length=10)
    cross_sector_trends: CrossSectorTrends
    recommendations: List[str] = Field(min_length=3, max_length=5)
    sentiment_score: SentimentScore


class AnalysisMetadata(BaseModel):
    version: str = "1.0"
    generated_at: datetime
    generator_version: str
    llm_model: str
    processing_time_seconds: float
    regenerated_from_version: Optional[str] = None
```

---

## Data Volume Estimates

| Entity | Per Document | Storage Size |
|--------|--------------|--------------|
| OverallAnalysis | 1 | ~10 KB |
| SectorAnalysis | 4-5 | ~3 KB each (~15 KB total) |
| Theme | 5-10 | ~500 bytes each (~5 KB total) |
| IndicatorSignal | 40-60 | ~100 bytes each (~6 KB total) |
| **Total Analysis Addition** | - | **~36 KB per document** |

Current document size: ~500 KB - 2 MB (depending on chart data)
Analysis adds: ~2-7% overhead
