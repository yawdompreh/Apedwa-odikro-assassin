"""
Tests for KG query response parsing (no real network calls – mocked).
"""

import pytest
from unittest.mock import patch, MagicMock
from stock_analyzer.providers.knowledge_graph import (
    get_kg_enrichment,
    _TICKER_QID_MAP,
    _cache,
)


@pytest.fixture(autouse=True)
def clear_kg_cache():
    """Clear the module-level cache before each test."""
    _cache.clear()
    yield
    _cache.clear()


class TestKGEnrichment:
    def test_known_ticker_uses_hardcoded_qid(self):
        """AAPL should resolve to Q312 without any SPARQL query."""
        with patch(
            "stock_analyzer.providers.knowledge_graph._get_company_attributes"
        ) as mock_attrs:
            mock_attrs.return_value = {
                "industry": "Technology",
                "country": "United States",
                "hq": "Cupertino",
            }
            result = get_kg_enrichment("AAPL")

        assert result["wikidata_qid"] == "Q312"
        assert result["kg_enriched"] is True
        assert result["kg_industry"] == "Technology"
        assert result["kg_country"] == "United States"
        assert result["kg_hq"] == "Cupertino"

    def test_unknown_ticker_sparql_fails_gracefully(self):
        """An unknown ticker where SPARQL returns nothing should return nulls."""
        with patch(
            "stock_analyzer.providers.knowledge_graph._sparql_query",
            return_value=None,
        ):
            result = get_kg_enrichment("XYZUNKNOWN")

        assert result["wikidata_qid"] is None
        assert result["kg_enriched"] is False

    def test_result_is_cached(self):
        """Second call for the same ticker should not re-query."""
        with patch(
            "stock_analyzer.providers.knowledge_graph._get_company_attributes"
        ) as mock_attrs:
            mock_attrs.return_value = {"industry": "Finance"}
            first = get_kg_enrichment("JPM")
            second = get_kg_enrichment("JPM")

        # _get_company_attributes should be called only once
        assert mock_attrs.call_count == 1
        assert first == second

    def test_sparql_response_parsing(self):
        """Test that SPARQL JSON bindings are parsed correctly."""
        from stock_analyzer.providers.knowledge_graph import _get_company_attributes

        mock_response = {
            "results": {
                "bindings": [
                    {
                        "industryLabel": {"value": "Software"},
                        "countryLabel": {"value": "USA"},
                        "hqLabel": {"value": "Redmond"},
                        "ceoLabel": {"value": "Satya Nadella"},
                    }
                ]
            }
        }
        with patch(
            "stock_analyzer.providers.knowledge_graph._sparql_query",
            return_value=mock_response,
        ):
            attrs = _get_company_attributes("Q2283")

        assert attrs["industry"] == "Software"
        assert attrs["country"] == "USA"
        assert attrs["hq"] == "Redmond"
        assert attrs["ceo"] == "Satya Nadella"

    def test_all_known_tickers_have_qids(self):
        """Every entry in the hardcoded map should have a non-empty QID."""
        for ticker, qid in _TICKER_QID_MAP.items():
            assert qid.startswith("Q"), f"{ticker} maps to invalid QID: {qid}"
