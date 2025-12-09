"""
Unit tests for AnalysisGenerator.

Tests the overall analysis generation, sector analysis,
and helper methods.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.analysis_generator import AnalysisGenerator
from src.models import (
    OverallAnalysis,
    SectorAnalysis,
    SentimentScore,
    AnalysisMetadata,
    Theme,
    CrossSectorTrends,
    ConfidenceLevel,
    SentimentLabel,
    AnalysisBusinessPhase,
)


class TestAnalysisGenerator:
    """Tests for AnalysisGenerator class."""

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return {
            "report_id": "test_report",
            "pdf_filename": "Test Report.pdf",
            "report_period": "March 2024",
            "extraction_timestamp": datetime.now().isoformat(),
            "metadata": {
                "total_pages": 50,
                "series_pages_count": 40,
                "total_charts": 80,
                "sectors_covered": ["core", "financial", "construction", "manufacturing"]
            },
            "document_flow": [
                {
                    "page_number": 1,
                    "page_type": "series",
                    "series_name": "US Industrial Production",
                    "sector": "core",
                    "page_summary": "US Industrial Production shows moderate growth.",
                    "key_insights": ["Growth trending upward", "Phase B indicated"],
                    "blocks": [
                        {
                            "block_type": "chart",
                            "interpretation": "Rising trend",
                            "metadata": {"trend_direction": "rising", "current_phase": "B"}
                        }
                    ]
                },
                {
                    "page_number": 5,
                    "page_type": "series",
                    "series_name": "US Stock Prices",
                    "sector": "financial",
                    "page_summary": "Stock prices continue to climb.",
                    "key_insights": ["Markets bullish", "S&P 500 up 10%"],
                    "blocks": []
                },
                {
                    "page_number": 10,
                    "page_type": "series",
                    "series_name": "US Single-Unit Housing Starts",
                    "sector": "construction",
                    "page_summary": "Housing starts declining.",
                    "key_insights": ["Interest rates impacting demand"],
                    "blocks": []
                },
                {
                    "page_number": 15,
                    "page_type": "series",
                    "series_name": "US Machinery New Orders",
                    "sector": "manufacturing",
                    "page_summary": "Manufacturing orders stable.",
                    "key_insights": ["Slight uptick expected"],
                    "blocks": []
                }
            ],
            "series_index": {
                "US Industrial Production": {
                    "page_number": 1,
                    "sector": "core",
                    "summary": "Growth trending",
                    "insights": ["Growth trending upward"]
                },
                "US Stock Prices": {
                    "page_number": 5,
                    "sector": "financial",
                    "summary": "Markets bullish",
                    "insights": ["Markets bullish"]
                },
                "US Single-Unit Housing Starts": {
                    "page_number": 10,
                    "sector": "construction",
                    "summary": "Declining",
                    "insights": ["Interest rates impact"]
                },
                "US Machinery New Orders": {
                    "page_number": 15,
                    "sector": "manufacturing",
                    "summary": "Stable",
                    "insights": ["Slight uptick"]
                }
            },
            "aggregated_insights": {
                "total_insights": 5,
                "top_insights": ["Growth trending upward", "Markets bullish"]
            }
        }

    @pytest.fixture
    def generator_no_llm(self):
        """Create AnalysisGenerator without LLM."""
        return AnalysisGenerator(llm_extractor=None)

    @pytest.fixture
    def generator_with_mock_llm(self):
        """Create AnalysisGenerator with mock LLM."""
        mock_llm = Mock()
        mock_llm.config = Mock()
        mock_llm.config.deployment = "gpt-4.1"
        return AnalysisGenerator(llm_extractor=mock_llm)

    def test_generate_analysis_returns_required_fields(self, generator_no_llm, sample_document):
        """Test that generate_analysis returns all required fields."""
        result = generator_no_llm.generate_analysis(sample_document)

        assert "overall_analysis" in result
        assert "sector_analyses" in result
        assert "analysis_metadata" in result

    def test_generate_analysis_metadata_has_required_fields(self, generator_no_llm, sample_document):
        """Test that analysis metadata contains required fields."""
        result = generator_no_llm.generate_analysis(sample_document)
        metadata = result["analysis_metadata"]

        assert "version" in metadata
        assert "generated_at" in metadata
        assert "generator_version" in metadata
        assert "llm_model" in metadata
        assert "processing_time_seconds" in metadata

    def test_aggregate_page_summaries(self, generator_no_llm, sample_document):
        """Test page summary aggregation."""
        summaries = generator_no_llm._aggregate_page_summaries(sample_document)

        assert len(summaries) == 4
        assert all("page_number" in s for s in summaries)
        assert all("summary" in s for s in summaries)

    def test_aggregate_chart_interpretations(self, generator_no_llm, sample_document):
        """Test chart interpretation aggregation."""
        interpretations = generator_no_llm._aggregate_chart_interpretations(sample_document)

        assert len(interpretations) == 1
        assert interpretations[0]["series_name"] == "US Industrial Production"

    def test_group_series_by_sector(self, generator_no_llm, sample_document):
        """Test series grouping by sector."""
        by_sector = generator_no_llm._group_series_by_sector(sample_document)

        assert "core" in by_sector
        assert "financial" in by_sector
        assert "construction" in by_sector
        assert "manufacturing" in by_sector
        assert len(by_sector["core"]) == 1

    def test_generate_sector_analyses(self, generator_no_llm, sample_document):
        """Test sector analysis generation."""
        page_summaries = generator_no_llm._aggregate_page_summaries(sample_document)
        series_by_sector = generator_no_llm._group_series_by_sector(sample_document)

        sector_analyses = generator_no_llm.generate_sector_analyses(
            sample_document, series_by_sector, page_summaries
        )

        assert len(sector_analyses) == 4
        assert all(isinstance(a, SectorAnalysis) for a in sector_analyses.values())

    def test_sector_analysis_has_required_fields(self, generator_no_llm, sample_document):
        """Test that sector analysis contains all required fields."""
        page_summaries = generator_no_llm._aggregate_page_summaries(sample_document)
        series_by_sector = generator_no_llm._group_series_by_sector(sample_document)

        sector_analyses = generator_no_llm.generate_sector_analyses(
            sample_document, series_by_sector, page_summaries
        )

        for name, analysis in sector_analyses.items():
            assert analysis.sector_name == name
            assert len(analysis.summary) >= 50
            assert analysis.series_count >= 1
            assert isinstance(analysis.phase_distribution, dict)
            assert analysis.dominant_trend in ["accelerating", "slowing", "stable", "declining", "recovering"]

    def test_fallback_overall_analysis(self, generator_no_llm, sample_document):
        """Test fallback overall analysis generation without LLM."""
        page_summaries = generator_no_llm._aggregate_page_summaries(sample_document)
        series_by_sector = generator_no_llm._group_series_by_sector(sample_document)

        sector_analyses = generator_no_llm.generate_sector_analyses(
            sample_document, series_by_sector, page_summaries
        )

        overall = generator_no_llm._generate_fallback_overall_analysis(
            sample_document, sector_analyses
        )

        assert isinstance(overall, OverallAnalysis)
        assert len(overall.executive_summary) >= 100
        assert isinstance(overall.sentiment_score, SentimentScore)

    def test_calculate_phase_distribution(self, generator_no_llm, sample_document):
        """Test phase distribution calculation."""
        series_list = [{"series_name": "Test Series"}]
        distribution = generator_no_llm._calculate_phase_distribution(series_list, sample_document)

        assert "A" in distribution
        assert "B" in distribution
        assert "C" in distribution
        assert "D" in distribution

    def test_determine_dominant_trend(self, generator_no_llm):
        """Test dominant trend determination from phase distribution."""
        distribution = {"A": 5, "B": 2, "C": 1, "D": 0}
        trend, phase = generator_no_llm._determine_dominant_trend(distribution)

        assert trend == "recovering"
        assert phase == AnalysisBusinessPhase.A

    def test_extract_sector_source_pages(self, generator_no_llm, sample_document):
        """Test extraction of source pages for a sector."""
        pages = generator_no_llm._extract_sector_source_pages("core", sample_document)

        assert 1 in pages

    def test_identify_leading_indicators(self, generator_no_llm, sample_document):
        """Test leading indicator identification."""
        series_list = [
            {"series_name": "ITR Leading Indicator"},
            {"series_name": "US ISM PMI"},
            {"series_name": "US Industrial Production"}
        ]

        indicators = generator_no_llm._identify_leading_indicators("core", series_list, sample_document)

        assert len(indicators) <= 3

    def test_regenerate_analysis(self, generator_no_llm, sample_document):
        """Test analysis regeneration."""
        # First generate
        first_result = generator_no_llm.generate_analysis(sample_document)
        sample_document["analysis_metadata"] = first_result["analysis_metadata"]

        # Then regenerate
        regenerated = generator_no_llm.regenerate_analysis(sample_document)

        assert "overall_analysis" in regenerated
        assert "sector_analyses" in regenerated

    def test_export_analysis(self, generator_no_llm, sample_document):
        """Test analysis export formatting."""
        result = generator_no_llm.generate_analysis(sample_document)
        sample_document.update(result)

        export = generator_no_llm.export_analysis(sample_document)

        assert export["report_id"] == "test_report"
        assert "overall_analysis" in export
        assert "sector_analyses" in export
        assert "analysis_metadata" in export


class TestDocumentValidation:
    """Tests for document validation and edge cases (T086, T087)."""

    @pytest.fixture
    def generator(self):
        return AnalysisGenerator(llm_extractor=None)

    def test_validate_empty_document(self, generator):
        """Test validation of empty document."""
        doc = {}
        result = generator._validate_document(doc)

        assert not result["valid"]
        assert "Missing document_flow" in result["issues"]
        assert "Missing series_index" in result["issues"]

    def test_validate_document_with_missing_pages(self, generator):
        """Test validation detects missing pages."""
        doc = {
            "document_flow": [
                {"page_number": 1},
                {"page_number": 2},
                {"page_number": 5},  # Gap in pages
                {"page_number": 10},
            ],
            "series_index": {}
        }
        result = generator._validate_document(doc)

        assert not result["valid"]
        assert any("Missing pages" in issue for issue in result["issues"])

    def test_validate_document_missing_sectors(self, generator):
        """Test validation detects missing sectors."""
        doc = {
            "document_flow": [{"page_number": i} for i in range(1, 20)],
            "series_index": {
                "Series1": {"sector": "core"},
                "Series2": {"sector": "financial"}
                # Missing construction and manufacturing
            }
        }
        result = generator._validate_document(doc)

        assert not result["valid"]
        assert any("Missing sectors" in issue for issue in result["issues"])

    def test_validate_document_no_summaries(self, generator):
        """Test validation detects unexpected format with no summaries."""
        doc = {
            "document_flow": [
                {"page_number": i, "page_type": "series"}  # No page_summary
                for i in range(1, 20)
            ],
            "series_index": {
                "Series1": {"sector": "core"},
            }
        }
        result = generator._validate_document(doc)

        assert not result["valid"]
        assert any("No page summaries" in issue for issue in result["issues"])

    def test_validate_valid_document(self, generator):
        """Test validation passes for valid document."""
        doc = {
            "document_flow": [
                {
                    "page_number": i,
                    "page_type": "series",
                    "page_summary": f"Summary for page {i}",
                    "sector": ["core", "financial", "construction", "manufacturing"][i % 4]
                }
                for i in range(1, 51)
            ],
            "series_index": {
                f"Series{i}": {"sector": ["core", "financial", "construction", "manufacturing"][i % 4]}
                for i in range(1, 41)
            }
        }
        result = generator._validate_document(doc)

        assert result["valid"]
        assert len(result["issues"]) == 0


class TestConfidenceAdjustment:
    """Tests for confidence adjustment when analysis is partial (T084)."""

    @pytest.fixture
    def generator(self):
        return AnalysisGenerator(llm_extractor=None)

    def test_confidence_low_when_partial(self, generator):
        """Test confidence is LOW when analysis is partial."""
        generator._partial_analysis = True

        sector_analyses = {
            "core": Mock(series_count=10, dominant_trend="accelerating"),
            "financial": Mock(series_count=10, dominant_trend="accelerating"),
            "construction": Mock(series_count=10, dominant_trend="accelerating"),
        }

        sentiment = generator._calculate_sentiment_score(sector_analyses, [], [])

        assert sentiment.confidence == ConfidenceLevel.LOW

    def test_confidence_low_when_many_llm_failures(self, generator):
        """Test confidence is LOW when many LLM failures occurred."""
        generator._llm_failures = 3

        sector_analyses = {
            "core": Mock(series_count=10, dominant_trend="accelerating"),
            "financial": Mock(series_count=10, dominant_trend="accelerating"),
            "construction": Mock(series_count=10, dominant_trend="accelerating"),
        }

        sentiment = generator._calculate_sentiment_score(sector_analyses, [], [])

        assert sentiment.confidence == ConfidenceLevel.LOW

    def test_confidence_high_when_no_issues(self, generator):
        """Test confidence is HIGH when no issues occurred."""
        generator._partial_analysis = False
        generator._llm_failures = 0

        sector_analyses = {
            "core": Mock(series_count=10, dominant_trend="accelerating"),
            "financial": Mock(series_count=10, dominant_trend="accelerating"),
            "construction": Mock(series_count=10, dominant_trend="accelerating"),
        }

        sentiment = generator._calculate_sentiment_score(sector_analyses, [], [])

        assert sentiment.confidence == ConfidenceLevel.HIGH


class TestAnalysisGeneratorWithMockLLM:
    """Tests for AnalysisGenerator with mocked LLM responses."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM extractor."""
        mock = Mock()
        mock.config = Mock()
        mock.config.deployment = "gpt-4.1"
        return mock

    @pytest.fixture
    def sample_document(self):
        """Create a sample document for testing."""
        return {
            "report_id": "test_report",
            "pdf_filename": "Test Report.pdf",
            "report_period": "March 2024",
            "metadata": {"sectors_covered": ["core", "financial"]},
            "document_flow": [
                {
                    "page_number": 1,
                    "page_type": "series",
                    "series_name": "Test Series",
                    "sector": "core",
                    "page_summary": "Test summary",
                    "key_insights": ["insight 1"],
                    "blocks": []
                }
            ],
            "series_index": {
                "Test Series": {
                    "page_number": 1,
                    "sector": "core",
                    "summary": "Test",
                    "insights": ["insight"]
                }
            },
            "aggregated_insights": {"total_insights": 1, "top_insights": ["insight"]}
        }

    def test_llm_model_name_extraction(self, mock_llm, sample_document):
        """Test LLM model name is extracted from config."""
        generator = AnalysisGenerator(mock_llm)
        model_name = generator._get_llm_model_name()

        assert model_name == "gpt-4.1"

    def test_generate_analysis_with_llm(self, mock_llm, sample_document):
        """Test that analysis generation calls LLM methods."""
        mock_llm._call_llm = Mock(return_value="Test summary text that is long enough to pass validation.")
        generator = AnalysisGenerator(mock_llm)

        result = generator.generate_analysis(sample_document)

        assert "overall_analysis" in result
        assert "sector_analyses" in result
