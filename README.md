# ITRImport

**ITR Economics Data Import & Analysis System**

Extract, analyze, and store economic data from ITR Economics Trends Report PDFs with AI-powered enhancement.

## Features

- **PDF Data Extraction**: Extract 30+ economic series from ITR Trends Reports
- **Chart & Table Context**: Capture chart metadata and forecast tables
- **LLM Enhancement**: Azure OpenAI GPT-4 for intelligent content extraction
- **MongoDB Storage**: Organized by sector with idempotent upserts
- **Multi-Format Export**: JSON, CSV, and detailed text reports

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your MongoDB and Azure OpenAI credentials

# Process all PDFs in Files/
python main_enhanced.py

# Process single PDF
python main_enhanced.py --pdf "Files/TR Complete March 2024.pdf"

# Without LLM (faster)
python main_enhanced.py --no-llm

# Without database
python main_enhanced.py --no-db

# Show database stats
python main_enhanced.py --stats
```

## Output Files

| File | Description |
|------|-------------|
| `*_enhanced_data.json` | Full extracted data with context |
| `*_enhanced_report.txt` | Human-readable analysis report |
| `*_enhanced_summary.csv` | Tabular summary for spreadsheets |
| `*_charts_manifest.json` | Chart metadata for visualization |
| `*_forecast_tables.json` | Structured forecast tables |

## Project Structure

```
ITRImport/
├── main_enhanced.py       # Main entry point
├── src/
│   ├── models.py          # Data models
│   ├── enhanced_parser.py # PDF parsing with context
│   ├── llm_extractor.py   # Azure OpenAI integration
│   ├── database.py        # MongoDB operations
│   └── enhanced_analyzer.py # Reports and exports
├── output/                # Generated files
├── Files/                 # Source PDFs
└── specs/                 # Documentation
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
| Sectors | Core, Financial, Construction, Manufacturing |

## License

Proprietary - Internal Use Only
