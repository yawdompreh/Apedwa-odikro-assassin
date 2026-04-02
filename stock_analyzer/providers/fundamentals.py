"""
Fundamental data provider.

Uses yfinance Ticker.info (free, no API key required).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import yfinance as yf

logger = logging.getLogger(__name__)

_cache: Dict[str, dict] = {}


def _get_info(ticker: str) -> dict:
    if ticker in _cache:
        return _cache[ticker]
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:
        logger.warning("Could not fetch fundamentals for %s: %s", ticker, exc)
        info = {}
    _cache[ticker] = info
    return info


def get_fundamentals(ticker: str) -> Dict[str, Optional[float]]:
    """
    Return fundamental metrics for *ticker*.

    Keys
    ----
    market_cap         – market capitalisation in USD
    pe_ratio           – trailing P/E ratio
    forward_pe         – forward P/E ratio
    eps_ttm            – trailing twelve-month EPS
    revenue_growth     – year-over-year revenue growth (fraction, e.g. 0.12 = 12 %)
    profit_margin      – net profit margin (fraction)
    debt_to_equity     – debt-to-equity ratio
    current_ratio      – current ratio (liquidity)
    roe                – return on equity (fraction)
    dividend_yield     – dividend yield (fraction)
    beta               – beta vs. S&P 500
    52w_high           – 52-week high
    52w_low            – 52-week low
    """
    info = _get_info(ticker)

    def _f(key: str) -> Optional[float]:
        val = info.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    return {
        "market_cap": _f("marketCap"),
        "pe_ratio": _f("trailingPE"),
        "forward_pe": _f("forwardPE"),
        "eps_ttm": _f("trailingEps"),
        "revenue_growth": _f("revenueGrowth"),
        "profit_margin": _f("profitMargins"),
        "debt_to_equity": _f("debtToEquity"),
        "current_ratio": _f("currentRatio"),
        "roe": _f("returnOnEquity"),
        "dividend_yield": _f("dividendYield"),
        "beta": _f("beta"),
        "52w_high": _f("fiftyTwoWeekHigh"),
        "52w_low": _f("fiftyTwoWeekLow"),
        "company_name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }
