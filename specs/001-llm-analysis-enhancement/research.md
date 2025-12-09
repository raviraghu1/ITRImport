# Research: Enhanced LLM Analysis

**Feature**: 001-llm-analysis-enhancement
**Date**: 2025-12-09
**Status**: Complete

## Research Tasks

### 1. LLM Prompt Engineering for Document-Level Analysis

**Decision**: Use a two-stage LLM approach - first aggregate page-level data, then synthesize into overall analysis.

**Rationale**:
- Azure OpenAI GPT-4 has a 128K context window but performs better with focused prompts
- Page-level summaries already exist in `page_summary` field (generated in `_generate_page_summary`)
- Aggregating these first reduces token usage and improves coherence
- Matches existing pattern in `analyze_trends()` method

**Alternatives Considered**:
1. Single massive prompt with all page text - Rejected: token limits, poor focus
2. Multi-turn conversation - Rejected: adds latency, complexity
3. External summarization model - Rejected: additional dependency, consistency issues

**Implementation Approach**:
```python
# Stage 1: Collect existing page summaries and chart interpretations
summaries = [page.page_summary for page in document_flow]
interpretations = [block.interpretation for block in all_chart_blocks]

# Stage 2: Generate overall analysis from aggregated data
overall_analysis = llm.generate_overall_analysis(summaries, interpretations, series_index)
```

---

### 2. Sentiment Score Calculation Method

**Decision**: Weighted sector-based sentiment aggregation with LLM interpretation.

**Rationale**:
- Sectors have varying importance in ITR reports (core > financial > construction > manufacturing)
- Business cycle phases (A/B/C/D) provide quantifiable signals
- LLM can interpret phase transitions and provide nuanced sentiment
- Structured output enables downstream modeling per clarification requirements

**5-Point Scale Mapping**:
| Score | Label | Phase Indicators | Description |
|-------|-------|------------------|-------------|
| 5 | Strongly Bullish | Majority A/B phases, rising trends | Expansion expected |
| 4 | Bullish | Mixed A/B with some C, generally rising | Moderate growth |
| 3 | Neutral | Mixed phases, flat trends | Uncertainty/transition |
| 2 | Bearish | Majority C/D phases, declining trends | Contraction expected |
| 1 | Strongly Bearish | Majority D phases, sharp declines | Recession underway |

**Confidence Calculation**:
- High: >80% phase agreement across sectors
- Medium: 50-80% agreement
- Low: <50% agreement

**Alternatives Considered**:
1. Pure rule-based scoring - Rejected: lacks nuance, misses context
2. Pure LLM scoring - Rejected: inconsistent, not reproducible
3. External economic model - Rejected: out of scope, adds complexity

---

### 3. Sector Analysis Aggregation Strategy

**Decision**: Group series by sector using existing `SERIES_PATTERNS` mapping, then generate per-sector LLM summaries.

**Rationale**:
- `FlowExtractor.SERIES_PATTERNS` already maps series names to sectors
- `series_index` contains per-series summaries and insights
- Sector-level analysis is aggregation + synthesis of these existing elements

**Sectors Identified in Codebase**:
1. `core` - US Industrial Production, Retail Sales, Employment, etc.
2. `financial` - Stock Prices, Bond Yields, CPI, PPI, etc.
3. `construction` - Housing Starts, Commercial Construction, etc.
4. `manufacturing` - Machinery, Vehicles, Aerospace, etc.

**Per-Sector Output Structure**:
```python
{
    "sector_name": "manufacturing",
    "summary": "LLM-generated sector summary",
    "series_count": 12,
    "phase_distribution": {"A": 2, "B": 3, "C": 5, "D": 2},
    "dominant_trend": "slowing",
    "leading_indicators": ["US Machinery New Orders", "US Construction Machinery"],
    "business_phase": "C",
    "correlations": [{"related_sector": "construction", "relationship": "leading", "lag_months": 3}],
    "key_insights": ["insight1", "insight2"],
    "source_pages": [3, 5, 12, 15, 22]
}
```

---

### 4. Cross-Sector Correlation Analysis

**Decision**: Use predefined economic relationships with LLM confirmation/enhancement.

**Rationale**:
- Economic sectors have known interdependencies (e.g., construction leads manufacturing)
- ITR Economics provides domain expertise in their reports
- LLM can identify report-specific correlations from the data
- Combining predefined relationships with LLM analysis provides robustness

**Known Relationships** (from ITR methodology):
| Leading Sector | Lagging Sector | Typical Lag |
|----------------|----------------|-------------|
| Financial | Core | 6-12 months |
| Core | Construction | 3-6 months |
| Core | Manufacturing | 3-9 months |
| Construction | Manufacturing | 0-3 months |

**Implementation**:
```python
# Use LLM to identify correlations from current report data
correlations = llm.identify_correlations(sector_analyses)

# Validate against known relationships
validated_correlations = validate_with_known_patterns(correlations)
```

---

### 5. Incremental Analysis Update Strategy (FR-014)

**Decision**: Store analysis with version tracking; regenerate analysis on-demand without full document reprocessing.

**Rationale**:
- Document extraction is expensive (PDF parsing, image extraction)
- Analysis is cheaper (LLM calls on existing extracted data)
- Version tracking enables analysis evolution without data loss

**Schema Addition**:
```python
"analysis_metadata": {
    "version": "1.0",
    "generated_at": "2025-12-09T10:00:00Z",
    "generator_version": "3.1.0",
    "llm_model": "gpt-4.1",
    "regenerated_from_version": null  # or previous version if incremental
}
```

**Regeneration Trigger**:
- New API endpoint: `POST /api/reports/{id}/regenerate-analysis`
- Uses existing extracted data from MongoDB
- Only calls LLM for analysis generation

---

### 6. Theme Identification Approach

**Decision**: Extract themes using LLM analysis of aggregated insights with frequency and impact weighting.

**Rationale**:
- Themes emerge from patterns across multiple series/pages
- Existing `key_insights` field provides raw material
- LLM excels at pattern recognition and summarization
- Frequency (how often mentioned) + Impact (business significance) provides ranking

**Theme Output Structure**:
```python
{
    "theme_name": "Manufacturing Slowdown",
    "significance_score": 8.5,  # 1-10 scale
    "frequency": 15,  # mentions across pages
    "description": "Multiple manufacturing indicators showing phase C/D...",
    "affected_sectors": ["manufacturing", "core"],
    "source_pages": [5, 12, 22, 35],
    "business_implications": "Prepare for reduced capital equipment demand..."
}
```

---

### 7. Export Schema Design (FR-019, FR-020, FR-021)

**Decision**: Extend existing JSON export with nested analysis structure; maintain backwards compatibility.

**Rationale**:
- Current export format is used by downstream systems
- Adding new top-level fields preserves existing integrations
- Nested structure matches spec entity hierarchy

**Export Structure Addition**:
```json
{
  "report_id": "...",
  "document_flow": [...],
  "series_index": {...},

  "overall_analysis": {
    "executive_summary": "...",
    "key_themes": [...],
    "cross_sector_trends": {...},
    "recommendations": [...],
    "sentiment_score": {...}
  },

  "sector_analyses": {
    "core": {...},
    "financial": {...},
    "construction": {...},
    "manufacturing": {...}
  },

  "analysis_metadata": {...}
}
```

---

### 8. Viewer Integration Approach

**Decision**: Add new "Analysis" tab adjacent to existing tabs; reuse existing component patterns.

**Rationale**:
- Viewer already has tabbed navigation (Overview, Series, Charts)
- Consistent UX by following existing patterns
- CSS variables already defined for styling

**Tab Structure**:
```
[Overview] [Series] [Charts] [Analysis]  <- New tab
                                |
                                ├── Executive Summary section
                                ├── Sentiment Score (visual indicator)
                                ├── Key Themes (ranked list)
                                ├── Sector Navigator (dropdown/tabs)
                                │   ├── Core
                                │   ├── Financial
                                │   ├── Construction
                                │   └── Manufacturing
                                ├── Cross-Sector Trends
                                └── Recommendations
```

**Source Linking**:
- Each insight displays page reference
- Clicking page number navigates PDF viewer to that page
- Reuses existing `goToPage()` function

---

## Summary

All research tasks completed. No NEEDS CLARIFICATION items remain. The implementation approach:

1. **New Module**: `src/analysis_generator.py` - Orchestrates analysis generation
2. **Model Extensions**: Add `OverallAnalysis`, `SectorAnalysis`, `SentimentScore` to `models.py`
3. **LLM Extensions**: Add `generate_overall_analysis()`, `generate_sector_analysis()`, `calculate_sentiment()` to `llm_extractor.py`
4. **Pipeline Integration**: Extend `FlowExtractor.extract_full_document_flow()` to call analysis generator
5. **API Extension**: Add `/api/reports/{id}/analysis` endpoint
6. **Viewer Extension**: Add Analysis tab with sector navigation

**Next Step**: Phase 1 - Generate data-model.md and contracts/
