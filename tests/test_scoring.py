"""
Tests for the scoring module.

These tests are unit tests only – no network calls are made.
"""

import pytest
from stock_analyzer.scoring import (
    _technical_score,
    _fundamental_score,
    _sentiment_sub_score,
    _kg_sub_score,
    score_ticker,
    BUY_THRESHOLD,
    SELL_THRESHOLD,
)


# ── technical scoring ──────────────────────────────────────────────────────────

class TestTechnicalScore:
    def test_oversold_rsi_is_bullish(self):
        score, reasons = _technical_score({"rsi14": 25})
        assert score > 0
        assert any("oversold" in r.lower() for r in reasons)

    def test_overbought_rsi_is_bearish(self):
        score, reasons = _technical_score({"rsi14": 75})
        assert score < 0
        assert any("overbought" in r.lower() for r in reasons)

    def test_golden_cross_bullish(self):
        score, reasons = _technical_score({"golden_cross": 1})
        assert score > 0
        assert any("golden cross" in r.lower() for r in reasons)

    def test_death_cross_bearish(self):
        score, reasons = _technical_score({"golden_cross": -1})
        assert score < 0
        assert any("death cross" in r.lower() for r in reasons)

    def test_positive_macd_bullish(self):
        score, reasons = _technical_score({"macd_hist": 0.5})
        assert score > 0

    def test_negative_macd_bearish(self):
        score, reasons = _technical_score({"macd_hist": -0.5})
        assert score < 0

    def test_score_clamped_between_minus_one_and_one(self):
        # Extreme bullish signals should not exceed 1.0
        f = {
            "rsi14": 20,
            "macd_hist": 2.0,
            "golden_cross": 1,
            "sma50_cross": 1,
            "price_change_1m": 30,
        }
        score, _ = _technical_score(f)
        assert -1.0 <= score <= 1.0

    def test_none_values_handled_gracefully(self):
        score, reasons = _technical_score({"rsi14": None, "macd_hist": None})
        assert isinstance(score, float)
        assert isinstance(reasons, list)


# ── fundamental scoring ────────────────────────────────────────────────────────

class TestFundamentalScore:
    def test_low_pe_bullish(self):
        score, reasons = _fundamental_score({"pe_ratio": 10.0})
        assert score > 0
        assert any("undervalued" in r.lower() or "low p/e" in r.lower() for r in reasons)

    def test_high_pe_bearish(self):
        score, reasons = _fundamental_score({"pe_ratio": 60.0})
        assert score < 0

    def test_high_revenue_growth_bullish(self):
        score, reasons = _fundamental_score({"revenue_growth": 0.35})
        assert score > 0
        assert any("revenue growth" in r.lower() for r in reasons)

    def test_negative_revenue_bearish(self):
        score, reasons = _fundamental_score({"revenue_growth": -0.10})
        assert score < 0

    def test_high_profit_margin_bullish(self):
        score, reasons = _fundamental_score({"profit_margin": 0.25})
        assert score > 0

    def test_negative_profit_margin_bearish(self):
        score, reasons = _fundamental_score({"profit_margin": -0.05})
        assert score < 0

    def test_none_values_handled_gracefully(self):
        score, reasons = _fundamental_score({})
        assert isinstance(score, float)
        assert isinstance(reasons, list)


# ── sentiment scoring ──────────────────────────────────────────────────────────

class TestSentimentScore:
    def test_positive_sentiment_bullish(self):
        score, reasons = _sentiment_sub_score(
            {"sentiment_score": 0.7, "sentiment_label": "positive", "headline_count": 5}
        )
        assert score > 0

    def test_negative_sentiment_bearish(self):
        score, reasons = _sentiment_sub_score(
            {"sentiment_score": -0.6, "sentiment_label": "negative", "headline_count": 5}
        )
        assert score < 0

    def test_no_headlines_neutral(self):
        score, reasons = _sentiment_sub_score(
            {"sentiment_score": 0.0, "sentiment_label": "neutral", "headline_count": 0}
        )
        assert score == 0.0
        assert any("no recent news" in r.lower() for r in reasons)


# ── KG scoring ─────────────────────────────────────────────────────────────────

class TestKGScore:
    def test_enriched_gives_positive_boost(self):
        score, reasons = _kg_sub_score(
            {"kg_enriched": True, "kg_industry": "Technology", "kg_country": "USA"}
        )
        assert score > 0
        assert any("wikidata" in r.lower() for r in reasons)

    def test_not_enriched_gives_zero(self):
        score, reasons = _kg_sub_score({"kg_enriched": False})
        assert score == 0.0


# ── end-to-end score_ticker ────────────────────────────────────────────────────

class TestScoreTicker:
    def _make_features(self, **overrides):
        base = {
            "ticker": "TEST",
            "company_name": "Test Corp",
            "rsi14": 50.0,
            "macd_hist": 0.0,
            "golden_cross": 0,
            "sma50_cross": 0,
            "price_change_1m": 0.0,
            "pe_ratio": 20.0,
            "revenue_growth": 0.10,
            "profit_margin": 0.10,
            "debt_to_equity": 50.0,
            "roe": 0.12,
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "headline_count": 0,
            "kg_enriched": False,
            "wikidata_qid": None,
            "kg_industry": None,
            "kg_country": None,
            "kg_hq": None,
            "sector": None,
            "industry": None,
        }
        base.update(overrides)
        return base

    def test_recommendation_is_valid(self):
        result = score_ticker(self._make_features())
        assert result["recommendation"] in ("BUY", "HOLD", "SELL")

    def test_confidence_in_range(self):
        result = score_ticker(self._make_features())
        assert 0.0 <= result["confidence"] <= 1.0

    def test_combined_score_in_range(self):
        result = score_ticker(self._make_features())
        assert -1.0 <= result["combined_score"] <= 1.0

    def test_reasons_is_list(self):
        result = score_ticker(self._make_features())
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) > 0

    def test_strong_buy_signals_produce_buy(self):
        features = self._make_features(
            rsi14=28,
            macd_hist=0.8,
            golden_cross=1,
            sma50_cross=1,
            pe_ratio=10.0,
            revenue_growth=0.30,
            profit_margin=0.25,
            sentiment_score=0.6,
            sentiment_label="positive",
            headline_count=8,
        )
        result = score_ticker(features)
        assert result["recommendation"] == "BUY"

    def test_strong_sell_signals_produce_sell(self):
        features = self._make_features(
            rsi14=78,
            macd_hist=-0.8,
            golden_cross=-1,
            sma50_cross=-1,
            pe_ratio=65.0,
            revenue_growth=-0.15,
            profit_margin=-0.10,
            sentiment_score=-0.6,
            sentiment_label="negative",
            headline_count=8,
        )
        result = score_ticker(features)
        assert result["recommendation"] == "SELL"

    def test_at_least_5_tickers_validation_via_cli(self):
        """Verify the CLI parser rejects fewer than 5 tickers."""
        import sys
        from io import StringIO
        from cli import build_parser, cmd_analyze

        parser = build_parser()
        args = parser.parse_args(["analyze", "--tickers", "AAPL", "MSFT", "GOOGL"])
        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        ret = cmd_analyze(args)
        sys.stderr = old_stderr
        assert ret == 1
        assert "5" in captured.getvalue()
