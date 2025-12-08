<!--
Sync Impact Report
==================
Version change: 0.0.0 → 1.0.0 (MAJOR - initial constitution)
Modified principles: N/A (new constitution)
Added sections:
  - Core Principles (7 principles)
  - Data Processing Standards
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (no changes needed - generic template)
  - .specify/templates/spec-template.md ✅ (no changes needed - generic template)
  - .specify/templates/tasks-template.md ✅ (no changes needed - generic template)
Follow-up TODOs: None
-->

# ITRImport Constitution

## Core Principles

### I. Data Fidelity

All extracted economic data MUST preserve the original values, units, and precision from source PDFs.
Data transformations MUST be traceable and reversible where applicable. No data point may be
silently modified, interpolated, or estimated without explicit documentation. Economic indicators,
forecasts, and rate-of-change calculations MUST match source documents exactly.

**Rationale**: ITR Economics data drives business decisions. Inaccurate data extraction or
transformation could lead to incorrect forecasts and poor business outcomes.

### II. Source Traceability

Every data point stored in MongoDB MUST include metadata linking back to its source:
- Source PDF filename and page number
- Extraction timestamp
- Data series identifier (e.g., "US Industrial Production 12MMA")
- Reporting period (e.g., "March 2024")

This enables audit trails and data validation against original documents.

**Rationale**: Economic analysis requires confidence in data provenance. Analysts must be able to
verify any data point against the original ITR Trends Report.

### III. Structured Data Model

Economic data MUST be stored in a consistent, queryable schema:
- Time series data with proper date indexing
- Sector/market categorization (Core, Financial, Construction, Manufacturing)
- Forecast ranges with confidence bounds where provided
- Rate-of-change metrics (12/12, 3/12, 1/12) as separate fields

MongoDB collections MUST enforce schema validation to prevent malformed data insertion.

**Rationale**: Consistent data structure enables reliable querying, visualization, and integration
with downstream analytics systems.

### IV. Idempotent Processing

PDF extraction and data loading MUST be idempotent. Re-processing the same PDF multiple times
MUST produce identical results without creating duplicates. Use composite keys (source + period +
series) to enable upsert operations.

**Rationale**: Data pipelines fail and require re-runs. Idempotency ensures reliability without
manual deduplication.

### V. Visualization Integrity

Charts and visualizations MUST accurately represent the underlying data:
- Axis scales MUST not mislead (no truncated y-axes without clear indication)
- Time series MUST use consistent intervals
- Forecast ranges MUST be visually distinguished from historical data
- Business cycle phases (A, B, C, D) MUST use ITR's standard color coding when applicable

**Rationale**: Visualizations inform strategic decisions. Misleading charts could cause
misinterpretation of economic trends.

### VI. Test Coverage

All data extraction logic MUST have corresponding tests:
- Unit tests for parsing functions
- Integration tests comparing extracted data against known-good reference values
- Contract tests validating MongoDB document structure
- Regression tests when adding support for new PDF formats

Tests MUST run before any code merge. Extraction accuracy below 99% for numerical data
MUST block deployment.

**Rationale**: Economic data extraction is complex and error-prone. Comprehensive testing
catches regressions before they corrupt production data.

### VII. Simplicity and Maintainability

Prefer straightforward solutions over clever ones:
- Use standard Python libraries (PyMuPDF, pandas, pymongo) unless alternatives offer significant
  benefits
- Avoid premature optimization; profile before optimizing
- Document non-obvious code with inline comments
- Keep functions focused and under 50 lines where practical
- Use type hints for all public interfaces

**Rationale**: This project will evolve as ITR report formats change. Simple, well-documented
code enables faster adaptation.

## Data Processing Standards

### Extraction Requirements

- PDF text extraction MUST handle multi-column layouts common in ITR reports
- Tables MUST be parsed with row/column alignment preserved
- Numerical values MUST handle various formats: percentages, currency, indices, millions/billions
- Forecast ranges (e.g., "98.7 - 100.0") MUST be parsed into min/max fields

### Storage Requirements

- MongoDB connection: Use environment variables for credentials, never hardcode
- Database: `itr_economics`
- Collections: Organized by data category (core, financial, construction, manufacturing)
- Indexes: Create indexes on date fields and series identifiers for query performance
- Backup: Document backup/restore procedures before production use

### Integration Requirements

- Expose data via well-defined Python interfaces before adding API layers
- Support export to common formats (CSV, JSON) for downstream consumers
- Maintain compatibility with existing analytics tools where applicable

## Development Workflow

### Code Changes

1. All changes MUST be made on feature branches
2. Run linting (ruff/black) and type checking (mypy) before commits
3. Write or update tests for any extraction logic changes
4. Document breaking changes to data schemas
5. Update relevant specs if behavior changes

### Data Pipeline Changes

1. Test new PDF parsing against multiple report versions
2. Validate extracted data against source PDFs (spot-check minimum 10 data points)
3. Run full regression test suite
4. Document any new fields or schema changes

## Governance

This constitution establishes the non-negotiable rules for the ITRImport project. All code
contributions, design decisions, and data processing logic MUST comply with these principles.

### Amendment Process

1. Propose changes via documented issue or discussion
2. Assess impact on existing data and pipelines
3. Update version number per semantic versioning:
   - MAJOR: Breaking changes to data model or removal of principles
   - MINOR: New principles or significant expansions
   - PATCH: Clarifications and wording improvements
4. Update all dependent documentation
5. Notify all contributors of changes

### Compliance

- Code reviews MUST verify principle adherence
- Data quality checks MUST run on every pipeline execution
- Violations MUST be documented and remediated before merge

**Version**: 1.0.0 | **Ratified**: 2025-12-08 | **Last Amended**: 2025-12-08
