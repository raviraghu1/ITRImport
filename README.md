# ITRImport

**ITR Economics Data Import & Analysis System** | v3.0.0

Extract, analyze, and store economic data from ITR Economics Trends Report PDFs with AI-powered enhancement and GPT-4 Vision chart interpretation.

> **665 charts analyzed** across 5 reports with full LLM vision interpretations

## Features

- **REST API**: FastAPI server for portal integration with async processing
- **Automated Workflow**: End-to-end processing with a single command
- **File Watcher**: Automatic processing when new PDFs are uploaded
- **PDF Data Extraction**: Extract 30+ economic series from ITR Trends Reports
- **Chart & Table Context**: Capture chart metadata and forecast tables
- **LLM Enhancement**: Azure OpenAI GPT-4 for intelligent content extraction
- **Vision-Based Chart Analysis**: GPT-4 Vision interprets charts with trend analysis
- **Flow-Based Documents**: Preserve PDF context flow for better LLM understanding
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

# Create flow-based documents with vision analysis
python create_flow_document.py

# === API Server (for portal integration) ===

# Start the API server
python api.py

# Or with uvicorn directly
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

## Report Viewer

The `viewer/` directory contains a web application for viewing and analyzing reports.

### Start the Viewer

```bash
python viewer/server.py
# Open http://localhost:8080
```

### Viewer Features

- **Side-by-Side View**: PDF displayed alongside extracted data
- **LLM Analysis Tab**: View all GPT-4 Vision chart interpretations
- **Page Linking**: Click to jump to specific PDF pages
- **Ask AI**: Compare extracted data with PDF, analyze trends
- **Quick Prompts**: One-click analysis queries

### Ask AI Examples

- "Compare the extracted series with the PDF"
- "What are the key economic trends?"
- "Which series are in recession phase?"
- "Summarize the forecast outlook"
- "Are there any discrepancies in the extracted data?"

## REST API

The `api.py` provides a FastAPI server for portal integration.

### Start the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python api.py
# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload PDF and process synchronously |
| `POST` | `/upload/async` | Upload PDF and process asynchronously |
| `GET` | `/status/{job_id}` | Check async job status |
| `GET` | `/reports` | List all processed reports |
| `GET` | `/reports/{id}` | Get specific report data |
| `GET` | `/reports/{id}/charts` | Get all chart interpretations |
| `GET` | `/reports/{id}/series` | Get all series from report |
| `DELETE` | `/reports/{id}` | Delete a report |
| `GET` | `/health` | Health check |

### Example: Upload PDF (Sync)

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Files/TR Complete March 2024.pdf"
```

Response:
```json
{
  "success": true,
  "message": "PDF processed successfully",
  "report_id": "tr_complete_march_2024",
  "filename": "TR Complete March 2024.pdf",
  "statistics": {
    "total_pages": 58,
    "total_series": 31,
    "total_charts": 158,
    "llm_interpretations": 158
  }
}
```

### Example: Upload PDF (Async)

```bash
# Upload and get job ID
curl -X POST "http://localhost:8000/upload/async" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Files/TR Complete March 2024.pdf"

# Response: {"job_id": "abc123...", "status_url": "/status/abc123..."}

# Check status
curl "http://localhost:8000/status/abc123..."
```

### Example: JavaScript/TypeScript

```typescript
// Upload PDF from portal
async function uploadPDF(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/upload/async', {
    method: 'POST',
    body: formData
  });

  return response.json();
}

// Check job status
async function checkStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`http://localhost:8000/status/${jobId}`);
  return response.json();
}

// Get all reports
async function getReports(): Promise<Report[]> {
  const response = await fetch('http://localhost:8000/reports');
  return response.json();
}
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ITRImport System                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   PDF File  │────▶│              Processing Pipeline                  │  │
│  │  (Upload)   │     │                                                   │  │
│  └─────────────┘     │  ┌────────────┐   ┌────────────┐   ┌──────────┐  │  │
│                      │  │  PyMuPDF   │──▶│    LLM     │──▶│  Vision  │  │  │
│                      │  │ Extraction │   │Enhancement │   │ Analysis │  │  │
│                      │  └────────────┘   └────────────┘   └──────────┘  │  │
│                      └──────────────────────────┬───────────────────────┘  │
│                                                 │                          │
│                      ┌──────────────────────────┼──────────────────────┐   │
│                      │                          ▼                      │   │
│                      │              ┌───────────────────┐              │   │
│                      │              │    MongoDB Atlas   │              │   │
│                      │              └─────────┬─────────┘              │   │
│                      │    ┌─────────────┬─────┴─────┬─────────────┐    │   │
│                      │    ▼             ▼           ▼             ▼    │   │
│                      │ ┌──────┐   ┌──────────┐  ┌──────┐   ┌────────┐ │   │
│                      │ │ Flow │   │Consolidated│ │Sector│   │ Charts │ │   │
│                      │ │ Docs │   │   Docs    │  │Series│   │Metadata│ │   │
│                      │ └──────┘   └──────────┘  └──────┘   └────────┘ │   │
│                      └────────────────────────────────────────────────┘   │
│                                                 │                          │
│                      ┌──────────────────────────┼──────────────────────┐   │
│                      │            Output Files  ▼                      │   │
│                      │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────┐ │   │
│                      │  │ JSON │  │ CSV  │  │ TXT  │  │ Flow + Vision│ │   │
│                      │  └──────┘  └──────┘  └──────┘  └──────────────┘ │   │
│                      └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Design

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Parser | PyMuPDF (fitz) | Extract text, images, and structure from PDFs |
| LLM Extractor | Azure OpenAI GPT-4 | Intelligent content extraction and structuring |
| Vision Analyzer | GPT-4 Vision | Interpret chart images with trend analysis |
| Flow Extractor | Custom Python | Preserve PDF reading order and context |
| Database | MongoDB Atlas | Store structured data with sector collections |
| Analyzer | pandas | Generate reports and exports |

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  PDF File   │────▶│ FlowExtractor│────▶│ LLMExtractor│────▶│ VisionAnalysis│
└─────────────┘     └──────────────┘     └─────────────┘     └──────┬───────┘
                                                                    │
                    ┌───────────────────────────────────────────────┘
                    ▼
              ┌──────────────┐     ┌─────────────────┐     ┌────────────┐
              │  MongoDB     │────▶│ ITRextract_Flow │────▶│ Downstream │
              │  Storage     │     │   Collection    │     │    LLMs    │
              └──────────────┘     └─────────────────┘     └────────────┘
```

## Workflow Pipeline

The `workflow.py` script provides automated end-to-end processing:

```
PDF Upload → Extraction → LLM Enhancement → Vision Analysis → MongoDB Storage → Reports
```

### Pipeline Steps

1. **PDF Extraction** (PyMuPDF) - Extract text, charts, tables, and metadata
2. **Flow Preservation** - Maintain reading order for context
3. **LLM Enhancement** (Azure OpenAI GPT-4) - Intelligent content extraction
4. **Vision Analysis** (GPT-4 Vision) - Interpret chart images with trends
5. **MongoDB Storage** - Store in sector-specific and flow collections
6. **Report Generation** - JSON, CSV, TXT, and flow document outputs

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
| `*_flow.json` | Flow-based document with vision interpretations (in output/flow/) |

## MongoDB Collections

### Database: `ITRReports`

| Collection | Description |
|------------|-------------|
| `ITRextract_Flow` | **Flow-based document with vision interpretations** |
| `reports_consolidated` | Single document per PDF for downstream use |
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

### Flow Document Structure

Each document in `ITRextract_Flow` preserves the PDF reading order with vision analysis:

```json
{
  "report_id": "itr_trends_report_november_2025",
  "pdf_filename": "ITR Trends Report November 2025.pdf",
  "report_period": "November 2025",
  "metadata": {
    "total_pages": 54,
    "total_charts": 66,
    "extraction_date": "2024-12-08T..."
  },
  "document_flow": [
    {
      "page_number": 1,
      "series_name": "US Industrial Production",
      "blocks": [
        {
          "block_type": "heading",
          "content": "US Industrial Production",
          "sequence_number": 1
        },
        {
          "block_type": "text",
          "content": "Overview text...",
          "sequence_number": 2
        },
        {
          "block_type": "chart",
          "content": {"chart_type": "rate_of_change", "width": 400, "height": 300},
          "interpretation": {
            "description": "Chart shows 12/12 rate-of-change...",
            "trend_direction": "rising",
            "current_phase": "A",
            "forecast_trend": "improving",
            "key_patterns": ["Recovery from 2023 low", "Accelerating growth"],
            "business_implications": "Consider inventory expansion...",
            "confidence": "high"
          },
          "sequence_number": 3
        }
      ]
    }
  ],
  "series_index": ["US Industrial Production", "US GDP", ...]
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

// Get flow document with chart interpretations
db.ITRextract_Flow.findOne({report_id: "itr_trends_report_november_2025"})

// Get all chart interpretations for a series
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

// Find all series in recession phase (D)
db.ITRextract_Flow.aggregate([
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {"document_flow.blocks.interpretation.current_phase": "D"}},
  {$project: {
    report_id: 1,
    series: "$document_flow.series_name",
    implications: "$document_flow.blocks.interpretation.business_implications"
  }}
])

// Get business implications for declining trends
db.ITRextract_Flow.aggregate([
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {"document_flow.blocks.interpretation.trend_direction": "falling"}},
  {$project: {
    series: "$document_flow.series_name",
    description: "$document_flow.blocks.interpretation.description",
    implications: "$document_flow.blocks.interpretation.business_implications"
  }}
])
```

## Project Structure

```
ITRImport/
├── api.py                     # FastAPI server for portal integration
├── workflow.py                # Automated end-to-end workflow (RECOMMENDED)
├── create_flow_document.py    # Flow-based extraction with vision
├── main_enhanced.py           # Main extraction entry point
├── import_to_mongodb.py       # Import data to MongoDB
├── create_consolidated_docs.py # Create single doc per PDF
├── viewer/                    # Web viewer application
│   ├── server.py              # Viewer FastAPI server
│   ├── templates/
│   │   └── index.html         # Main viewer page
│   └── static/
│       ├── css/styles.css     # Styling (matches portal design)
│       └── js/app.js          # Frontend JavaScript
├── src/
│   ├── models.py              # Data models
│   ├── enhanced_parser.py     # PDF parsing with context
│   ├── flow_extractor.py      # Flow-based extraction with context
│   ├── llm_extractor.py       # Azure OpenAI integration (+ Vision)
│   ├── database.py            # MongoDB operations
│   └── enhanced_analyzer.py   # Reports and exports
├── output/                    # Generated files
│   ├── consolidated/          # Consolidated JSON files
│   └── flow/                  # Flow-based JSON files
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
| Total Pages | 246 |
| Series Extracted | 117 |
| Charts with Vision Analysis | 665 |
| LLM Interpretations | 665 |
| Flow Documents | 5 |
| Consolidated Documents | 5 |
| Sectors | Core, Financial, Construction, Manufacturing |

### Reports Processed

| Report | Period | Pages | Series | Charts | LLM Interpretations |
|--------|--------|-------|--------|--------|---------------------|
| DYMAX DEC 2021 ff.pdf | December 2021 | 48 | 9 | 155 | 155 |
| TR Complete March 2024.pdf | March 2024 | 58 | 31 | 158 | 158 |
| TR Complete July 2024.pdf | July 2024 | 57 | 34 | 152 | 152 |
| ITR Webinar July 2021.pdf | July 2021 | 29 | 6 | 134 | 134 |
| ITR Trends Report November 2025.pdf | November 2025 | 54 | 37 | 66 | 66 |

### Flow Document Features

Each flow document in `ITRextract_Flow` contains:
- **Document Flow**: Content blocks in reading order (text, charts, tables, headings)
- **Vision Interpretations**: GPT-4 Vision analysis of each chart including:
  - Trend direction (rising/falling/stabilizing)
  - Business cycle phase (A/B/C/D)
  - Key patterns identified
  - Business implications
- **Series Index**: Quick lookup of all economic series
- **Metadata**: Page count, chart count, extraction timestamp

## License

Proprietary - Internal Use Only
