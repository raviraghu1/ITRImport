# Tasks: Enhanced LLM Analysis with Overall and Topic-Driven Insights

**Input**: Design documents from `/specs/001-llm-analysis-enhancement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as the constitution requires test coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `src/` at repository root
- **Viewer Frontend**: `viewer/static/js/`, `viewer/static/css/`, `viewer/templates/`
- **API**: `api.py`, `viewer/server.py`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/contract/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test structure and ensure dependencies are in place

- [ ] T001 Create test directory structure: `tests/unit/`, `tests/integration/`, `tests/contract/`
- [ ] T002 [P] Verify Python 3.11+ and all dependencies in requirements.txt are installed
- [ ] T003 [P] Verify MongoDB connection and Azure OpenAI credentials are configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Data Models (Required by All Stories)

- [ ] T004 [P] Add ConfidenceLevel, TrendDirection, SentimentLabel enums to src/models.py
- [ ] T005 [P] Add ContributingFactor model to src/models.py
- [ ] T006 [P] Add IndicatorSignal model to src/models.py
- [ ] T007 [P] Add Correlation model to src/models.py
- [ ] T008 [P] Add Theme model to src/models.py
- [ ] T009 Add SentimentScore model with sector_weights validator to src/models.py
- [ ] T010 Add CrossSectorTrends model to src/models.py
- [ ] T011 Add SectorAnalysis model to src/models.py
- [ ] T012 Add OverallAnalysis model to src/models.py
- [ ] T013 Add AnalysisMetadata model to src/models.py

### Analysis Generator Module (Core Orchestrator)

- [ ] T014 Create src/analysis_generator.py with AnalysisGenerator class skeleton
- [ ] T015 Implement _aggregate_page_summaries() method in src/analysis_generator.py
- [ ] T016 Implement _aggregate_chart_interpretations() method in src/analysis_generator.py
- [ ] T017 Implement _group_series_by_sector() method in src/analysis_generator.py

### LLM Extractor Extensions

- [ ] T018 Add generate_overall_analysis() method to src/llm_extractor.py
- [ ] T019 Add generate_sector_analysis() method to src/llm_extractor.py
- [ ] T020 Add calculate_sentiment() method to src/llm_extractor.py
- [ ] T021 Add identify_themes() method to src/llm_extractor.py
- [ ] T022 Add identify_correlations() method to src/llm_extractor.py

### Pipeline Integration

- [ ] T023 Modify FlowExtractor.extract_full_document_flow() in src/flow_extractor.py to call analysis generator
- [ ] T024 Add overall_analysis, sector_analyses, analysis_metadata fields to document output in src/flow_extractor.py

**Checkpoint**: Foundation ready - Pydantic models defined, analysis generator skeleton in place, LLM methods stubbed

---

## Phase 3: User Story 1 - View Overall Document Analysis (Priority: P1)

**Goal**: Users can see comprehensive overall analysis including executive summary, key themes, cross-sector trends, recommendations, and sentiment score in a new "Analysis" tab

**Independent Test**: Upload any ITR PDF, view report in viewer, click "Analysis" tab, verify executive summary, themes, trends, recommendations, and sentiment score are displayed

### Tests for User Story 1

- [ ] T025 [P] [US1] Unit test for AnalysisGenerator.generate_overall_analysis() in tests/unit/test_analysis_generator.py
- [ ] T026 [P] [US1] Unit test for SentimentScore model validation in tests/unit/test_sentiment_score.py
- [ ] T027 [P] [US1] Contract test for /api/reports/{id}/analysis endpoint in tests/contract/test_analysis_schema.py
- [ ] T028 [US1] Integration test for overall analysis generation pipeline in tests/integration/test_analysis_pipeline.py

### Implementation for User Story 1

**Backend - Overall Analysis Generation**

- [ ] T029 [US1] Implement generate_overall_analysis() full logic in src/analysis_generator.py (calls LLM, returns OverallAnalysis)
- [ ] T030 [US1] Implement _generate_executive_summary() in src/analysis_generator.py
- [ ] T031 [US1] Implement _generate_recommendations() in src/analysis_generator.py
- [ ] T032 [US1] Implement theme identification and ranking in src/analysis_generator.py (uses identify_themes())
- [ ] T033 [US1] Implement cross-sector trend synthesis in src/analysis_generator.py (uses identify_correlations())
- [ ] T034 [US1] Implement sentiment score calculation in src/analysis_generator.py (uses calculate_sentiment())

**API Endpoints**

- [ ] T035 [US1] Add GET /api/reports/{report_id}/analysis endpoint to viewer/server.py
- [ ] T036 [P] [US1] Add GET /api/reports/{report_id}/analysis/overall endpoint to viewer/server.py
- [ ] T037 [P] [US1] Add GET /api/reports/{report_id}/analysis/sentiment endpoint to viewer/server.py
- [ ] T038 [P] [US1] Add GET /api/reports/{report_id}/analysis/themes endpoint to viewer/server.py

**Viewer Frontend - Analysis Tab**

- [ ] T039 [US1] Add "Analysis" tab button to viewer/templates/index.html
- [ ] T040 [US1] Add analysis tab content container structure to viewer/templates/index.html
- [ ] T041 [US1] Add renderAnalysisTab() function to viewer/static/js/app.js
- [ ] T042 [US1] Add renderExecutiveSummary() function to viewer/static/js/app.js
- [ ] T043 [US1] Add renderSentimentScore() with visual indicator to viewer/static/js/app.js
- [ ] T044 [US1] Add renderKeyThemes() with ranking display to viewer/static/js/app.js
- [ ] T045 [US1] Add renderCrossSectorTrends() to viewer/static/js/app.js
- [ ] T046 [US1] Add renderRecommendations() to viewer/static/js/app.js
- [ ] T047 [US1] Add source page linking (click to navigate PDF) to viewer/static/js/app.js
- [ ] T048 [US1] Add analysis tab styles to viewer/static/css/styles.css (sentiment indicator, theme cards, trend visualization)

**Checkpoint**: User Story 1 complete - Overall analysis visible in viewer with all components

---

## Phase 4: User Story 2 - Access Topic-Driven Analysis by Economic Sector (Priority: P1)

**Goal**: Users can navigate to specific sectors (core, financial, construction, manufacturing) and see dedicated analysis for each

**Independent Test**: Upload an ITR PDF, go to Analysis tab, select a sector from navigation, verify sector summary, phase distribution, leading indicators, and correlations are displayed

### Tests for User Story 2

- [ ] T049 [P] [US2] Unit test for AnalysisGenerator.generate_sector_analyses() in tests/unit/test_analysis_generator.py
- [ ] T050 [P] [US2] Contract test for /api/reports/{id}/analysis/sectors endpoint in tests/contract/test_analysis_schema.py
- [ ] T051 [US2] Integration test for sector analysis generation in tests/integration/test_analysis_pipeline.py

### Implementation for User Story 2

**Backend - Sector Analysis Generation**

- [ ] T052 [US2] Implement generate_sector_analyses() in src/analysis_generator.py (iterates sectors, calls LLM per sector)
- [ ] T053 [US2] Implement _calculate_phase_distribution() for each sector in src/analysis_generator.py
- [ ] T054 [US2] Implement _identify_leading_indicators() for each sector in src/analysis_generator.py
- [ ] T055 [US2] Implement _identify_sector_correlations() in src/analysis_generator.py
- [ ] T056 [US2] Implement _extract_sector_source_pages() in src/analysis_generator.py

**API Endpoints**

- [ ] T057 [US2] Add GET /api/reports/{report_id}/analysis/sectors endpoint to viewer/server.py
- [ ] T058 [US2] Add GET /api/reports/{report_id}/analysis/sectors/{sector} endpoint to viewer/server.py

**Viewer Frontend - Sector Navigation**

- [ ] T059 [US2] Add sector navigation component (tabs or dropdown) to viewer/static/js/app.js
- [ ] T060 [US2] Add renderSectorAnalysis() function to viewer/static/js/app.js
- [ ] T061 [US2] Add renderPhaseDistribution() with phase badges (A/B/C/D) to viewer/static/js/app.js
- [ ] T062 [US2] Add renderLeadingIndicators() to viewer/static/js/app.js
- [ ] T063 [US2] Add renderSectorCorrelations() with relationship visualization to viewer/static/js/app.js
- [ ] T064 [US2] Add renderSectorInsights() with source page links to viewer/static/js/app.js
- [ ] T065 [US2] Add sector navigation and display styles to viewer/static/css/styles.css
- [ ] T066 [US2] Handle edge case: sector with no data (display "No data available" message)

**Checkpoint**: User Story 2 complete - Sector analysis accessible via navigation

---

## Phase 5: User Story 3 - Export Analysis for Further Processing (Priority: P2)

**Goal**: Users can export complete analysis (overall + all sectors) in structured JSON format for downstream tools

**Independent Test**: Process a report, call export endpoint, verify JSON file downloads with all analysis sections parseable

### Tests for User Story 3

- [ ] T067 [P] [US3] Contract test for /api/reports/{id}/analysis/export endpoint in tests/contract/test_analysis_schema.py
- [ ] T068 [US3] Unit test for export schema validation in tests/unit/test_analysis_generator.py

### Implementation for User Story 3

**Backend - Export Functionality**

- [ ] T069 [US3] Add GET /api/reports/{report_id}/analysis/export endpoint to viewer/server.py
- [ ] T070 [US3] Implement export_analysis() method in src/analysis_generator.py (formats analysis per export schema)
- [ ] T071 [US3] Add Content-Disposition header for file download in export endpoint
- [ ] T072 [US3] Extend enhanced_analyzer.py export_to_json() to include analysis fields

**Viewer Frontend - Export Button**

- [ ] T073 [US3] Add "Export Analysis" button to Analysis tab in viewer/templates/index.html
- [ ] T074 [US3] Add exportAnalysis() function to viewer/static/js/app.js (triggers download)
- [ ] T075 [US3] Add export button styles to viewer/static/css/styles.css

**Checkpoint**: User Story 3 complete - Analysis exportable in JSON format

---

## Phase 6: FR-014 - Incremental Analysis Regeneration (Priority: P2)

**Goal**: Users can regenerate analysis without reprocessing the entire PDF (FR-014)

**Note**: This phase implements FR-014 (incremental updates). It is NOT User Story 4 from the spec (Comparative Trend Analysis), which is deferred to a future iteration per the Scope Boundaries section.

**Independent Test**: Process a report, call regenerate endpoint, verify analysis is updated with new timestamp while document_flow remains unchanged

### Tests for FR-014

- [ ] T076 [P] Unit test for regenerate_analysis() in tests/unit/test_analysis_generator.py
- [ ] T077 Integration test for regeneration (verify document_flow unchanged) in tests/integration/test_analysis_pipeline.py

### Implementation for FR-014

**Backend - Regeneration**

- [ ] T078 Add POST /api/reports/{report_id}/regenerate-analysis endpoint to viewer/server.py
- [ ] T079 Implement regenerate_analysis() in src/analysis_generator.py (loads existing doc, regenerates analysis only)
- [ ] T080 Update analysis_metadata with regeneration version tracking

**Viewer Frontend - Regenerate Button**

- [ ] T081 Add "Regenerate Analysis" button to Analysis tab in viewer/static/js/app.js
- [ ] T082 Add regeneration loading state and success feedback in viewer/static/js/app.js

**Checkpoint**: FR-014 complete - Analysis regeneration available

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, edge cases, and performance optimization

- [ ] T083 Add error handling for LLM failures with fallback messages in src/analysis_generator.py
- [ ] T084 Add confidence="low" marking when analysis is partial in src/analysis_generator.py
- [ ] T085 [P] Add logging for analysis generation timing (SC-006 validation) in src/analysis_generator.py
- [ ] T086 [P] Add edge case handling for reports with missing pages in src/analysis_generator.py
- [ ] T087 [P] Add edge case handling for unexpected report formats in src/analysis_generator.py
- [ ] T088 Run quickstart.md validation steps and document results
- [ ] T089 Verify all success criteria (SC-001 through SC-008) and document results
- [ ] T090 Performance test: Verify analysis adds <30% to processing time (SC-006)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - First priority P1 story
- **User Story 2 (Phase 4)**: Depends on Foundational - Second P1 story (can parallel with US1 if staffed)
- **User Story 3 (Phase 5)**: Depends on US1 completion (needs analysis to export)
- **FR-014 (Phase 6)**: Depends on US1 completion (needs analysis to regenerate)
- **Polish (Phase 7)**: Depends on US1, US2 at minimum; ideally all stories complete

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|-----------|-----------------|
| US1 - Overall Analysis | Foundational (Phase 2) | T024 complete |
| US2 - Sector Analysis | Foundational (Phase 2) | T024 complete |
| US3 - Export | US1 complete | T048 complete |
| FR-014 - Regeneration | US1 complete | T048 complete |

### Within Each User Story

1. Tests written FIRST, verified to FAIL
2. Backend implementation (models → generator → LLM methods)
3. API endpoints
4. Frontend rendering
5. Story complete checkpoint

### Parallel Opportunities

**Phase 2 - Foundational Models (All [P]):**
```
T004, T005, T006, T007, T008 (parallel - different models)
```

**Phase 3 - US1 Tests (All [P]):**
```
T025, T026, T027 (parallel - different test files)
```

**Phase 3 - US1 API Endpoints (Partial [P]):**
```
T036, T037, T038 (parallel - independent endpoints)
```

**Phase 4 - US2 Tests (All [P]):**
```
T049, T050 (parallel - different test files)
```

**US1 and US2 can run in parallel** if team capacity allows (both only depend on Foundational)

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all model definitions in parallel (different enums/models):
Task: "Add ConfidenceLevel, TrendDirection, SentimentLabel enums to src/models.py"
Task: "Add ContributingFactor model to src/models.py"
Task: "Add IndicatorSignal model to src/models.py"
Task: "Add Correlation model to src/models.py"
Task: "Add Theme model to src/models.py"

# Then sequential for models with dependencies:
Task: "Add SentimentScore model with validator"
Task: "Add CrossSectorTrends model"
Task: "Add SectorAnalysis model"
Task: "Add OverallAnalysis model"
Task: "Add AnalysisMetadata model"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T024)
3. Complete Phase 3: User Story 1 - Overall Analysis (T025-T048)
4. **STOP and VALIDATE**: Test overall analysis independently
5. Deploy/demo MVP - users can see overall analysis

### Incremental Delivery

1. MVP → User Story 1 complete (overall analysis visible)
2. Add User Story 2 → Sector analysis available
3. Add User Story 3 → Export functionality
4. Add User Story 4 → Regeneration capability
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2+ developers after Foundational phase:
- Developer A: User Story 1 (overall analysis)
- Developer B: User Story 2 (sector analysis)
- Then both can work on US3/US4 after US1 complete

---

## Summary

| Phase | Tasks | Parallel Tasks | Story Coverage |
|-------|-------|----------------|----------------|
| Phase 1: Setup | 3 | 2 | Infrastructure |
| Phase 2: Foundational | 21 | 5 | All stories |
| Phase 3: US1 | 24 | 7 | P1 - Overall Analysis |
| Phase 4: US2 | 18 | 2 | P1 - Sector Analysis |
| Phase 5: US3 | 9 | 1 | P2 - Export |
| Phase 6: FR-014 | 7 | 1 | P2 - Regeneration |
| Phase 7: Polish | 8 | 3 | Cross-cutting |
| **Total** | **90** | **21** | 3 User Stories + FR-014 |

**MVP Scope**: Phases 1-3 (48 tasks) delivers core overall analysis functionality

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests should fail before implementation begins
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently

**Deferred to Future Iteration:**
- **User Story 4 (Comparative Trend Analysis)** - Per spec.md Scope Boundaries, comparative analysis across multiple reports is out of scope for this iteration. Phase 6 implements FR-014 (incremental regeneration), not US4.

**Manual Validation Required Post-Deployment:**
- SC-005: User satisfaction (90% report faster decisions) - requires user feedback collection
- SC-007: Theme relevance validation - requires user domain expert review
- SC-008: Correlation accuracy (80% match) - requires user domain knowledge validation
