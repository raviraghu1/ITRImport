# ITRImport

**ITR Economics Data Import & Analysis System**

Extract, analyze, and store economic data from ITR Economics Trends Report PDFs with AI-powered enhancement.

## Features

- **Automated Workflow**: End-to-end processing with a single command
- **File Watcher**: Automatic processing when new PDFs are uploaded
- **PDF Data Extraction**: Extract 30+ economic series from ITR Trends Reports
- **Chart & Table Context**: Capture chart metadata and forecast tables
- **LLM Enhancement**: Azure OpenAI GPT-4 for intelligent content extraction
- **MongoDB Storage**: Organized by sector with idempotent upserts
- **Consolidated Documents**: Single document per PDF for downstream use
- **Multi-Format Export**: JSON, CSV, and detailed text reports

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your MongoDB and Azure OpenAI credentials

# === RECOMMENDED: Use the Workflow (End-to-End Processing) ===

# Process a single PDF through complete workflow
python workflow.py --pdf "Files/TR Complete March 2024.pdf"

# Process all PDFs in a directory
python workflow.py --dir Files/

# Watch directory for new PDFs (continuous monitoring)
python workflow.py --watch Files/

# Process without LLM (faster)
python workflow.py --pdf "Files/report.pdf" --no-llm

# Check workflow status
python workflow.py --status

# === Alternative: Step-by-Step Processing ===

# Step 1: Extract from PDFs
python main_enhanced.py

# Step 2: Import to MongoDB
python import_to_mongodb.py

# Step 3: Create consolidated documents
python create_consolidated_docs.py
```

## Workflow Pipeline

The `workflow.py` script provides automated end-to-end processing:

```
PDF Upload → Extraction → LLM Enhancement → MongoDB Storage → Consolidation → Reports
```

### Pipeline Steps

1. **PDF Extraction** (PyMuPDF) - Extract text, charts, tables, and metadata
2. **LLM Enhancement** (Azure OpenAI GPT-4) - Intelligent content extraction
3. **Report Generation** - JSON, CSV, TXT outputs
4. **MongoDB Storage** - Store in sector-specific collections
5. **Consolidation** - Create single document per PDF for downstream use

### Watch Mode

For continuous processing of uploaded files:

```bash
# Watch the Files/ directory for new PDFs
python workflow.py --watch Files/

# With custom poll interval (default: 10 seconds)
python workflow.py --watch Files/ --poll-interval 30
```

When a new PDF is uploaded, the workflow automatically:
- Detects the new file
- Processes through complete pipeline
- Stores results in MongoDB
- Creates consolidated document
- Generates all output reports

## Output Files

| File | Description |
|------|-------------|
| `*_enhanced_data.json` | Full extracted data with context |
| `*_enhanced_report.txt` | Human-readable analysis report |
| `*_enhanced_summary.csv` | Tabular summary for spreadsheets |
| `*_charts_manifest.json` | Chart metadata for visualization |
| `*_forecast_tables.json` | Structured forecast tables |
| `*_consolidated.json` | Single document per PDF (in output/consolidated/) |

## MongoDB Collections

### Database: `ITRReports`

| Collection | Description |
|------------|-------------|
| `reports_consolidated` | **Single document per PDF for downstream use** |
| `reports` | Report metadata and executive summaries |
| `core_series` | Core economic indicators |
| `financial_series` | Financial market indicators |
| `construction_series` | Construction sector indicators |
| `manufacturing_series` | Manufacturing sector indicators |
| `charts` | Chart metadata (type, dimensions, page) |
| `forecast_tables` | Structured forecast tables |

### Consolidated Document Structure

Each document in `reports_consolidated` contains all data from one PDF:

```json
{
  "report_id": "tr_complete_march_2024",
  "pdf_filename": "TR Complete March 2024.pdf",
  "report_period": "March 2024",
  "metadata": { ... },
  "executive_summary": { ... },
  "statistics": {
    "total_series": 32,
    "series_by_sector": {"core": 9, "financial": 5, ...},
    "total_charts": 88
  },
  "sectors": {
    "core": {"series_count": 9, "series": [...]},
    "financial": {"series_count": 5, "series": [...]},
    ...
  },
  "charts": [...],
  "forecast_tables": [...],
  "series_index": {
    "all_series_names": [...],
    "by_sector": {...}
  }
}
```

### Query Examples

```javascript
// Get complete report
db.reports_consolidated.findOne({report_id: "tr_complete_march_2024"})

// Get all series names
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
```

## Project Structure

```
ITRImport/
├── workflow.py                # Automated end-to-end workflow (RECOMMENDED)
├── main_enhanced.py           # Main extraction entry point
├── import_to_mongodb.py       # Import data to MongoDB
├── create_consolidated_docs.py # Create single doc per PDF
├── src/
│   ├── models.py              # Data models
│   ├── enhanced_parser.py     # PDF parsing with context
│   ├── llm_extractor.py       # Azure OpenAI integration
│   ├── database.py            # MongoDB operations
│   └── enhanced_analyzer.py   # Reports and exports
├── output/                    # Generated files
│   └── consolidated/          # Consolidated JSON files
├── Files/                     # Source PDFs (upload here)
└── specs/                     # Documentation
```

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `ITR_MONGODB_URI` | MongoDB connection string |
| `ITR_DATABASE_NAME` | Database name (default: ITRReports) |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |

## Documentation

- [Feature Specification](specs/itr-import/spec.md)
- [Implementation Plan](specs/itr-import/plan.md)
- [Project Constitution](.specify/memory/constitution.md)

## Current Results

| Metric | Value |
|--------|-------|
| PDFs Processed | 5 |
| Series Extracted | 118 |
| Charts Captured | 289 |
| Forecast Tables | 29 |
| Consolidated Documents | 5 |
| Total MongoDB Documents | 446 |
| Sectors | Core, Financial, Construction, Manufacturing |

### Reports Processed

| Report | Period | Series | Charts |
|--------|--------|--------|--------|
| DYMAX DEC 2021 ff.pdf | December 2021 | 10 | 39 |
| TR Complete March 2024.pdf | March 2024 | 32 | 88 |
| TR Complete July 2024.pdf | July 2024 | 36 | 102 |
| ITR Webinar July 2021.pdf | - | 6 | 26 |
| ITR Trends Report November 2025.pdf | November 2025 | 34 | 34 |

## License

Proprietary - Internal Use Only
