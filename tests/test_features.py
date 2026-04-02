"""
Tests for feature extraction (providers mocked – no network calls).
"""

import pytest
from unittest.mock import patch


_MOCK_TECH = {
    "close": 150.0,
    "price_change_1m": 3.0,
    "price_change_3m": 8.0,
    "price_change_1y": 25.0,
    "volatility_30d": 20.0,
    "sma50": 145.0,
    "sma200": 130.0,
    "ema20": 148.0,
    "sma50_cross": 1,
    "golden_cross": 1,
    "rsi14": 55.0,
    "macd_hist": 0.2,
}

_MOCK_FUND = {
    "market_cap": 2e12,
    "pe_ratio": 28.0,
    "forward_pe": 24.0,
    "eps_ttm": 6.0,
    "revenue_growth": 0.10,
    "profit_margin": 0.23,
    "debt_to_equity": 120.0,
    "current_ratio": 1.5,
    "roe": 0.15,
    "dividend_yield": 0.005,
    "beta": 1.1,
    "52w_high": 180.0,
    "52w_low": 130.0,
    "company_name": "Test Corp",
    "sector": "Technology",
    "industry": "Software",
}

_MOCK_SENT = {
    "sentiment_score": 0.15,
    "sentiment_label": "positive",
    "headline_count": 5,
    "headlines": ["Stock rises on earnings beat"],
    "source": "yahoo",
}

_MOCK_KG = {
    "wikidata_qid": "Q999",
    "kg_industry": "Technology",
    "kg_country": "United States",
    "kg_hq": "San Francisco",
    "kg_ceo": "Jane Doe",
    "kg_parent_org": None,
    "kg_enriched": True,
}


class TestExtractFeatures:
    def _run(self, ticker="AAPL"):
        with (
            patch(
                "stock_analyzer.providers.historical.get_technical_indicators",
                return_value=_MOCK_TECH,
            ),
            patch(
                "stock_analyzer.providers.fundamentals.get_fundamentals",
                return_value=_MOCK_FUND,
            ),
            patch(
                "stock_analyzer.providers.sentiment.get_sentiment",
                return_value=_MOCK_SENT,
            ),
            patch(
                "stock_analyzer.providers.knowledge_graph.get_kg_enrichment",
                return_value=_MOCK_KG,
            ),
        ):
            from stock_analyzer.features import extract_features
            return extract_features(ticker)

    def test_ticker_uppercased(self):
        features = self._run("aapl")
        assert features["ticker"] == "AAPL"

    def test_technical_keys_present(self):
        features = self._run()
        for key in _MOCK_TECH:
            assert key in features, f"Missing technical key: {key}"

    def test_fundamental_keys_present(self):
        features = self._run()
        for key in _MOCK_FUND:
            assert key in features, f"Missing fundamental key: {key}"

    def test_sentiment_keys_present(self):
        features = self._run()
        for key in _MOCK_SENT:
            assert key in features, f"Missing sentiment key: {key}"

    def test_kg_keys_present(self):
        features = self._run()
        for key in _MOCK_KG:
            assert key in features, f"Missing KG key: {key}"

    def test_values_merged_correctly(self):
        features = self._run()
        assert features["close"] == 150.0
        assert features["pe_ratio"] == 28.0
        assert features["sentiment_label"] == "positive"
        assert features["kg_country"] == "United States"
