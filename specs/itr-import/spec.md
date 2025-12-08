# Feature Specification: ITR Economics Data Import & Analysis System

**Feature Branch**: `main`
**Created**: 2025-12-08
**Status**: Implemented
**Version**: 2.0.0

## Overview

ITRImport is a comprehensive data extraction and analysis system for ITR Economics Trends Report PDFs. The system extracts economic indicators, forecasts, charts, and contextual information from PDF reports, stores them in MongoDB, and provides analysis capabilities powered by Azure OpenAI GPT-4.

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

#### Data Storage
- **FR-014**: System MUST store extracted data in MongoDB with sector-specific collections.
- **FR-015**: System MUST implement idempotent upsert operations using composite keys (series_id + report_period).
- **FR-016**: System MUST create indexes on date fields and series identifiers for query performance.
- **FR-017**: System MUST store report-level metadata including executive summary and page counts.

#### Output Generation
- **FR-018**: System MUST generate detailed text reports with executive summary, sector breakdown, and forecasts.
- **FR-019**: System MUST export data to JSON with full structure including charts and content.
- **FR-020**: System MUST export CSV summaries suitable for spreadsheet analysis.
- **FR-021**: System MUST generate charts manifest JSON for visualization integration.
- **FR-022**: System MUST generate forecast tables JSON for downstream processing.

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
┌───────────────┐              ┌─────────────────┐
│    Models     │              │   Collections   │
│ (Dataclasses) │              │ core_series     │
└───────────────┘              │ financial_series│
                               │ construction_*  │
                               │ manufacturing_* │
                               │ report_metadata │
                               └─────────────────┘
```

### Data Flow

1. **Input**: ITR Trends Report PDF files
2. **Extraction**: PyMuPDF extracts text, images, and structure
3. **Enhancement**: Azure OpenAI GPT-4 enriches extracted content
4. **Storage**: MongoDB stores structured data with indexes
5. **Output**: JSON, CSV, TXT reports for analysis and integration

### Technology Stack

| Component | Technology |
|-----------|------------|
| PDF Processing | PyMuPDF (fitz) |
| LLM | Azure OpenAI GPT-4.1 |
| Database | MongoDB Atlas |
| Language | Python 3.11+ |
| HTTP Client | httpx |
| Data Analysis | pandas |

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

### Current Performance (v2.0.0)

| Metric | Result |
|--------|--------|
| PDFs Processed | 5 |
| Total Series Extracted | 118 |
| Total Charts Captured | 289 |
| Forecast Tables Extracted | 29 |
| LLM Enhanced Series | 118 (100%) |
| MongoDB Documents | 123 |
| Sectors Covered | 4/4 (Core, Financial, Construction, Manufacturing) |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ITR_MONGODB_URI` | MongoDB connection string | localhost |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | (configured) |

### MongoDB Collections

| Collection | Description |
|------------|-------------|
| `core_series` | Core economic indicators |
| `financial_series` | Financial market indicators |
| `construction_series` | Construction sector indicators |
| `manufacturing_series` | Manufacturing sector indicators |
| `report_metadata` | Report-level metadata and summaries |

## Usage

```bash
# Full extraction with LLM and MongoDB
python main_enhanced.py

# Process single PDF
python main_enhanced.py --pdf "Files/TR Complete March 2024.pdf"

# Without LLM (faster)
python main_enhanced.py --no-llm

# Without database (file output only)
python main_enhanced.py --no-db

# Show database statistics
python main_enhanced.py --stats

# Quiet mode (minimal output)
python main_enhanced.py --quiet
```

## Output Files

| File Pattern | Description |
|--------------|-------------|
| `*_enhanced_data.json` | Full extracted data with all context |
| `*_enhanced_report.txt` | Human-readable detailed report |
| `*_enhanced_summary.csv` | Tabular summary for spreadsheets |
| `*_charts_manifest.json` | Chart metadata for visualization |
| `*_forecast_tables.json` | Structured forecast tables |

## Future Enhancements

1. **Image Extraction**: Extract actual chart images for archival/display
2. **Time Series Database**: Add InfluxDB or TimescaleDB for historical tracking
3. **API Layer**: REST/GraphQL API for data access
4. **Dashboard Integration**: Direct Tableau/PowerBI connectors
5. **Automated Scheduling**: Cron-based processing of new reports
6. **Comparison Reports**: Cross-period analysis and trend detection
7. **Alert System**: Notifications for significant forecast changes
