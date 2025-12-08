# Feature Specification: ITR Economics Data Import & Analysis System

**Feature Branch**: `main`
**Created**: 2025-12-08
**Status**: Implemented
**Version**: 3.0.0

## Overview

ITRImport is a comprehensive data extraction and analysis system for ITR Economics Trends Report PDFs. The system extracts economic indicators, forecasts, charts, and contextual information from PDF reports, stores them in MongoDB, and provides analysis capabilities powered by Azure OpenAI GPT-4.

### Key Capabilities (v3.0.0)

- **Automated Workflow**: End-to-end processing with single command or file watcher
- **Flow-Based Documents**: Preserve PDF context flow for better LLM understanding
- **Vision-Based Chart Analysis**: GPT-4 Vision interprets 665 charts with trend analysis
- **LLM Enhancement**: Intelligent content extraction with Azure OpenAI GPT-4
- **MongoDB Storage**: Organized by sector with consolidated and flow collections

## User Scenarios & Testing

### User Story 1 - PDF Data Extraction (Priority: P1)

As a data analyst, I want to extract all economic data series from ITR Trends Report PDFs so that I can analyze economic indicators programmatically without manual data entry.

**Why this priority**: Core functionality - without extraction, no other features can work. This is the foundation of the entire system.

**Independent Test**: Run `python main_enhanced.py --pdf "Files/report.pdf" --no-db --no-llm` and verify JSON output contains all series from the PDF.

**Acceptance Scenarios**:

1. **Given** an ITR Trends Report PDF, **When** I run the extraction, **Then** the system extracts all economic series with their names, sectors, and source page numbers.
2. **Given** a PDF with 58 pages, **When** extraction completes, **Then** at least 30 economic series are identified and extracted.
3. **Given** a series page with forecast data, **When** extracted, **Then** forecasts include year, 12/12 rate, and 12MMA/12MMT values.

---

### User Story 2 - Chart and Table Context Capture (Priority: P1)

As a data analyst, I want charts and tables to be captured with their full context so that I can understand the visual data representations and recreate visualizations.

**Why this priority**: Charts and tables contain critical forecast and trend data that text alone cannot convey. Essential for complete data capture.

**Independent Test**: Run extraction and verify `*_charts_manifest.json` contains chart metadata with dimensions, types, and page references.

**Acceptance Scenarios**:

1. **Given** a series page with rate-of-change and data trend charts, **When** extracted, **Then** chart metadata includes type, dimensions, and image reference (xref).
2. **Given** a forecast table on a page, **When** extracted, **Then** table data is structured with headers, rows, and surrounding context text.
3. **Given** an At-a-Glance summary page, **When** extracted, **Then** sector summary and phase information is captured.

---

### User Story 3 - LLM-Enhanced Extraction (Priority: P2)

As a data analyst, I want AI-powered extraction to intelligently parse complex content so that I get higher quality, contextually rich data.

**Why this priority**: Improves extraction quality significantly but system works without it. Adds value on top of base extraction.

**Independent Test**: Run `python main_enhanced.py --pdf "Files/report.pdf"` and compare output with `--no-llm` version to verify enhanced content.

**Acceptance Scenarios**:

1. **Given** a series page with bullet points, **When** LLM extraction runs, **Then** highlights are cleanly extracted as a structured list.
2. **Given** an executive summary page, **When** LLM processes it, **Then** author, key points, and outlook are structured.
3. **Given** management objective text, **When** LLM extracts it, **Then** the objective is clean, complete, and contextual.

---

### User Story 4 - MongoDB Storage (Priority: P2)

As a data engineer, I want extracted data stored in MongoDB so that I can query, analyze, and integrate the data with other systems.

**Why this priority**: Enables persistence and querying but extraction works standalone with file output.

**Independent Test**: Run extraction with database, then run `python main_enhanced.py --stats` to verify document counts.

**Acceptance Scenarios**:

1. **Given** extracted series data, **When** stored in MongoDB, **Then** data is organized in sector-specific collections (core, financial, construction, manufacturing).
2. **Given** the same PDF processed twice, **When** stored, **Then** existing records are updated (upsert) without duplicates.
3. **Given** series with source metadata, **When** queried, **Then** I can trace back to exact PDF filename, page, and extraction timestamp.

---

### User Story 5 - Analysis and Reporting (Priority: P3)

As a business analyst, I want comprehensive reports generated so that I can review extracted data without writing code.

**Why this priority**: Convenience feature that adds value but isn't required for core data extraction.

**Independent Test**: Run extraction and verify `*_enhanced_report.txt` contains formatted, readable analysis.

**Acceptance Scenarios**:

1. **Given** extracted data, **When** report generated, **Then** it includes executive summary, sector breakdown, and forecast overview.
2. **Given** multiple series, **When** CSV exported, **Then** it includes all series with forecasts in tabular format.
3. **Given** charts extracted, **When** manifest generated, **Then** it lists all charts with series mapping and page references.

---

### User Story 6 - Data Visualization Integration (Priority: P3)

As a dashboard developer, I want chart metadata and data exported so that I can recreate ITR visualizations in our BI tools.

**Why this priority**: Enables downstream visualization but requires other systems to implement.

**Independent Test**: Verify `*_charts_manifest.json` and `*_enhanced_data.json` contain sufficient metadata for chart recreation.

**Acceptance Scenarios**:

1. **Given** chart metadata, **When** exported, **Then** it includes image dimensions, chart type, and associated series.
2. **Given** forecast data, **When** exported as JSON, **Then** it includes year-by-year values suitable for time-series charts.
3. **Given** business cycle phases, **When** exported, **Then** phase codes (A, B, C, D) and descriptions are included.

---

### User Story 7 - Consolidated Documents for Downstream Use (Priority: P1)

As a downstream system developer, I want a single consolidated document per PDF file so that I can easily consume complete report data without joining multiple collections.

**Why this priority**: Critical for downstream integration - enables simple queries and data pipelines.

**Independent Test**: Run `python create_consolidated_docs.py` and verify `reports_consolidated` collection contains one document per PDF with all data.

**Acceptance Scenarios**:

1. **Given** extracted data from a PDF, **When** consolidated, **Then** a single document contains all series, charts, forecasts, and metadata.
2. **Given** a consolidated document, **When** queried, **Then** I can access series by sector, get all chart metadata, and retrieve the executive summary in one query.
3. **Given** 5 processed PDFs, **When** consolidation runs, **Then** 5 documents exist in `reports_consolidated` collection.
4. **Given** a consolidated document, **When** I need series names, **Then** `series_index.all_series_names` provides a quick lookup list.

---

### User Story 8 - Flow-Based Documents with Vision Analysis (Priority: P1)

As a downstream LLM system, I want documents that preserve the PDF reading order with AI interpretations of charts so that I can understand economic data in its original context.

**Why this priority**: Critical for downstream LLM consumption - maintains context and provides visual data interpretation.

**Independent Test**: Run `python create_flow_document.py` and verify `ITRextract_Flow` collection contains flow documents with chart interpretations.

**Acceptance Scenarios**:

1. **Given** a PDF with mixed text and charts, **When** flow extraction runs, **Then** content blocks maintain reading order (text before related charts).
2. **Given** a chart image in the PDF, **When** processed with vision, **Then** interpretation includes trend direction, business cycle phase, and business implications.
3. **Given** 5 PDFs processed, **When** flow extraction completes, **Then** 665 charts have LLM vision interpretations.
4. **Given** a flow document, **When** queried, **Then** I can iterate through page-by-page content in sequence.

---

### User Story 9 - Automated Workflow with File Watcher (Priority: P2)

As a data engineer, I want an automated workflow that processes PDFs when uploaded so that I don't need to manually trigger processing.

**Why this priority**: Convenience feature that enables hands-off operation.

**Independent Test**: Run `python workflow.py --watch Files/` and drop a new PDF into the directory.

**Acceptance Scenarios**:

1. **Given** watch mode is running, **When** a new PDF is added to the watched directory, **Then** it is automatically processed through the complete pipeline.
2. **Given** a PDF to process, **When** `workflow.py --pdf` is run, **Then** extraction, LLM enhancement, MongoDB storage, and consolidation complete in sequence.
3. **Given** `workflow.py --status`, **When** executed, **Then** it shows database connection status and document counts.

---

### Edge Cases

- **Corrupted PDF**: System should fail gracefully with clear error message, not crash.
- **Missing series name**: Pages without identifiable series names are skipped with no error.
- **Network timeout to MongoDB**: System continues extraction to files; database errors logged.
- **LLM API failure**: System continues with basic extraction; LLM errors logged but don't stop processing.
- **Duplicate PDFs**: Idempotent processing ensures no duplicate records.
- **Non-ITR PDFs**: System extracts what it can; unknown formats yield minimal results.
- **Large PDFs (100+ pages)**: System processes page-by-page without memory issues.

## Requirements

### Functional Requirements

#### Data Extraction
- **FR-001**: System MUST extract economic series name, sector classification, and unit of measurement from each data page.
- **FR-002**: System MUST identify and categorize series into sectors: Core, Financial, Construction, Manufacturing.
- **FR-003**: System MUST extract forecast data including year, 12/12 rate-of-change, and 12MMA/12MMT values.
- **FR-004**: System MUST capture source traceability: PDF filename, page number, extraction timestamp, report period.
- **FR-005**: System MUST extract bullet-point highlights and management objectives from series pages.

#### Chart and Table Processing
- **FR-006**: System MUST identify all images/charts on each page and record their metadata (dimensions, xref, position).
- **FR-007**: System MUST classify charts by type: rate_of_change, data_trend, overview.
- **FR-008**: System MUST extract forecast tables with headers, rows, and contextual text.
- **FR-009**: System MUST capture At-a-Glance summary tables with sector phase information.

#### LLM Integration
- **FR-010**: System MUST integrate with Azure OpenAI GPT-4 for enhanced extraction.
- **FR-011**: System MUST use LLM to extract structured highlights from unstructured text.
- **FR-012**: System MUST use LLM to parse and structure executive summaries.
- **FR-013**: System MUST gracefully degrade to basic extraction if LLM unavailable.

#### Vision-Based Chart Analysis
- **FR-031**: System MUST use GPT-4 Vision to interpret chart images.
- **FR-032**: System MUST extract trend direction (rising/falling/stabilizing) from charts.
- **FR-033**: System MUST identify business cycle phase (A/B/C/D) from chart patterns.
- **FR-034**: System MUST provide business implications for each chart interpretation.
- **FR-035**: System MUST include confidence level for vision interpretations.

#### Data Storage
- **FR-014**: System MUST store extracted data in MongoDB with sector-specific collections.
- **FR-015**: System MUST implement idempotent upsert operations using composite keys (series_id + report_period).
- **FR-016**: System MUST create indexes on date fields and series identifiers for query performance.
- **FR-017**: System MUST store report-level metadata including executive summary and page counts.
- **FR-028**: System MUST create consolidated documents with all data from each PDF in a single document.
- **FR-029**: System MUST include series index for quick lookup in consolidated documents.
- **FR-036**: System MUST store flow-based documents in `ITRextract_Flow` collection.
- **FR-037**: System MUST preserve PDF reading order in flow documents.

#### Output Generation
- **FR-018**: System MUST generate detailed text reports with executive summary, sector breakdown, and forecasts.
- **FR-019**: System MUST export data to JSON with full structure including charts and content.
- **FR-020**: System MUST export CSV summaries suitable for spreadsheet analysis.
- **FR-021**: System MUST generate charts manifest JSON for visualization integration.
- **FR-022**: System MUST generate forecast tables JSON for downstream processing.
- **FR-030**: System MUST export consolidated JSON files for each PDF.
- **FR-038**: System MUST export flow-based JSON files with vision interpretations.

#### Workflow & Automation
- **FR-039**: System MUST provide automated end-to-end workflow via `workflow.py`.
- **FR-040**: System MUST support file watcher mode for automatic PDF processing.
- **FR-041**: System MUST support configurable poll interval for watch mode.

#### CLI Interface
- **FR-023**: System MUST support processing single PDF via `--pdf` argument.
- **FR-024**: System MUST support batch processing of all PDFs in a directory.
- **FR-025**: System MUST support `--no-db` flag to skip database operations.
- **FR-026**: System MUST support `--no-llm` flag to skip LLM enhancement.
- **FR-027**: System MUST support `--stats` flag to display database statistics.

### Key Entities

- **EconomicSeries**: A single economic indicator (e.g., "US Industrial Production") with current value, forecasts, phase, and metadata.
- **ForecastRange**: Year-specific forecast with metric type (12/12, 12MMA, 12MMT), value, and optional min/max bounds.
- **ChartMetadata**: Information about a chart image including type, dimensions, page, and image reference.
- **TableData**: Structured table with headers, rows, and contextual text.
- **SourceMetadata**: Traceability information linking data to source PDF, page, and extraction time.
- **Sector**: Classification enum (Core, Financial, Construction, Manufacturing).
- **BusinessPhase**: ITR business cycle phase (A=Recovery, B=Accelerating, C=Slowing, D=Recession).
- **ConsolidatedReport**: Single document containing all extracted data from one PDF file.

## Technical Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        main_enhanced.py                         │
│                    (CLI Entry Point)                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────────┐
        ▼             ▼             ▼                 ▼
┌───────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐
│ EnhancedParser│ │LLMExtractor│ │ Database │ │EnhancedAnalyzer │
│  (PyMuPDF)   │ │(Azure GPT)│ │ (MongoDB) │ │   (Reports)     │
└───────────────┘ └───────────┘ └───────────┘ └─────────────────┘
        │                              │
        ▼                              ▼
┌───────────────┐              ┌─────────────────────────┐
│    Models     │              │      Collections        │
│ (Dataclasses) │              │ ┌─────────────────────┐ │
└───────────────┘              │ │reports_consolidated │ │
                               │ │  (1 doc per PDF)    │ │
                               │ └─────────────────────┘ │
                               │ core_series             │
                               │ financial_series        │
                               │ construction_series     │
                               │ manufacturing_series    │
                               │ charts                  │
                               │ forecast_tables         │
                               │ reports                 │
                               └─────────────────────────┘
```

### Data Flow

1. **Input**: ITR Trends Report PDF files
2. **Extraction**: PyMuPDF extracts text, images, and structure
3. **Enhancement**: Azure OpenAI GPT-4 enriches extracted content
4. **Storage**: MongoDB stores structured data with indexes
5. **Consolidation**: Create single document per PDF for downstream use
6. **Output**: JSON, CSV, TXT reports for analysis and integration

### Technology Stack

| Component | Technology |
|-----------|------------|
| PDF Processing | PyMuPDF (fitz) |
| LLM | Azure OpenAI GPT-4.1 |
| Database | MongoDB Atlas |
| Language | Python 3.11+ |
| HTTP Client | httpx |
| Data Analysis | pandas |
| Environment | python-dotenv |

## Success Criteria

### Measurable Outcomes

- **SC-001**: System extracts at least 30 economic series from a standard 58-page ITR Trends Report.
- **SC-002**: Extraction accuracy for numerical values (forecasts, rates) exceeds 95%.
- **SC-003**: Chart metadata capture rate exceeds 90% of visible charts in PDF.
- **SC-004**: Processing time for a single PDF is under 3 minutes with LLM, under 30 seconds without.
- **SC-005**: MongoDB upsert operations complete without duplicates across multiple runs.
- **SC-006**: Generated reports include executive summary, all sectors, and forecast tables.
- **SC-007**: System handles 5+ PDFs in batch mode without memory issues or crashes.
- **SC-008**: LLM enhancement improves highlight extraction quality (measured by completeness of bullet points).
- **SC-009**: Consolidated documents contain 100% of extracted data from source PDF.
- **SC-010**: Downstream systems can query complete report data with single document fetch.

### Current Performance (v3.0.0)

| Metric | Result |
|--------|--------|
| PDFs Processed | 5 |
| Total Pages | 246 |
| Total Series Extracted | 117 |
| Charts with Vision Analysis | 665 |
| LLM Vision Interpretations | 665 |
| Flow Documents | 5 |
| Consolidated Documents | 5 |
| Sectors Covered | 4/4 (Core, Financial, Construction, Manufacturing) |

### Reports Processed

| Report | Period | Pages | Series | Charts | LLM Interpretations |
|--------|--------|-------|--------|--------|---------------------|
| DYMAX DEC 2021 ff.pdf | December 2021 | 48 | 9 | 155 | 155 |
| TR Complete March 2024.pdf | March 2024 | 58 | 31 | 158 | 158 |
| TR Complete July 2024.pdf | July 2024 | 57 | 34 | 152 | 152 |
| ITR Webinar July 2021.pdf | July 2021 | 29 | 6 | 134 | 134 |
| ITR Trends Report November 2025.pdf | November 2025 | 54 | 37 | 66 | 66 |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ITR_MONGODB_URI` | MongoDB connection string | localhost |
| `ITR_DATABASE_NAME` | Database name | ITRReports |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | (required) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | (configured) |
| `AZURE_OPENAI_API_VERSION` | API version | 2025-01-01-preview |

### MongoDB Collections

| Collection | Description | Documents |
|------------|-------------|-----------|
| `ITRextract_Flow` | **Flow-based documents with 665 vision interpretations** | 5 |
| `reports_consolidated` | Single document per PDF for downstream use | 5 |
| `reports` | Report metadata and executive summaries | 5 |
| `core_series` | Core economic indicators | 33 |
| `financial_series` | Financial market indicators | 26 |
| `construction_series` | Construction sector indicators | 23 |
| `manufacturing_series` | Manufacturing sector indicators | 36 |
| `charts` | Chart metadata (type, dimensions, page) | 289 |
| `forecast_tables` | Structured forecast tables | 29 |

### Consolidated Document Structure

```json
{
  "report_id": "tr_complete_march_2024",
  "pdf_filename": "TR Complete March 2024.pdf",
  "report_period": "March 2024",
  "metadata": {
    "page_count": 58,
    "extraction_timestamp": "...",
    "consolidated_timestamp": "..."
  },
  "executive_summary": {
    "author": "BRIAN BEAULIEU",
    "content": "..."
  },
  "statistics": {
    "total_series": 32,
    "series_by_sector": {"core": 9, "financial": 5, "construction": 7, "manufacturing": 11},
    "total_charts": 88,
    "total_forecast_tables": 0
  },
  "sectors": {
    "core": {"series_count": 9, "series": [...]},
    "financial": {"series_count": 5, "series": [...]},
    "construction": {"series_count": 7, "series": [...]},
    "manufacturing": {"series_count": 11, "series": [...]}
  },
  "charts": [...],
  "forecast_tables": [...],
  "series_index": {
    "all_series_names": ["ITR Leading Indicator", "US Industrial Production", ...],
    "by_sector": {"core": [...], "financial": [...], ...}
  }
}
```

## Usage

```bash
# === RECOMMENDED: Automated Workflow ===

# Process a single PDF through complete workflow
python workflow.py --pdf "Files/TR Complete March 2024.pdf"

# Process all PDFs in a directory
python workflow.py --dir Files/

# Watch directory for new PDFs (continuous monitoring)
python workflow.py --watch Files/

# Check workflow status
python workflow.py --status

# === Flow Document Creation (with Vision Analysis) ===

# Create flow documents for all PDFs
python create_flow_document.py

# Single PDF with vision analysis
python create_flow_document.py --pdf "Files/report.pdf"

# Without LLM (faster, no chart interpretations)
python create_flow_document.py --no-llm

# === Step-by-Step Processing ===

# Full extraction with LLM and MongoDB
python main_enhanced.py

# Import to MongoDB
python import_to_mongodb.py

# Create consolidated documents (one per PDF)
python create_consolidated_docs.py

# Without LLM (faster)
python main_enhanced.py --no-llm

# Without database (file output only)
python main_enhanced.py --no-db

# Show database statistics
python main_enhanced.py --stats
```

## Output Files

| File Pattern | Description |
|--------------|-------------|
| `*_enhanced_data.json` | Full extracted data with all context |
| `*_enhanced_report.txt` | Human-readable detailed report |
| `*_enhanced_summary.csv` | Tabular summary for spreadsheets |
| `*_charts_manifest.json` | Chart metadata for visualization |
| `*_forecast_tables.json` | Structured forecast tables |
| `*_consolidated.json` | Single document per PDF (in output/consolidated/) |
| `*_flow.json` | Flow-based document with vision interpretations (in output/flow/) |

## Query Examples

```javascript
// === Consolidated Documents ===

// Get complete report by ID
db.reports_consolidated.findOne({report_id: "tr_complete_march_2024"})

// Get all series names from a report
db.reports_consolidated.findOne(
  {report_id: "tr_complete_march_2024"},
  {"series_index.all_series_names": 1}
)

// Get core sector data only
db.reports_consolidated.findOne(
  {report_id: "tr_complete_march_2024"},
  {"sectors.core": 1}
)

// Find reports by period
db.reports_consolidated.find({report_period: "March 2024"})

// === Flow Documents (with Vision Analysis) ===

// Get flow document with chart interpretations
db.ITRextract_Flow.findOne({report_id: "itr_trends_report_november_2025"})

// Get all chart interpretations for a report
db.ITRextract_Flow.aggregate([
  {$match: {report_id: "itr_trends_report_november_2025"}},
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {"document_flow.blocks.block_type": "chart"}},
  {$project: {
    series: "$document_flow.series_name",
    chart_type: "$document_flow.blocks.content.chart_type",
    interpretation: "$document_flow.blocks.interpretation",
    trend: "$document_flow.blocks.metadata.trend_direction"
  }}
])

// Find charts showing declining trends
db.ITRextract_Flow.aggregate([
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {"document_flow.blocks.interpretation.trend_direction": "falling"}},
  {$project: {
    report_id: 1,
    series: "$document_flow.series_name",
    implications: "$document_flow.blocks.interpretation.business_implications"
  }}
])

// Get series in recession phase (D)
db.ITRextract_Flow.aggregate([
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {"document_flow.blocks.interpretation.current_phase": "D"}},
  {$project: {
    report_id: 1,
    series: "$document_flow.series_name",
    description: "$document_flow.blocks.interpretation.description"
  }}
])
```

## Completed Enhancements (v3.0.0)

1. **Vision-Based Chart Analysis**: GPT-4 Vision interprets all 665 charts with trend analysis
2. **Flow-Based Documents**: Preserve PDF reading order for downstream LLM consumption
3. **Automated Workflow**: End-to-end processing with single command
4. **File Watcher**: Automatic processing when new PDFs are uploaded

## Future Enhancements

1. **Time Series Database**: Add InfluxDB or TimescaleDB for historical tracking
2. **API Layer**: REST/GraphQL API for data access
3. **Dashboard Integration**: Direct Tableau/PowerBI connectors
4. **Comparison Reports**: Cross-period analysis and trend detection
5. **Alert System**: Notifications for significant forecast changes
6. **Vector Embeddings**: Semantic search across report content
7. **Chart Image Storage**: Store extracted chart images in blob storage
