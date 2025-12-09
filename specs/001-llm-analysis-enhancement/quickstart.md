# Quickstart: Enhanced LLM Analysis

**Feature**: 001-llm-analysis-enhancement
**Date**: 2025-12-09

## Prerequisites

1. Python 3.11+ installed
2. MongoDB running locally or accessible
3. Azure OpenAI API key configured
4. Existing ITRImport environment set up

## Environment Setup

```bash
# Ensure you're on the feature branch
git checkout 001-llm-analysis-enhancement

# Install any new dependencies (if added)
pip install -r requirements.txt

# Verify environment variables
export AZURE_OPENAI_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/openai/deployments/gpt-4.1/chat/completions"
export ITR_MONGODB_URI="mongodb://localhost:27017"
export ITR_DATABASE_NAME="ITRReports"
```

## Quick Verification

### 1. Test Analysis Generator (Unit)

```bash
# Run unit tests for the new analysis generator
pytest tests/unit/test_analysis_generator.py -v

# Run sentiment score tests
pytest tests/unit/test_sentiment_score.py -v
```

### 2. Test API Endpoints

```bash
# Start the viewer server
python viewer/server.py &

# Test analysis endpoint (replace with actual report_id)
curl http://localhost:8081/api/reports/tr_complete_march_2024/analysis | jq .

# Test sentiment endpoint
curl http://localhost:8081/api/reports/tr_complete_march_2024/analysis/sentiment | jq .

# Test sector analysis
curl http://localhost:8081/api/reports/tr_complete_march_2024/analysis/sectors/core | jq .
```

### 3. Test Full Pipeline

```bash
# Process a PDF with analysis generation
python -c "
from pathlib import Path
from src.flow_extractor import FlowExtractor
from src.llm_extractor import LLMExtractor

pdf_path = Path('Files/TR Complete March 2024.pdf')
with LLMExtractor() as llm:
    with FlowExtractor(pdf_path, llm) as extractor:
        doc = extractor.extract_full_document_flow()

# Check analysis was generated
print('Overall Analysis:', 'overall_analysis' in doc)
print('Sector Analyses:', list(doc.get('sector_analyses', {}).keys()))
print('Sentiment Score:', doc.get('overall_analysis', {}).get('sentiment_score', {}).get('label'))
"
```

### 4. View in Browser

1. Open http://localhost:8081
2. Select a processed report
3. Click the **Analysis** tab
4. Verify:
   - Executive Summary displays
   - Sentiment score shows with visual indicator
   - Key themes are listed (5-10 items)
   - Sector navigation works
   - Clicking page references navigates PDF

## Key Files Modified

| File | Changes |
|------|---------|
| `src/models.py` | Added OverallAnalysis, SectorAnalysis, SentimentScore models |
| `src/llm_extractor.py` | Added `generate_overall_analysis()`, `generate_sector_analysis()`, `calculate_sentiment()` |
| `src/flow_extractor.py` | Integrated analysis generation into `extract_full_document_flow()` |
| `src/analysis_generator.py` | NEW - Orchestrates analysis generation |
| `viewer/server.py` | Added `/api/reports/{id}/analysis` endpoints |
| `viewer/static/js/app.js` | Added Analysis tab rendering |
| `viewer/static/css/styles.css` | Added Analysis tab styles |
| `viewer/templates/index.html` | Added Analysis tab structure |

## Expected Analysis Output Structure

```json
{
  "overall_analysis": {
    "executive_summary": "The March 2024 ITR Trends Report indicates...",
    "key_themes": [
      {
        "theme_name": "Manufacturing Slowdown",
        "significance_score": 8.5,
        "frequency": 15,
        "description": "Multiple manufacturing indicators...",
        "affected_sectors": ["manufacturing", "core"],
        "source_pages": [5, 12, 22],
        "business_implications": "Prepare for reduced demand..."
      }
    ],
    "cross_sector_trends": {
      "overall_direction": "mixed",
      "sectors_in_growth": ["financial"],
      "sectors_in_decline": ["manufacturing", "construction"],
      "sector_correlations": [...],
      "trend_summary": "The economy shows divergent patterns..."
    },
    "recommendations": [
      "Monitor leading indicators for phase transition signals",
      "Consider inventory reduction in manufacturing sectors",
      "Evaluate financial sector opportunities"
    ],
    "sentiment_score": {
      "score": 3,
      "label": "Neutral",
      "confidence": "medium",
      "contributing_factors": [...],
      "sector_weights": {
        "core": 0.35,
        "financial": 0.25,
        "construction": 0.20,
        "manufacturing": 0.20
      },
      "indicator_signals": [...],
      "rationale": "Mixed signals across sectors with..."
    }
  },
  "sector_analyses": {
    "core": { ... },
    "financial": { ... },
    "construction": { ... },
    "manufacturing": { ... }
  },
  "analysis_metadata": {
    "version": "1.0",
    "generated_at": "2025-12-09T10:00:00Z",
    "generator_version": "3.1.0",
    "llm_model": "gpt-4.1",
    "processing_time_seconds": 45.2
  }
}
```

## Troubleshooting

### Analysis Not Generated

1. Check LLM is initialized:
   ```bash
   curl http://localhost:8081/health | jq .llm
   ```
2. Verify Azure OpenAI key is set:
   ```bash
   echo $AZURE_OPENAI_KEY | head -c 10
   ```

### Sentiment Score Missing

Check that sector analyses were generated first - sentiment is calculated from sector data.

### Themes Not Appearing

Verify `key_insights` exists in page flows - themes are aggregated from these.

### Performance Issues

Analysis adds ~30% to processing time. For large PDFs:
- Check LLM timeout settings (default 60s)
- Consider processing in batches

## Next Steps

After verification:
1. Run full test suite: `pytest tests/ -v`
2. Process multiple PDFs to validate consistency
3. Compare analysis quality against manual review
4. Proceed to `/speckit.tasks` for implementation tasks
