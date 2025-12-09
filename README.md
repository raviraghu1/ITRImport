# ITRImport

**ITR Economics Data Import & Analysis System** | v3.1.0

Extract, analyze, and interactively explore economic data from ITR Economics Trends Report PDFs with AI-powered enhancement, GPT-4 Vision chart interpretation, and an intelligent report viewer.

> **665 charts analyzed** across 5 reports with full LLM vision interpretations

---

## The Story

### Background

ITR Economics produces comprehensive Trends Reports - detailed PDF documents containing economic forecasts, business cycle analysis, and sector-specific indicators. These reports are invaluable for business planning but are challenging to:

1. **Search and Query** - Data is locked in PDF format
2. **Compare Across Reports** - Manual effort to track trends over time
3. **Extract Insights** - Charts require expert interpretation
4. **Integrate with Systems** - No API or structured data access

### Solution

ITRImport transforms these PDF reports into a powerful, queryable knowledge base with AI-powered analysis:

```
PDF Reports → Intelligent Extraction → MongoDB Storage → Interactive Viewer
                     ↓
              GPT-4 Vision analyzes every chart
              LLM extracts structured data
              Preserves document reading flow
```

### What Makes This Different

- **Vision-Based Chart Analysis**: Every chart is interpreted by GPT-4 Vision, providing trend direction, business cycle phase, and actionable implications
- **Flow Preservation**: Unlike simple text extraction, we preserve the reading order and context of the original document
- **Interactive AI Analysis**: Analysts can query reports naturally, compare data, and get AI-generated insights on demand
- **Save & Build Knowledge**: Analysis can be saved to pages, building an institutional knowledge layer

---

## Features

### Core Extraction
- **PDF Data Extraction**: Extract 30+ economic series from ITR Trends Reports
- **Chart & Table Context**: Capture chart metadata and forecast tables
- **LLM Enhancement**: Azure OpenAI GPT-4 for intelligent content extraction
- **Vision-Based Chart Analysis**: GPT-4 Vision interprets charts with trend analysis
- **Flow-Based Documents**: Preserve PDF context flow for better LLM understanding

### Storage & Integration
- **MongoDB Storage**: Organized by sector with idempotent upserts
- **REST API**: FastAPI server for portal integration with async processing
- **Consolidated Documents**: Single document per PDF for downstream use
- **Multi-Format Export**: JSON, CSV, and detailed text reports

### Interactive Viewer (NEW in v3.1)
- **Side-by-Side View**: PDF displayed alongside extracted data
- **Ask AI Chat**: Natural language queries about report content
- **Analyze with AI**: Multi-page analysis with custom context
- **Save Analyses**: Build institutional knowledge by saving insights to pages
- **View Full Analysis**: Popup modals for saved analysis review
- **Orange Scrollbars**: Enhanced visibility throughout the interface

---

## Use Cases

### 1. Quarterly Business Review Preparation

**Scenario**: Finance team needs to prepare for quarterly planning meeting

**Workflow**:
1. Upload latest ITR Trends Report to the viewer
2. Use "Analyze with AI" to select key indicator pages
3. Choose "Forecast Analysis" type
4. Add context: "Focus on construction sector for Q1 2026 budget planning"
5. Save analysis to relevant pages for team review
6. Export insights for presentation

### 2. Risk Monitoring Dashboard

**Scenario**: Risk management team monitors economic indicators weekly

**Workflow**:
1. Query MongoDB for all series in "recession phase" (Phase D)
2. Review GPT-4 Vision interpretations for declining trends
3. Use "Risk Analysis" in viewer to identify warning signs
4. Save risk assessments to pages with analyst context
5. Compare across multiple reports to track trend changes

### 3. Sales Forecasting Support

**Scenario**: Sales team needs economic backdrop for territory planning

**Workflow**:
1. Open report in viewer, navigate to relevant sector
2. Use Ask AI: "What are the key trends affecting manufacturing demand?"
3. Run multi-page analysis on sector overview pages
4. Add context: "Our customers are primarily in automotive and machinery"
5. Export analysis for sales kickoff presentation

### 4. Investment Committee Briefing

**Scenario**: Portfolio manager prepares economic overview for IC meeting

**Workflow**:
1. Process multiple ITR reports through the pipeline
2. Use MongoDB queries to compare indicators across time periods
3. In viewer, analyze pages covering financial markets
4. Use "Opportunities" analysis type to identify positive trends
5. Combine with "Risks" analysis for balanced view
6. Save comprehensive analysis to share with committee

### 5. Automated Report Processing

**Scenario**: Operations wants hands-off processing of new reports

**Workflow**:
1. Set up watch mode: `python workflow.py --watch Files/`
2. New PDFs dropped in folder are automatically processed
3. All charts analyzed by GPT-4 Vision
4. Data stored in MongoDB, accessible via API
5. Viewer immediately reflects new reports

### 6. Custom Research Queries

**Scenario**: Economist needs specific data point comparisons

**Workflow**:
```javascript
// Find all series showing recovery patterns
db.ITRextract_Flow.aggregate([
  {$unwind: "$document_flow"},
  {$unwind: "$document_flow.blocks"},
  {$match: {
    "document_flow.blocks.interpretation.current_phase": "A",
    "document_flow.blocks.interpretation.trend_direction": "rising"
  }},
  {$project: {
    series: "$document_flow.series_name",
    implications: "$document_flow.blocks.interpretation.business_implications"
  }}
])
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/ITRImport.git
cd ITRImport

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your MongoDB and Azure OpenAI credentials
```

### Process Reports

```bash
# Process a single PDF through complete workflow
python workflow.py --pdf "Files/TR Complete March 2024.pdf"

# Process all PDFs in a directory
python workflow.py --dir Files/

# Watch directory for new PDFs (continuous monitoring)
python workflow.py --watch Files/
```

### Start the Viewer

```bash
# Option 1: Direct Python
python viewer/server.py
# Open http://localhost:8081

# Option 2: Docker (recommended for production)
docker-compose up -d
# Open http://localhost:8081
```

---

## Report Viewer

The viewer provides an interactive interface for exploring and analyzing ITR reports.

### Main Interface

| Panel | Description |
|-------|-------------|
| **PDF Viewer** | Original PDF with page navigation |
| **Page Data** | Extracted text, chart analysis, saved AI analyses |
| **Analysis Tab** | Generate summaries, export PDFs |
| **Overview Tab** | Report metadata and statistics |
| **Series Tab** | All economic series from report |
| **LLM Analysis Tab** | GPT-4 Vision chart interpretations |
| **Ask AI Panel** | Chat interface for natural language queries |

### Analyze with AI Feature

1. Click **"Analyze with AI"** button
2. **Select Pages**: Choose which pages to include in analysis
3. **Analysis Type**:
   - General Analysis - Comprehensive overview
   - Comparison - Compare series and indicators
   - Forecast Analysis - Outlook and predictions
   - Risk Analysis - Warning signs and concerns
   - Opportunities - Positive indicators
4. **Add Context**: Provide analyst-specific context (optional)
5. **Run Analysis**: AI processes selected pages
6. **Save to Page**: Store analysis for future reference

### Saved Analyses

- Analyses are saved to the page they were triggered from
- View with **"View Full Analysis"** popup
- Options to **Replace** or **Append** when page has existing analysis
- **Copy to Clipboard** for easy sharing
- Orange scrollbars for easy navigation when multiple analyses exist

### Ask AI Examples

- "Compare the extracted series with the PDF"
- "What are the key economic trends?"
- "Which series are in recession phase?"
- "Summarize the forecast outlook"
- "What are the risks for manufacturing sector?"

---

## Docker Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Docker Configuration

```yaml
# docker-compose.yml
services:
  itr-viewer:
    build: .
    ports:
      - "8081:8081"
    environment:
      - ITR_MONGODB_URI=${ITR_MONGODB_URI}
      - AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
    volumes:
      - ./Files:/app/Files
      - ./output:/app/output
```

---

## REST API

The `api.py` provides a FastAPI server for portal integration.

### Start the Server

```bash
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

### Viewer API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/reports` | List reports with metadata |
| `GET` | `/api/reports/{id}` | Get full report with flow data |
| `GET` | `/api/reports/{id}/pdf` | Serve PDF file |
| `POST` | `/api/reports/{id}/ask` | Ask AI about report |
| `POST` | `/api/reports/{id}/analyze-pages` | Run multi-page AI analysis |
| `POST` | `/api/reports/{id}/save-page-analysis` | Save analysis to page |
| `GET` | `/api/reports/{id}/page/{num}/analysis` | Get saved analyses for page |

---

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
│  ┌──────────────────────────────────────────────┼──────────────────────┐   │
│  │                    Interactive Viewer        ▼                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │  PDF View   │  │  Page Data  │  │  Ask AI     │  │  Analyze   │ │   │
│  │  │  (iframe)   │  │  + Analyses │  │  (Chat)     │  │  with AI   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

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

### Flow Document Structure

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
      "extracted_text": "Full page text...",
      "summary": "AI-generated summary...",
      "custom_analysis": [
        {
          "analysis_type": "forecast",
          "content": "Saved analysis content...",
          "pages_analyzed": [1, 2, 3],
          "analyst_context": "Focus on Q1 planning",
          "timestamp": "2024-12-09T16:08:00Z"
        }
      ],
      "blocks": [
        {
          "block_type": "chart",
          "interpretation": {
            "description": "Chart shows 12/12 rate-of-change...",
            "trend_direction": "rising",
            "current_phase": "A",
            "business_implications": "Consider inventory expansion..."
          }
        }
      ]
    }
  ]
}
```

---

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `ITR_MONGODB_URI` | MongoDB connection string |
| `ITR_DATABASE_NAME` | Database name (default: ITRReports) |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ITR_VIEWER_PORT` | Viewer server port | 8081 |
| `ITR_VIEWER_HOST` | Viewer server host | 0.0.0.0 |
| `AZURE_API_VERSION` | Azure OpenAI API version | 2024-02-15-preview |

---

## Project Structure

```
ITRImport/
├── api.py                     # FastAPI server for portal integration
├── workflow.py                # Automated end-to-end workflow
├── create_flow_document.py    # Flow-based extraction with vision
├── main_enhanced.py           # Main extraction entry point
├── import_to_mongodb.py       # Import data to MongoDB
├── create_consolidated_docs.py # Create single doc per PDF
├── Dockerfile                 # Docker build configuration
├── docker-compose.yml         # Docker Compose configuration
├── viewer/                    # Web viewer application
│   ├── server.py              # Viewer FastAPI server
│   ├── templates/
│   │   └── index.html         # Main viewer page
│   └── static/
│       ├── css/styles.css     # Styling with orange accents
│       └── js/app.js          # Frontend JavaScript
├── src/
│   ├── models.py              # Data models
│   ├── enhanced_parser.py     # PDF parsing with context
│   ├── flow_extractor.py      # Flow-based extraction
│   ├── llm_extractor.py       # Azure OpenAI integration (+ Vision)
│   ├── database.py            # MongoDB operations
│   └── enhanced_analyzer.py   # Reports and exports
├── output/                    # Generated files
│   ├── consolidated/          # Consolidated JSON files
│   └── flow/                  # Flow-based JSON files
├── Files/                     # Source PDFs (upload here)
└── specs/                     # Documentation
```

---

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

### Reports Processed

| Report | Period | Pages | Series | Charts |
|--------|--------|-------|--------|--------|
| DYMAX DEC 2021 ff.pdf | December 2021 | 48 | 9 | 155 |
| TR Complete March 2024.pdf | March 2024 | 58 | 31 | 158 |
| TR Complete July 2024.pdf | July 2024 | 57 | 34 | 152 |
| ITR Webinar July 2021.pdf | July 2021 | 29 | 6 | 134 |
| ITR Trends Report November 2025.pdf | November 2025 | 54 | 37 | 66 |

---

## Changelog

### v3.1.0 (2024-12-09)
- **Analyze with AI**: Multi-page analysis with custom context
- **Save Analysis**: Store insights to pages with append/replace options
- **View Full Analysis**: Modal popup for saved analysis review
- **Post-Save Navigation**: Options to continue analysis or go to page
- **Proportional Windows**: Balanced layout for extracted text and analyses
- **Orange Scrollbars**: Enhanced visibility throughout interface
- **Docker Support**: Production-ready containerized deployment

### v3.0.0 (2024-12-08)
- **Report Viewer**: Side-by-side PDF and extracted data view
- **Ask AI Chat**: Natural language queries about reports
- **LLM Analysis Tab**: View all GPT-4 Vision interpretations
- **Page Linking**: Navigate PDF from extracted data

### v2.0.0
- **Vision Analysis**: GPT-4 Vision for chart interpretation
- **Flow Documents**: Preserve PDF reading order
- **Business Implications**: AI-generated actionable insights

### v1.0.0
- Initial extraction pipeline
- MongoDB storage
- Basic PDF parsing

---

## License

Proprietary - Internal Use Only
