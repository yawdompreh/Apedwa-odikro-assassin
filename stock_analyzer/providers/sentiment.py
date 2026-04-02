"""
Sentiment analysis provider.

Strategy
--------
1. Fetch recent news headlines for the ticker via the free GNews API
   (https://gnews.io – free tier: 100 requests/day, no key required for
   the public search endpoint used here).
2. Fall back to Yahoo Finance news if GNews is unavailable.
3. Score each headline with VADER (vaderSentiment – pure Python, no API key).
4. Return an aggregate compound score in [-1, +1].

If no headlines are available the provider returns a neutral score (0.0).
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf

logger = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()
_cache: Dict[str, dict] = {}

# GNews free public search (no API key for headline-only access)
_GNEWS_URL = (
    "https://gnews.io/api/v4/search"
    "?q={query}&lang=en&max=10&token=public"
)

# Conservative request timeout
_TIMEOUT = 10


def _fetch_gnews_headlines(ticker: str) -> List[str]:
    """Try GNews free endpoint; return list of headline strings."""
    url = _GNEWS_URL.format(query=ticker)
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return [
                article.get("title", "")
                for article in data.get("articles", [])
                if article.get("title")
            ]
    except Exception as exc:
        logger.debug("GNews fetch failed for %s: %s", ticker, exc)
    return []


def _fetch_yahoo_headlines(ticker: str) -> List[str]:
    """Fall back to Yahoo Finance news feed."""
    try:
        news = yf.Ticker(ticker).news or []
        return [
            item.get("title", "")
            for item in news
            if item.get("title")
        ]
    except Exception as exc:
        logger.debug("Yahoo news fetch failed for %s: %s", ticker, exc)
    return []


def _score_headlines(headlines: List[str]) -> float:
    """Return mean VADER compound score in [-1, +1]."""
    if not headlines:
        return 0.0
    scores = [_analyzer.polarity_scores(h)["compound"] for h in headlines]
    return sum(scores) / len(scores)


def get_sentiment(ticker: str) -> Dict[str, object]:
    """
    Return sentiment data for *ticker*.

    Keys
    ----
    sentiment_score   – aggregate VADER compound score in [-1, +1]
    sentiment_label   – 'positive', 'neutral', or 'negative'
    headline_count    – number of headlines analysed
    headlines         – list of up to 10 headlines used
    source            – data source used ('gnews', 'yahoo', or 'none')
    """
    if ticker in _cache:
        return _cache[ticker]

    headlines = _fetch_gnews_headlines(ticker)
    source = "gnews" if headlines else None

    if not headlines:
        headlines = _fetch_yahoo_headlines(ticker)
        source = "yahoo" if headlines else "none"

    score = _score_headlines(headlines)
    if score >= 0.05:
        label = "positive"
    elif score <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    result = {
        "sentiment_score": round(score, 4),
        "sentiment_label": label,
        "headline_count": len(headlines),
        "headlines": headlines[:10],
        "source": source or "none",
    }
    _cache[ticker] = result
    return result
