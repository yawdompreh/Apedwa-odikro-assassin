"""
Knowledge graph enrichment via Wikidata SPARQL.

Queries Wikidata to find sector, industry, headquarters, country, and key
people associated with a publicly traded company.

Wikidata SPARQL endpoint: https://query.wikidata.org/sparql
No API key required.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
_HEADERS = {
    "User-Agent": "StockAnalyzer/1.0 (educational tool; contact@example.com)",
    "Accept": "application/sparql-results+json",
}
_TIMEOUT = 15

# Well-known ticker → Wikidata QID overrides for reliability
_TICKER_QID_MAP: Dict[str, str] = {
    "AAPL": "Q312",
    "MSFT": "Q2283",
    "GOOGL": "Q95",
    "GOOG": "Q95",
    "AMZN": "Q3884",
    "META": "Q380",
    "TSLA": "Q478214",
    "NVDA": "Q182477",
    "NFLX": "Q47740",
    "JPM": "Q192583",
    "BAC": "Q487097",
    "WMT": "Q483551",
    "DIS": "Q2743",
    "INTC": "Q248",
    "AMD": "Q294706",
    "PYPL": "Q1361880",
    "CRM": "Q802185",
    "ORCL": "Q104819",
    "IBM": "Q37156",
    "GE": "Q54173",
    "F": "Q44294",
    "GM": "Q81965",
    "BA": "Q66",
    "KO": "Q2813",
    "PEP": "Q893190",
    "MCD": "Q38076",
}

_cache: Dict[str, dict] = {}


def _sparql_query(query: str) -> Optional[dict]:
    """Execute a SPARQL query and return the parsed JSON response."""
    try:
        resp = requests.get(
            _SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("SPARQL query failed: %s", exc)
    return None


def _get_qid_by_ticker(ticker: str) -> Optional[str]:
    """Look up the Wikidata QID for a stock ticker symbol."""
    # Check hardcoded map first
    qid = _TICKER_QID_MAP.get(ticker.upper())
    if qid:
        return qid

    query = f"""
SELECT ?company WHERE {{
  ?company wdt:P414 ?exchange .
  ?company wdt:P249 "{ticker.upper()}" .
}}
LIMIT 1
"""
    result = _sparql_query(query)
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            uri = bindings[0].get("company", {}).get("value", "")
            return uri.split("/")[-1] if uri else None

    # Fallback: search by ticker in P249 (stock exchange ticker symbol)
    query2 = f"""
SELECT ?company WHERE {{
  ?company wdt:P249 "{ticker.upper()}" .
  ?company wdt:P31 wd:Q4830453 .
}}
LIMIT 1
"""
    result2 = _sparql_query(query2)
    if result2:
        bindings = result2.get("results", {}).get("bindings", [])
        if bindings:
            uri = bindings[0].get("company", {}).get("value", "")
            return uri.split("/")[-1] if uri else None

    return None


def _get_company_attributes(qid: str) -> dict:
    """Fetch company attributes from Wikidata for a given QID."""
    query = f"""
SELECT ?industryLabel ?countryLabel ?hqLabel ?ceoLabel ?parentLabel WHERE {{
  OPTIONAL {{ wd:{qid} wdt:P452 ?industry . }}
  OPTIONAL {{ wd:{qid} wdt:P17 ?country . }}
  OPTIONAL {{ wd:{qid} wdt:P159 ?hq . }}
  OPTIONAL {{ wd:{qid} wdt:P169 ?ceo . }}
  OPTIONAL {{ wd:{qid} wdt:P749 ?parent . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 1
"""
    result = _sparql_query(query)
    attrs: dict = {}
    if result:
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            row = bindings[0]
            for key in ("industryLabel", "countryLabel", "hqLabel", "ceoLabel", "parentLabel"):
                val = row.get(key, {}).get("value")
                if val:
                    attrs[key.replace("Label", "")] = val
    return attrs


def get_kg_enrichment(ticker: str) -> Dict[str, Optional[str]]:
    """
    Return Wikidata knowledge-graph enrichment for *ticker*.

    Keys
    ----
    wikidata_qid   – Wikidata entity ID (e.g. 'Q312')
    kg_industry    – industry / sector label from Wikidata
    kg_country     – country of incorporation
    kg_hq          – headquarters city/location
    kg_ceo         – current CEO name
    kg_parent_org  – parent organisation (if applicable)
    kg_enriched    – True if any KG data was found
    """
    cache_key = ticker.upper()
    if cache_key in _cache:
        return _cache[cache_key]

    base: Dict[str, Optional[str]] = {
        "wikidata_qid": None,
        "kg_industry": None,
        "kg_country": None,
        "kg_hq": None,
        "kg_ceo": None,
        "kg_parent_org": None,
        "kg_enriched": False,
    }

    qid = _get_qid_by_ticker(ticker)
    if not qid:
        _cache[cache_key] = base
        return base

    base["wikidata_qid"] = qid
    attrs = _get_company_attributes(qid)

    base["kg_industry"] = attrs.get("industry")
    base["kg_country"] = attrs.get("country")
    base["kg_hq"] = attrs.get("hq")
    base["kg_ceo"] = attrs.get("ceo")
    base["kg_parent_org"] = attrs.get("parent")
    base["kg_enriched"] = bool(attrs)

    _cache[cache_key] = base
    return base
