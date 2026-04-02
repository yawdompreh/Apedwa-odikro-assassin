"""
Tests for report generation (no network calls).
"""

import pytest
from stock_analyzer.report import generate_csv, generate_html, DISCLAIMER


def _make_result(ticker="AAPL", rec="BUY"):
    return {
        "ticker": ticker,
        "company_name": f"{ticker} Inc",
        "recommendation": rec,
        "confidence": 0.72,
        "combined_score": 0.35,
        "technical_score": 0.4,
        "fundamental_score": 0.3,
        "sentiment_score_val": 0.2,
        "kg_score": 0.05,
        "close": 180.50,
        "pe_ratio": 28.5,
        "eps_ttm": 6.14,
        "revenue_growth": 0.08,
        "rsi14": 52.3,
        "macd_hist": 0.123,
        "volatility_30d": 18.5,
        "sentiment_label": "positive",
        "sentiment_score": 0.25,
        "headline_count": 7,
        "wikidata_qid": "Q312",
        "kg_industry": "Technology",
        "kg_country": "United States",
        "kg_hq": "Cupertino",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "reasons": [
            "=== Technical ===",
            "RSI 52.3 is moderate.",
            "=== Fundamental ===",
            "Low P/E (28.5) – potentially undervalued.",
            "=== Sentiment ===",
            "Sentiment analysis of 7 headlines: positive (score +0.250).",
            "=== Knowledge Graph ===",
            "Wikidata enrichment – industry: Technology; country: United States.",
        ],
    }


class TestCSVReport:
    def test_csv_contains_header(self):
        csv = generate_csv([_make_result()])
        assert "Ticker" in csv
        assert "Recommendation" in csv

    def test_csv_contains_ticker(self):
        csv = generate_csv([_make_result("AAPL", "BUY")])
        assert "AAPL" in csv

    def test_csv_contains_recommendation(self):
        csv = generate_csv([_make_result("MSFT", "SELL")])
        assert "SELL" in csv

    def test_csv_contains_disclaimer(self):
        csv = generate_csv([_make_result()])
        assert "DISCLAIMER" in csv or "not financial advice" in csv.lower()

    def test_csv_multiple_tickers(self):
        results = [_make_result("AAPL", "BUY"), _make_result("MSFT", "SELL")]
        csv = generate_csv(results)
        assert "AAPL" in csv
        assert "MSFT" in csv

    def test_csv_handles_none_values(self):
        result = _make_result()
        result["pe_ratio"] = None
        result["rsi14"] = None
        csv = generate_csv([result])
        assert "N/A" in csv


class TestHTMLReport:
    def test_html_is_valid_html_structure(self):
        html = generate_html([_make_result()])
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_html_contains_ticker(self):
        html = generate_html([_make_result("NVDA", "BUY")])
        assert "NVDA" in html

    def test_html_contains_recommendation_badge(self):
        html = generate_html([_make_result("TSLA", "SELL")])
        assert "SELL" in html

    def test_html_contains_wikidata_link(self):
        html = generate_html([_make_result("AAPL", "BUY")])
        assert "wikidata.org/wiki/Q312" in html

    def test_html_contains_disclaimer(self):
        html = generate_html([_make_result()])
        assert "DISCLAIMER" in html

    def test_html_multiple_tickers(self):
        results = [_make_result("AAPL", "BUY"), _make_result("GOOGL", "HOLD")]
        html = generate_html(results)
        assert "AAPL" in html
        assert "GOOGL" in html

    def test_html_contains_summary_table(self):
        html = generate_html([_make_result()])
        assert "<table" in html
        assert "Summary" in html
