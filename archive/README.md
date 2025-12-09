# Archive

This folder contains obsolete scripts and modules that have been superseded by newer implementations.

## Archived Files

### Scripts (`scripts/`)

| File | Replaced By | Notes |
|------|-------------|-------|
| `main.py` | `workflow.py` | Basic extraction script, superseded by automated workflow |
| `extract_pdf.py` | `create_flow_document.py` | Simple text extraction utility |

### Source Modules (`src/`)

| File | Replaced By | Notes |
|------|-------------|-------|
| `parser.py` | `enhanced_parser.py`, `flow_extractor.py` | Basic PDF parser without context |
| `analyzer.py` | `enhanced_analyzer.py` | Basic analysis without full reporting |

## Current Recommended Scripts

- **`workflow.py`** - Automated end-to-end processing (recommended)
- **`create_flow_document.py`** - Flow-based extraction with GPT-4 Vision
- **`main_enhanced.py`** - Enhanced extraction with LLM
- **`import_to_mongodb.py`** - MongoDB import utility
- **`create_consolidated_docs.py`** - Consolidated document generator

## Note

These files are kept for reference and backwards compatibility. They may be removed in future versions.
