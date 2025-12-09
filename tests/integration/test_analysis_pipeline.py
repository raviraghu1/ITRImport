"""
Integration tests for the analysis pipeline.

Tests end-to-end analysis generation and validation
against success criteria (SC-001 through SC-008).
"""

import pytest
import time
from datetime import datetime

from src.analysis_generator import AnalysisGenerator
from src.models import (
    OverallAnalysis,
    SectorAnalysis,
    SentimentScore,
    ConfidenceLevel,
    SentimentLabel,
)


class TestAnalysisPipeline:
    """Integration tests for analysis pipeline."""

    @pytest.fixture
    def sample_extracted_document(self):
        """Create a realistic extracted document for testing."""
        # Simulate a 50-page ITR report
        document_flow = []
        for i in range(1, 51):
            sector = ["core", "financial", "construction", "manufacturing"][i % 4]
            series_name = f"US {sector.title()} Indicator {i}"

            document_flow.append({
                "page_number": i,
                "page_type": "series" if i > 2 else "overview",
                "series_name": series_name if i > 2 else None,
                "sector": sector if i > 2 else None,
                "page_summary": f"Summary for {series_name}: Economic indicators show mixed trends.",
                "key_insights": [
                    f"Insight 1 for page {i}",
                    f"Insight 2 for page {i}"
                ],
                "blocks": [
                    {
                        "block_type": "chart",
                        "interpretation": f"Chart shows {['rising', 'falling', 'stable'][i % 3]} trend",
                        "content": {"chart_type": "line"},
                        "metadata": {
                            "trend_direction": ["rising", "falling", "stable"][i % 3],
                            "current_phase": ["A", "B", "C", "D"][i % 4]
                        }
                    }
                ]
            })

        series_index = {}
        for i in range(3, 51):
            sector = ["core", "financial", "construction", "manufacturing"][i % 4]
            series_name = f"US {sector.title()} Indicator {i}"
            series_index[series_name] = {
                "page_number": i,
                "sector": sector,
                "summary": f"Summary for {series_name}",
                "insights": [f"Insight for {series_name}"]
            }

        return {
            "report_id": "test_integration_report",
            "pdf_filename": "Test Report March 2024.pdf",
            "report_period": "March 2024",
            "extraction_timestamp": datetime.now().isoformat(),
            "metadata": {
                "total_pages": 50,
                "series_pages_count": 48,
                "total_charts": 96,
                "sectors_covered": ["core", "financial", "construction", "manufacturing"]
            },
            "document_flow": document_flow,
            "series_index": series_index,
            "aggregated_insights": {
                "total_insights": 100,
                "top_insights": ["Key insight 1", "Key insight 2"]
            }
        }

    def test_full_analysis_generation(self, sample_extracted_document):
        """Test complete analysis generation without LLM (SC-001, SC-002)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        # SC-001: Analysis should be accessible
        assert result is not None
        assert "overall_analysis" in result
        assert "sector_analyses" in result
        assert "analysis_metadata" in result

        # SC-002: Executive summary present
        overall = result["overall_analysis"]
        assert overall is not None
        assert "executive_summary" in overall
        assert len(overall["executive_summary"]) >= 100

    def test_sector_analysis_completeness(self, sample_extracted_document):
        """Test all sectors have analysis (SC-003)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        sector_analyses = result["sector_analyses"]

        # SC-003: All sectors should be analyzed
        expected_sectors = ["core", "financial", "construction", "manufacturing"]
        for sector in expected_sectors:
            assert sector in sector_analyses, f"Missing sector: {sector}"
            analysis = sector_analyses[sector]
            assert "summary" in analysis
            assert "series_count" in analysis
            assert "phase_distribution" in analysis
            assert "dominant_trend" in analysis

    def test_sentiment_score_validity(self, sample_extracted_document):
        """Test sentiment score is valid (SC-004)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        sentiment = result["overall_analysis"]["sentiment_score"]

        # SC-004: Sentiment score should be valid
        assert 1 <= sentiment["score"] <= 5
        assert sentiment["label"] in [
            "Strongly Bearish", "Bearish", "Neutral", "Bullish", "Strongly Bullish"
        ]
        assert sentiment["confidence"] in ["high", "medium", "low"]
        assert "rationale" in sentiment

    def test_source_traceability(self, sample_extracted_document):
        """Test source page references are present (SC-005)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        # SC-005: Source pages should be traceable
        for sector, analysis in result["sector_analyses"].items():
            assert "source_pages" in analysis
            assert len(analysis["source_pages"]) > 0

    def test_processing_time_tracking(self, sample_extracted_document):
        """Test processing time is tracked (SC-006)."""
        generator = AnalysisGenerator(llm_extractor=None)

        start = time.time()
        result = generator.generate_analysis(sample_extracted_document)
        elapsed = time.time() - start

        metadata = result["analysis_metadata"]

        # SC-006: Processing time should be tracked
        assert "processing_time_seconds" in metadata
        assert metadata["processing_time_seconds"] >= 0  # May be 0.0 for fast operations
        # Should be reasonably close to actual time (within 1 second)
        assert abs(metadata["processing_time_seconds"] - elapsed) < 1.0

    def test_metadata_completeness(self, sample_extracted_document):
        """Test metadata has all required fields (SC-007)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        metadata = result["analysis_metadata"]

        # SC-007: Metadata should be complete
        assert "version" in metadata
        assert "generated_at" in metadata
        assert "generator_version" in metadata
        assert "llm_model" in metadata
        assert "processing_time_seconds" in metadata

    def test_export_format(self, sample_extracted_document):
        """Test export format is correct (SC-008)."""
        generator = AnalysisGenerator(llm_extractor=None)
        result = generator.generate_analysis(sample_extracted_document)

        # Add analysis to document
        sample_extracted_document.update(result)

        export = generator.export_analysis(sample_extracted_document)

        # SC-008: Export should have correct format
        assert "report_id" in export
        assert "pdf_filename" in export
        assert "report_period" in export
        assert "overall_analysis" in export
        assert "sector_analyses" in export
        assert "analysis_metadata" in export


class TestAnalysisRegeneration:
    """Tests for analysis regeneration (FR-014)."""

    @pytest.fixture
    def sample_document_with_analysis(self):
        """Create a document that already has analysis."""
        return {
            "report_id": "test_regen_report",
            "pdf_filename": "Test Report.pdf",
            "report_period": "March 2024",
            "metadata": {
                "total_pages": 10,
                "sectors_covered": ["core", "financial"]
            },
            "document_flow": [
                {
                    "page_number": i,
                    "page_type": "series",
                    "series_name": f"Series {i}",
                    "sector": "core" if i % 2 == 0 else "financial",
                    "page_summary": f"Summary for page {i}",
                    "key_insights": [],
                    "blocks": []
                }
                for i in range(1, 11)
            ],
            "series_index": {
                f"Series {i}": {
                    "page_number": i,
                    "sector": "core" if i % 2 == 0 else "financial"
                }
                for i in range(1, 11)
            },
            "analysis_metadata": {
                "version": "0.9",
                "generated_at": "2024-01-01T00:00:00",
                "generator_version": "3.0.0",
                "llm_model": "gpt-4",
                "processing_time_seconds": 30.0
            }
        }

    def test_regeneration_preserves_document_flow(self, sample_document_with_analysis):
        """Test that regeneration doesn't modify document_flow."""
        generator = AnalysisGenerator(llm_extractor=None)

        original_flow = sample_document_with_analysis["document_flow"].copy()

        result = generator.regenerate_analysis(sample_document_with_analysis)

        # Document flow should be unchanged
        assert sample_document_with_analysis["document_flow"] == original_flow

    def test_regeneration_tracks_version(self, sample_document_with_analysis):
        """Test that regeneration tracks the previous version."""
        generator = AnalysisGenerator(llm_extractor=None)

        result = generator.regenerate_analysis(sample_document_with_analysis)

        # Should track that it was regenerated
        assert "regenerated_from_version" in result["analysis_metadata"]
        assert result["analysis_metadata"]["regenerated_from_version"] == "0.9"

    def test_regeneration_updates_timestamp(self, sample_document_with_analysis):
        """Test that regeneration updates the timestamp."""
        generator = AnalysisGenerator(llm_extractor=None)

        result = generator.regenerate_analysis(sample_document_with_analysis)

        # Timestamp should be recent
        new_timestamp = result["analysis_metadata"]["generated_at"]
        assert new_timestamp != "2024-01-01T00:00:00"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_document(self):
        """Test handling of empty document."""
        generator = AnalysisGenerator(llm_extractor=None)

        result = generator.generate_analysis({
            "report_id": "empty",
            "document_flow": [],
            "series_index": {},
            "metadata": {}
        })

        # Should still return valid structure
        assert "overall_analysis" in result
        assert "sector_analyses" in result
        assert "analysis_metadata" in result

    def test_single_sector_document(self):
        """Test handling of document with only one sector."""
        generator = AnalysisGenerator(llm_extractor=None)

        result = generator.generate_analysis({
            "report_id": "single_sector",
            "document_flow": [
                {
                    "page_number": 1,
                    "sector": "core",
                    "page_summary": "Core sector summary",
                    "key_insights": [],
                    "blocks": []
                }
            ],
            "series_index": {
                "Core Series": {"sector": "core", "page_number": 1}
            },
            "metadata": {"sectors_covered": ["core"]}
        })

        # Should handle gracefully
        assert len(result["sector_analyses"]) >= 1
        # Confidence should be lower with limited data
        sentiment = result["overall_analysis"]["sentiment_score"]
        assert sentiment["confidence"] in ["low", "medium"]

    def test_missing_metadata(self):
        """Test handling of document with missing metadata."""
        generator = AnalysisGenerator(llm_extractor=None)

        result = generator.generate_analysis({
            "report_id": "no_metadata",
            "document_flow": [
                {"page_number": 1, "sector": "core", "page_summary": "Test"}
            ],
            "series_index": {"Test": {"sector": "core"}}
            # No metadata field
        })

        # Should still work
        assert "overall_analysis" in result
