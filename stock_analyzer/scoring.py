"""
Scoring + recommendation engine.

Combines technical, fundamental, sentiment, and knowledge-graph features into
a transparent, rule-based score that maps to BUY / HOLD / SELL.

Score architecture
------------------
Each dimension produces a sub-score in [-1, +1]:
  technical_score    (weight 0.35)
  fundamental_score  (weight 0.35)
  sentiment_score    (weight 0.20)
  kg_score           (weight 0.10)  ← small boost for well-known/enriched companies

Combined score → recommendation:
  score >= +0.20  → BUY
  score <= -0.20  → SELL
  otherwise       → HOLD

Confidence is derived from |combined_score| scaled to [0.40, 0.95].

DISCLAIMER: This scoring model is rule-based and educational.
It does NOT constitute financial advice.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


# ── helpers ────────────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _safe(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ── technical sub-scorer ───────────────────────────────────────────────────────

def _technical_score(f: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Score in [-1, +1] based on technical indicators."""
    points = 0.0
    reasons: List[str] = []

    # RSI: oversold (<30) → bullish, overbought (>70) → bearish
    rsi = _safe(f.get("rsi14"), default=50.0)
    if rsi < 30:
        points += 0.4
        reasons.append(f"RSI {rsi:.1f} is oversold (<30) – potential reversal upward.")
    elif rsi < 45:
        points += 0.2
        reasons.append(f"RSI {rsi:.1f} is moderately oversold.")
    elif rsi > 70:
        points -= 0.4
        reasons.append(f"RSI {rsi:.1f} is overbought (>70) – potential reversal downward.")
    elif rsi > 55:
        points -= 0.1
        reasons.append(f"RSI {rsi:.1f} is mildly elevated.")

    # MACD histogram: positive = bullish momentum
    macd = _safe(f.get("macd_hist"), default=0.0)
    if macd > 0:
        points += 0.2
        reasons.append("MACD histogram positive – bullish momentum.")
    elif macd < 0:
        points -= 0.2
        reasons.append("MACD histogram negative – bearish momentum.")

    # Golden / death cross
    gc = f.get("golden_cross")
    if gc == 1:
        points += 0.2
        reasons.append("SMA50 above SMA200 (golden cross) – bullish long-term trend.")
    elif gc == -1:
        points -= 0.2
        reasons.append("SMA50 below SMA200 (death cross) – bearish long-term trend.")

    # Price above SMA50
    cross50 = f.get("sma50_cross")
    if cross50 == 1:
        points += 0.1
        reasons.append("Price above 50-day SMA – short-term trend is up.")
    elif cross50 == -1:
        points -= 0.1
        reasons.append("Price below 50-day SMA – short-term trend is down.")

    # 1-month momentum
    p1m = _safe(f.get("price_change_1m"), default=0.0)
    if p1m >= 5:
        points += 0.1
        reasons.append(f"Price up {p1m:.1f}% over the past month.")
    elif p1m <= -5:
        points -= 0.1
        reasons.append(f"Price down {abs(p1m):.1f}% over the past month.")

    return _clamp(points), reasons


# ── fundamental sub-scorer ─────────────────────────────────────────────────────

def _fundamental_score(f: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Score in [-1, +1] based on fundamental metrics."""
    points = 0.0
    reasons: List[str] = []

    # P/E ratio
    actual_pe = f.get("pe_ratio")
    if actual_pe is not None:
        pe = float(actual_pe)
        if pe <= 0:
            points -= 0.2
            reasons.append(f"Negative P/E ({pe:.1f}) – company is currently unprofitable.")
        elif pe < 15:
            points += 0.3
            reasons.append(f"Low P/E ({pe:.1f}) – potentially undervalued.")
        elif pe < 25:
            points += 0.1
            reasons.append(f"Moderate P/E ({pe:.1f}).")
        elif pe > 50:
            points -= 0.3
            reasons.append(f"High P/E ({pe:.1f}) – valuation appears stretched.")
        elif pe > 35:
            points -= 0.1
            reasons.append(f"Elevated P/E ({pe:.1f}).")

    # Revenue growth
    rev_growth = f.get("revenue_growth")
    if rev_growth is not None:
        rg = float(rev_growth)
        if rg >= 0.20:
            points += 0.3
            reasons.append(f"Strong revenue growth ({rg*100:.1f}% YoY).")
        elif rg >= 0.05:
            points += 0.15
            reasons.append(f"Positive revenue growth ({rg*100:.1f}% YoY).")
        elif rg < 0:
            points -= 0.2
            reasons.append(f"Revenue declining ({rg*100:.1f}% YoY).")

    # Profit margin
    pm = f.get("profit_margin")
    if pm is not None:
        pm_val = float(pm)
        if pm_val >= 0.20:
            points += 0.2
            reasons.append(f"High profit margin ({pm_val*100:.1f}%).")
        elif pm_val >= 0.05:
            points += 0.05
            reasons.append(f"Positive profit margin ({pm_val*100:.1f}%).")
        elif pm_val < 0:
            points -= 0.15
            reasons.append(f"Negative profit margin ({pm_val*100:.1f}%).")

    # Debt-to-equity
    de = f.get("debt_to_equity")
    if de is not None:
        de_val = float(de)
        if de_val > 200:
            points -= 0.2
            reasons.append(f"Very high debt-to-equity ({de_val:.0f}%) – elevated financial risk.")
        elif de_val > 100:
            points -= 0.1
            reasons.append(f"Elevated debt-to-equity ({de_val:.0f}%).")

    # Return on equity
    roe = f.get("roe")
    if roe is not None:
        roe_val = float(roe)
        if roe_val >= 0.15:
            points += 0.1
            reasons.append(f"Strong return on equity ({roe_val*100:.1f}%).")
        elif roe_val < 0:
            points -= 0.1
            reasons.append(f"Negative return on equity ({roe_val*100:.1f}%).")

    return _clamp(points), reasons


# ── sentiment sub-scorer ───────────────────────────────────────────────────────

def _sentiment_sub_score(f: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Convert VADER compound score → [-1, +1] sub-score."""
    score = _safe(f.get("sentiment_score"), default=0.0)
    label = f.get("sentiment_label", "neutral")
    count = int(_safe(f.get("headline_count"), default=0))
    reasons: List[str] = []

    if count == 0:
        reasons.append("No recent news headlines found; sentiment is neutral.")
    else:
        reasons.append(
            f"Sentiment analysis of {count} headlines: {label} "
            f"(score {score:+.3f})."
        )

    # Scale VADER compound [-1,+1] by 0.8 (don't over-weight news)
    return _clamp(score * 0.8), reasons


# ── KG sub-scorer ──────────────────────────────────────────────────────────────

def _kg_sub_score(f: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Small positive boost if Wikidata enrichment is available."""
    reasons: List[str] = []
    enriched = f.get("kg_enriched", False)
    if enriched:
        parts = []
        if f.get("kg_industry"):
            parts.append(f"industry: {f['kg_industry']}")
        if f.get("kg_country"):
            parts.append(f"country: {f['kg_country']}")
        if f.get("kg_hq"):
            parts.append(f"HQ: {f['kg_hq']}")
        if f.get("kg_ceo"):
            parts.append(f"CEO: {f['kg_ceo']}")
        if parts:
            reasons.append("Wikidata enrichment – " + "; ".join(parts) + ".")
        return 0.05, reasons   # tiny positive boost for data confidence
    else:
        reasons.append("No Wikidata enrichment found for this ticker.")
        return 0.0, reasons


# ── main scoring function ──────────────────────────────────────────────────────

WEIGHTS = {
    "technical": 0.35,
    "fundamental": 0.35,
    "sentiment": 0.20,
    "kg": 0.10,
}

BUY_THRESHOLD = 0.20
SELL_THRESHOLD = -0.20


def score_ticker(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a combined score and recommendation for a single ticker.

    Parameters
    ----------
    features : dict
        Output of ``stock_analyzer.features.extract_features``.

    Returns
    -------
    dict with keys:
        ticker          – symbol
        recommendation  – 'BUY', 'HOLD', or 'SELL'
        confidence      – float in [0.40, 0.95]
        combined_score  – weighted score in [-1, +1]
        technical_score
        fundamental_score
        sentiment_score
        kg_score
        reasons         – list of human-readable bullet strings
    """
    tech_score, tech_reasons = _technical_score(features)
    fund_score, fund_reasons = _fundamental_score(features)
    sent_score, sent_reasons = _sentiment_sub_score(features)
    kg_score, kg_reasons = _kg_sub_score(features)

    combined = (
        WEIGHTS["technical"] * tech_score
        + WEIGHTS["fundamental"] * fund_score
        + WEIGHTS["sentiment"] * sent_score
        + WEIGHTS["kg"] * kg_score
    )
    combined = _clamp(combined)

    if combined >= BUY_THRESHOLD:
        recommendation = "BUY"
    elif combined <= SELL_THRESHOLD:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    # Confidence: scale |combined| from [0, 1] → [0.40, 0.95]
    confidence = round(0.40 + abs(combined) * 0.55, 3)
    confidence = min(0.95, confidence)

    all_reasons = (
        ["=== Technical ==="]
        + tech_reasons
        + ["=== Fundamental ==="]
        + fund_reasons
        + ["=== Sentiment ==="]
        + sent_reasons
        + ["=== Knowledge Graph ==="]
        + kg_reasons
    )

    return {
        "ticker": features.get("ticker", ""),
        "company_name": features.get("company_name", features.get("ticker", "")),
        "recommendation": recommendation,
        "confidence": confidence,
        "combined_score": round(combined, 4),
        "technical_score": round(tech_score, 4),
        "fundamental_score": round(fund_score, 4),
        "sentiment_score_val": round(sent_score, 4),
        "kg_score": round(kg_score, 4),
        "reasons": all_reasons,
        # pass-through for report
        "close": features.get("close"),
        "pe_ratio": features.get("pe_ratio"),
        "eps_ttm": features.get("eps_ttm"),
        "revenue_growth": features.get("revenue_growth"),
        "rsi14": features.get("rsi14"),
        "macd_hist": features.get("macd_hist"),
        "volatility_30d": features.get("volatility_30d"),
        "sentiment_label": features.get("sentiment_label"),
        "sentiment_score": features.get("sentiment_score"),
        "headline_count": features.get("headline_count"),
        "wikidata_qid": features.get("wikidata_qid"),
        "kg_industry": features.get("kg_industry"),
        "kg_country": features.get("kg_country"),
        "kg_hq": features.get("kg_hq"),
        "sector": features.get("sector"),
        "industry": features.get("industry"),
    }
