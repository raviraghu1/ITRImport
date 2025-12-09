"""
Unit tests for SentimentScore model validation.

Tests the sentiment score model including validators
for sector_weights and label-score consistency.
"""

import pytest
from pydantic import ValidationError

from src.models import (
    SentimentScore,
    SentimentLabel,
    ConfidenceLevel,
    ContributingFactor,
    IndicatorSignal,
    TrendDirection,
    AnalysisBusinessPhase,
)


class TestSentimentScore:
    """Tests for SentimentScore model."""

    @pytest.fixture
    def valid_contributing_factors(self):
        """Create valid contributing factors."""
        return [
            ContributingFactor(
                factor_name="Core Sector Trend",
                impact="positive",
                weight=0.4,
                description="Core sector showing growth"
            ),
            ContributingFactor(
                factor_name="Financial Sector Trend",
                impact="positive",
                weight=0.3,
                description="Financial sector stable"
            )
        ]

    @pytest.fixture
    def valid_indicator_signals(self):
        """Create valid indicator signals."""
        return [
            IndicatorSignal(
                indicator_name="US Industrial Production",
                sector="core",
                direction=TrendDirection.RISING,
                phase=AnalysisBusinessPhase.B,
                source_page=5
            ),
            IndicatorSignal(
                indicator_name="US Stock Prices",
                sector="financial",
                direction=TrendDirection.RISING,
                source_page=10
            )
        ]

    @pytest.fixture
    def valid_sector_weights(self):
        """Create valid sector weights summing to 1.0."""
        return {
            "core": 0.35,
            "financial": 0.25,
            "construction": 0.20,
            "manufacturing": 0.20
        }

    def test_valid_sentiment_score_creation(
        self,
        valid_contributing_factors,
        valid_indicator_signals,
        valid_sector_weights
    ):
        """Test creating a valid SentimentScore."""
        sentiment = SentimentScore(
            score=4,
            label=SentimentLabel.BULLISH,
            confidence=ConfidenceLevel.HIGH,
            contributing_factors=valid_contributing_factors,
            sector_weights=valid_sector_weights,
            indicator_signals=valid_indicator_signals,
            rationale="Positive trends across core and financial sectors."
        )

        assert sentiment.score == 4
        assert sentiment.label == SentimentLabel.BULLISH
        assert sentiment.confidence == ConfidenceLevel.HIGH
        assert len(sentiment.contributing_factors) == 2
        assert len(sentiment.indicator_signals) == 2

    def test_score_must_be_1_to_5(self, valid_contributing_factors, valid_indicator_signals, valid_sector_weights):
        """Test that score must be between 1 and 5."""
        with pytest.raises(ValidationError) as exc_info:
            SentimentScore(
                score=0,
                label=SentimentLabel.STRONGLY_BEARISH,
                confidence=ConfidenceLevel.HIGH,
                contributing_factors=valid_contributing_factors,
                sector_weights=valid_sector_weights,
                indicator_signals=valid_indicator_signals,
                rationale="Test"
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SentimentScore(
                score=6,
                label=SentimentLabel.STRONGLY_BULLISH,
                confidence=ConfidenceLevel.HIGH,
                contributing_factors=valid_contributing_factors,
                sector_weights=valid_sector_weights,
                indicator_signals=valid_indicator_signals,
                rationale="Test"
            )
        assert "less than or equal to 5" in str(exc_info.value)

    def test_label_must_match_score(self, valid_contributing_factors, valid_indicator_signals, valid_sector_weights):
        """Test that label must match the score value."""
        with pytest.raises(ValidationError) as exc_info:
            SentimentScore(
                score=1,
                label=SentimentLabel.BULLISH,  # Should be STRONGLY_BEARISH
                confidence=ConfidenceLevel.HIGH,
                contributing_factors=valid_contributing_factors,
                sector_weights=valid_sector_weights,
                indicator_signals=valid_indicator_signals,
                rationale="Test"
            )
        assert "does not match score" in str(exc_info.value)

    def test_sector_weights_must_sum_to_one(self, valid_contributing_factors, valid_indicator_signals):
        """Test that sector_weights must sum to 1.0."""
        invalid_weights = {
            "core": 0.5,
            "financial": 0.5,
            "construction": 0.5,  # Sum = 1.5
            "manufacturing": 0.0
        }

        with pytest.raises(ValidationError) as exc_info:
            SentimentScore(
                score=3,
                label=SentimentLabel.NEUTRAL,
                confidence=ConfidenceLevel.HIGH,
                contributing_factors=valid_contributing_factors,
                sector_weights=invalid_weights,
                indicator_signals=valid_indicator_signals,
                rationale="Test"
            )
        assert "must sum to 1.0" in str(exc_info.value)

    def test_empty_sector_weights_allowed(self, valid_contributing_factors, valid_indicator_signals):
        """Test that empty sector_weights is allowed."""
        sentiment = SentimentScore(
            score=3,
            label=SentimentLabel.NEUTRAL,
            confidence=ConfidenceLevel.LOW,
            contributing_factors=valid_contributing_factors,
            sector_weights={},
            indicator_signals=valid_indicator_signals,
            rationale="Test with no sector weights"
        )

        assert sentiment.sector_weights == {}

    def test_all_score_label_combinations(self, valid_contributing_factors, valid_indicator_signals, valid_sector_weights):
        """Test all valid score-label combinations."""
        valid_combinations = [
            (1, SentimentLabel.STRONGLY_BEARISH),
            (2, SentimentLabel.BEARISH),
            (3, SentimentLabel.NEUTRAL),
            (4, SentimentLabel.BULLISH),
            (5, SentimentLabel.STRONGLY_BULLISH),
        ]

        for score, label in valid_combinations:
            sentiment = SentimentScore(
                score=score,
                label=label,
                confidence=ConfidenceLevel.MEDIUM,
                contributing_factors=valid_contributing_factors,
                sector_weights=valid_sector_weights,
                indicator_signals=valid_indicator_signals,
                rationale=f"Score {score} test"
            )
            assert sentiment.score == score
            assert sentiment.label == label

    def test_confidence_levels(self, valid_contributing_factors, valid_indicator_signals, valid_sector_weights):
        """Test all confidence levels are valid."""
        for confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]:
            sentiment = SentimentScore(
                score=3,
                label=SentimentLabel.NEUTRAL,
                confidence=confidence,
                contributing_factors=valid_contributing_factors,
                sector_weights=valid_sector_weights,
                indicator_signals=valid_indicator_signals,
                rationale="Test"
            )
            assert sentiment.confidence == confidence

    def test_empty_contributing_factors_allowed(self, valid_indicator_signals, valid_sector_weights):
        """Test that empty contributing_factors is allowed."""
        sentiment = SentimentScore(
            score=3,
            label=SentimentLabel.NEUTRAL,
            confidence=ConfidenceLevel.LOW,
            contributing_factors=[],
            sector_weights=valid_sector_weights,
            indicator_signals=valid_indicator_signals,
            rationale="No contributing factors"
        )

        assert sentiment.contributing_factors == []

    def test_empty_indicator_signals_allowed(self, valid_contributing_factors, valid_sector_weights):
        """Test that empty indicator_signals is allowed."""
        sentiment = SentimentScore(
            score=3,
            label=SentimentLabel.NEUTRAL,
            confidence=ConfidenceLevel.LOW,
            contributing_factors=valid_contributing_factors,
            sector_weights=valid_sector_weights,
            indicator_signals=[],
            rationale="No indicator signals"
        )

        assert sentiment.indicator_signals == []

    def test_model_serialization(self, valid_contributing_factors, valid_indicator_signals, valid_sector_weights):
        """Test that model can be serialized to dict."""
        sentiment = SentimentScore(
            score=4,
            label=SentimentLabel.BULLISH,
            confidence=ConfidenceLevel.HIGH,
            contributing_factors=valid_contributing_factors,
            sector_weights=valid_sector_weights,
            indicator_signals=valid_indicator_signals,
            rationale="Test serialization"
        )

        data = sentiment.model_dump()

        assert data["score"] == 4
        assert data["label"] == "Bullish"
        assert data["confidence"] == "high"
        assert len(data["contributing_factors"]) == 2
        assert len(data["indicator_signals"]) == 2


class TestContributingFactor:
    """Tests for ContributingFactor model."""

    def test_valid_contributing_factor(self):
        """Test creating a valid ContributingFactor."""
        factor = ContributingFactor(
            factor_name="Test Factor",
            impact="positive",
            weight=0.5,
            description="Test description"
        )

        assert factor.factor_name == "Test Factor"
        assert factor.impact == "positive"
        assert factor.weight == 0.5

    def test_weight_bounds(self):
        """Test weight must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            ContributingFactor(
                factor_name="Test",
                impact="positive",
                weight=1.5,
                description="Invalid weight"
            )

        with pytest.raises(ValidationError):
            ContributingFactor(
                factor_name="Test",
                impact="positive",
                weight=-0.1,
                description="Invalid weight"
            )


class TestIndicatorSignal:
    """Tests for IndicatorSignal model."""

    def test_valid_indicator_signal(self):
        """Test creating a valid IndicatorSignal."""
        signal = IndicatorSignal(
            indicator_name="US Industrial Production",
            sector="core",
            direction=TrendDirection.RISING,
            phase=AnalysisBusinessPhase.B,
            source_page=5
        )

        assert signal.indicator_name == "US Industrial Production"
        assert signal.direction == TrendDirection.RISING
        assert signal.phase == AnalysisBusinessPhase.B

    def test_indicator_signal_without_phase(self):
        """Test IndicatorSignal can be created without phase."""
        signal = IndicatorSignal(
            indicator_name="Test Indicator",
            sector="financial",
            direction=TrendDirection.STABLE,
            source_page=10
        )

        assert signal.phase is None

    def test_all_trend_directions(self):
        """Test all trend direction values."""
        for direction in [TrendDirection.RISING, TrendDirection.FALLING, TrendDirection.STABLE]:
            signal = IndicatorSignal(
                indicator_name="Test",
                sector="core",
                direction=direction,
                source_page=1
            )
            assert signal.direction == direction
