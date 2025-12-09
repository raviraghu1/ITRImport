# Implementation Plan: Enhanced LLM Analysis with Overall and Topic-Driven Insights

**Branch**: `001-llm-analysis-enhancement` | **Date**: 2025-12-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-llm-analysis-enhancement/spec.md`

## Summary

Enhance the existing LLM-powered PDF extraction pipeline to generate comprehensive overall document analysis and topic-driven (sector-level) insights. The enhancement will integrate synchronously into the existing `FlowExtractor` pipeline, extending the current `document_flow` and `series_index` data structures with new analysis entities. The viewer will receive a new "Analysis" tab displaying executive summaries, sector insights, and sentiment scores with full source traceability.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, PyMuPDF (fitz), httpx, pymongo, Pydantic, Jinja2
**Storage**: MongoDB (database: `ITRReports`, collection: `ITRextract_Flow`)
**Testing**: pytest (unit, integration, contract tests)
**Target Platform**: Linux/macOS server, Docker container
**Project Type**: Web application (Python backend + HTML/JS frontend)
**Performance Goals**: Analysis processing adds no more than 30% to total document processing time (SC-006); 5-second access time for viewing analysis (SC-001)
**Constraints**: Synchronous processing as per clarification; LLM calls must handle Azure OpenAI rate limits gracefully
**Scale/Scope**: Single-tenant deployment; ~50-100 reports per month; 4-5 sectors per report

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Data Fidelity | ✅ PASS | Analysis is additive synthesis; original extracted data preserved unchanged |
| II. Source Traceability | ✅ PASS | FR-017 requires linking all insights to source pages; analysis includes page references |
| III. Structured Data Model | ✅ PASS | New entities (OverallAnalysis, SectorAnalysis, SentimentScore) follow schema patterns |
| IV. Idempotent Processing | ✅ PASS | Re-processing same PDF with analysis regeneration produces identical results via upsert |
| V. Visualization Integrity | ✅ PASS | Analysis display uses consistent visual indicators (FR-018); no chart manipulation |
| VI. Test Coverage | ✅ PASS | Spec requires unit, integration, and contract tests per constitution |
| VII. Simplicity & Maintainability | ✅ PASS | Extending existing LLMExtractor/FlowExtractor; no new frameworks; type hints required |

**Gate Result**: PASS - All constitution principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-llm-analysis-enhancement/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API schemas)
│   ├── overall-analysis.json
│   ├── sector-analysis.json
│   └── analysis-export.json
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── models.py              # Existing: Add OverallAnalysis, SectorAnalysis, SentimentScore
├── llm_extractor.py       # Existing: Add analysis generation methods
├── flow_extractor.py      # Existing: Integrate analysis into document flow
├── analysis_generator.py  # NEW: Orchestrates overall + sector analysis generation
├── enhanced_analyzer.py   # Existing: Export enhancements
└── database.py            # Existing: No changes needed

viewer/
├── server.py              # Existing: Add /api/reports/{id}/analysis endpoint
├── static/
│   ├── css/styles.css     # Existing: Add analysis tab styles
│   └── js/app.js          # Existing: Add Analysis tab rendering
└── templates/
    └── index.html         # Existing: Add Analysis tab structure

api.py                     # Existing: Analysis included in sync response

tests/
├── unit/
│   ├── test_analysis_generator.py  # NEW
│   └── test_sentiment_score.py     # NEW
├── integration/
│   └── test_analysis_pipeline.py   # NEW
└── contract/
    └── test_analysis_schema.py     # NEW
```

**Structure Decision**: Web application structure - extending existing `src/` Python backend and `viewer/` frontend. No new project directories needed; all changes extend current modules.

## Complexity Tracking

> No constitution violations requiring justification.

| Aspect | Complexity | Rationale |
|--------|------------|-----------|
| New module | Low | Single `analysis_generator.py` orchestrator following existing patterns |
| LLM calls | Medium | 2-3 additional LLM calls per document (overall + per-sector summaries) |
| Data model | Low | 3 new Pydantic models extending existing patterns |
| UI changes | Low | One new tab reusing existing component patterns |

---

## Post-Design Constitution Re-Check

*Validation after Phase 1 design completion*

| Principle | Status | Design Validation |
|-----------|--------|-------------------|
| I. Data Fidelity | ✅ PASS | Data model preserves extracted values; analysis is LLM synthesis layer only |
| II. Source Traceability | ✅ PASS | `source_pages` field in Theme, SectorAnalysis, IndicatorSignal entities |
| III. Structured Data Model | ✅ PASS | JSON schemas defined in `contracts/`; Pydantic models with validators |
| IV. Idempotent Processing | ✅ PASS | Analysis stored via upsert; regeneration endpoint reuses extracted data |
| V. Visualization Integrity | ✅ PASS | Sentiment uses 5-point scale with clear labels; no misleading displays |
| VI. Test Coverage | ✅ PASS | Test files specified in project structure; contract tests validate schemas |
| VII. Simplicity & Maintainability | ✅ PASS | Single new module; extends existing patterns; type hints in Pydantic models |

**Post-Design Gate Result**: PASS - Design adheres to all constitution principles.

---

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Implementation Plan | `specs/001-llm-analysis-enhancement/plan.md` | ✅ Complete |
| Research | `specs/001-llm-analysis-enhancement/research.md` | ✅ Complete |
| Data Model | `specs/001-llm-analysis-enhancement/data-model.md` | ✅ Complete |
| API Contracts | `specs/001-llm-analysis-enhancement/contracts/` | ✅ Complete |
| Quickstart Guide | `specs/001-llm-analysis-enhancement/quickstart.md` | ✅ Complete |
| Agent Context | `CLAUDE.md` | ✅ Updated |

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks
2. Implement tasks in priority order (P1 stories first)
3. Run tests after each implementation phase
4. Validate against quickstart.md verification steps
