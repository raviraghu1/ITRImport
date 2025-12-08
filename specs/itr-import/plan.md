# Implementation Plan: ITR Economics Data Import & Analysis System

**Branch**: `main` | **Date**: 2025-12-08 | **Spec**: [spec.md](./spec.md)
**Status**: Implemented (v2.1.0)

## Summary

Comprehensive data extraction system for ITR Economics Trends Report PDFs, featuring PyMuPDF-based parsing, Azure OpenAI GPT-4 enhancement, MongoDB storage with consolidated documents, and multi-format reporting.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PyMuPDF (fitz), pymongo, httpx, pandas
**Storage**: MongoDB Atlas (cloud) / MongoDB (local)
**Testing**: pytest (recommended for future tests)
**Target Platform**: macOS/Linux CLI
**Project Type**: Single project (CLI application)
**Performance Goals**: <3 min per PDF with LLM, <30s without
**Constraints**: Azure OpenAI API rate limits, MongoDB connection limits
**Scale/Scope**: 5-50 PDFs per batch, 30-50 series per PDF

## Constitution Check

*Per project constitution v1.0.0:*

| Principle | Compliance |
|-----------|------------|
| I. Data Fidelity | ✅ Original values preserved from PDFs |
| II. Source Traceability | ✅ Every data point linked to source PDF/page |
| III. Structured Data Model | ✅ MongoDB collections by sector with schema |
| IV. Idempotent Processing | ✅ Upsert operations with composite keys |
| V. Visualization Integrity | ✅ Chart metadata captured for reproduction |
| VI. Test Coverage | ⚠️ Manual testing complete; automated tests recommended |
| VII. Simplicity | ✅ Standard libraries, clear structure |

## Project Structure

### Documentation

```text
specs/itr-import/
├── spec.md              # Feature specification (this PRD)
├── plan.md              # Implementation plan (this file)
└── tasks.md             # Task list (to be generated)
```

### Source Code

```text
ITRImport/
├── main.py                    # Basic extraction entry point
├── main_enhanced.py           # Enhanced extraction with LLM
├── import_to_mongodb.py       # MongoDB import utility
├── create_consolidated_docs.py # Consolidated document generator
├── extract_pdf.py             # Simple PDF text extraction utility
├── src/
│   ├── __init__.py
│   ├── models.py              # Data models (EconomicSeries, ForecastRange, etc.)
│   ├── parser.py              # Basic PDF parser
│   ├── enhanced_parser.py     # Enhanced parser with chart/table context
│   ├── database.py            # MongoDB operations
│   ├── analyzer.py            # Basic analysis and reporting
│   ├── enhanced_analyzer.py   # Enhanced analysis with detailed reports
│   └── llm_extractor.py       # Azure OpenAI GPT-4 integration
├── output/                    # Generated reports and exports
│   └── consolidated/          # Consolidated JSON files (one per PDF)
├── Files/                     # Source PDF files
└── .specify/
    └── memory/
        └── constitution.md    # Project principles
```

## Component Design

### 1. Data Models (`src/models.py`)

```python
@dataclass
class EconomicSeries:
    series_id: str
    series_name: str
    sector: Sector
    unit: str
    current_value: Optional[float]
    forecasts: list[ForecastRange]
    highlights: list[str]
    source: SourceMetadata

@dataclass
class ForecastRange:
    year: int
    metric_type: str  # "12/12", "12MMA", "12MMT"
    value_point: Optional[float]
    value_min: Optional[float]
    value_max: Optional[float]

class Sector(Enum):
    CORE = "core"
    FINANCIAL = "financial"
    CONSTRUCTION = "construction"
    MANUFACTURING = "manufacturing"

class BusinessPhase(Enum):
    PHASE_A = "A"  # Recovery
    PHASE_B = "B"  # Accelerating Growth
    PHASE_C = "C"  # Slowing Growth
    PHASE_D = "D"  # Recession
```

### 2. Enhanced Parser (`src/enhanced_parser.py`)

- Uses PyMuPDF for PDF text and image extraction
- Pattern matching for series identification
- Positional analysis for forecast table extraction
- Chart metadata capture from page images

### 3. LLM Extractor (`src/llm_extractor.py`)

- Azure OpenAI GPT-4.1 integration via REST API
- Structured JSON extraction prompts
- Fallback handling for API failures
- Methods: `extract_series_data()`, `extract_forecast_table()`, `extract_executive_summary()`

### 4. Database Layer (`src/database.py`)

- MongoDB client with connection pooling
- Sector-specific collections
- Composite key indexes for idempotency
- Upsert operations for data updates

### 5. Consolidated Document Generator (`create_consolidated_docs.py`)

- Creates single document per PDF for downstream use
- Aggregates all series, charts, and forecast tables
- Builds series index for quick lookups
- Exports both to MongoDB and JSON files

### 6. Enhanced Analyzer (`src/enhanced_analyzer.py`)

- Multi-format report generation (TXT, JSON, CSV)
- Forecast summary aggregation
- Charts manifest export
- Sector-based analysis

## API Integration

### Azure OpenAI Configuration

```python
endpoint = "https://gptproductsearch.openai.azure.com/openai/deployments/gpt-4.1/chat/completions"
api_version = "2025-01-01-preview"
```

### MongoDB Configuration

```python
uri = "mongodb+srv://licensing:***@analytics.meugir.mongodb.net/"
database = "ITRReports"
collections = [
    "reports",              # Report metadata
    "core_series",          # Core economic indicators
    "financial_series",     # Financial market indicators
    "construction_series",  # Construction sector indicators
    "manufacturing_series", # Manufacturing sector indicators
    "charts",               # Chart metadata
    "forecast_tables",      # Forecast tables
    "reports_consolidated"  # Single document per PDF (downstream use)
]
```

## Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  PDF File   │────▶│ EnhancedParser│────▶│ Raw Series  │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐            │
                    │ LLMExtractor │◀───────────┤
                    └──────┬───────┘            │
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │Enhanced Data │────▶│  MongoDB    │
                    └──────┬───────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Analyzer   │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │   JSON   │  │   CSV    │  │   TXT    │
      └──────────┘  └──────────┘  └──────────┘
```

## Extraction Pipeline

### Phase 1: PDF Parsing
1. Open PDF with PyMuPDF
2. Detect report period from first pages
3. Extract At-a-Glance summary tables
4. Iterate through pages for series detection

### Phase 2: Series Extraction
1. Match page text against series patterns
2. Extract unit of measurement
3. Capture chart metadata (images)
4. Parse forecast sections
5. Extract highlights and management objectives

### Phase 3: LLM Enhancement
1. Send page text to GPT-4 for structured extraction
2. Merge LLM results with parsed data
3. Extract executive summary
4. Handle API errors gracefully

### Phase 4: Storage & Export
1. Upsert series to MongoDB by sector
2. Save report metadata
3. Generate text report
4. Export JSON with full context
5. Export CSV summary
6. Generate charts manifest

### Phase 5: Consolidation (Optional)
1. Query all sector collections for report
2. Aggregate series, charts, and forecast tables
3. Build series index for quick lookups
4. Create single consolidated document
5. Upsert to `reports_consolidated` collection
6. Export consolidated JSON file

## Error Handling

| Error Type | Handling |
|------------|----------|
| PDF not found | Raise `FileNotFoundError` with clear message |
| MongoDB connection | Log warning, continue with file-only output |
| LLM API timeout | Log error, use basic extraction |
| Invalid forecast data | Skip with warning, don't fail entire page |
| Duplicate series | Update existing record (upsert) |

## Performance Optimizations

1. **Page-by-page processing**: Avoids loading entire PDF into memory
2. **Seen series tracking**: Prevents duplicate processing
3. **Batch database operations**: Reduces connection overhead
4. **LLM request batching**: One call per series page (could be optimized)
5. **Lazy loading**: Charts manifest generated on demand

## Testing Strategy

### Manual Testing (Completed)
- ✅ Single PDF extraction
- ✅ Batch PDF processing (5 PDFs)
- ✅ MongoDB storage and retrieval
- ✅ LLM enhancement
- ✅ Report generation
- ✅ Idempotent reprocessing

### Recommended Automated Tests
- Unit tests for pattern matching
- Integration tests for PDF parsing
- Contract tests for MongoDB documents
- Mock tests for LLM integration

## Deployment

### Requirements
```bash
pip install pymupdf pymongo httpx pandas
```

### Environment Setup
```bash
export ITR_MONGODB_URI="mongodb+srv://..."
export AZURE_OPENAI_KEY="..."
```

### Execution
```bash
# Full processing
python main_enhanced.py

# Single PDF
python main_enhanced.py --pdf "Files/report.pdf"

# Without external services
python main_enhanced.py --no-db --no-llm

# Import to MongoDB
python import_to_mongodb.py

# Create consolidated documents
python create_consolidated_docs.py
```

## Metrics & Monitoring

### Current Results (v2.1.0)

| Metric | Value |
|--------|-------|
| PDFs Processed | 5 |
| Series Extracted | 118 |
| Charts Captured | 289 |
| Forecast Tables | 29 |
| LLM Enhanced | 118 |
| Consolidated Documents | 5 |
| Total MongoDB Documents | 446 |
| Processing Time | ~2 min/PDF with LLM |

### Recommended Monitoring
- Extraction success rate per PDF
- LLM API latency and error rate
- MongoDB operation latency
- Series count per sector over time
