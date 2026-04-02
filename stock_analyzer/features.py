"""
Feature extraction: combine all provider outputs into a unified feature dict.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from stock_analyzer.providers.historical import get_technical_indicators
from stock_analyzer.providers.fundamentals import get_fundamentals
from stock_analyzer.providers.sentiment import get_sentiment
from stock_analyzer.providers.knowledge_graph import get_kg_enrichment

logger = logging.getLogger(__name__)


def extract_features(ticker: str) -> Dict[str, Any]:
    """
    Pull data from all providers and return a unified feature dictionary.

    The returned dict contains:
    - All technical indicator keys from ``get_technical_indicators``
    - All fundamental keys from ``get_fundamentals``
    - All sentiment keys from ``get_sentiment``
    - All KG enrichment keys from ``get_kg_enrichment``
    - ``ticker`` – uppercase ticker symbol
    """
    ticker = ticker.upper().strip()
    logger.info("Extracting features for %s …", ticker)

    tech = get_technical_indicators(ticker)
    fund = get_fundamentals(ticker)
    sent = get_sentiment(ticker)
    kg = get_kg_enrichment(ticker)

    features: Dict[str, Any] = {"ticker": ticker}
    features.update(tech)
    features.update(fund)
    features.update(sent)
    features.update(kg)

    return features
