"""
Historical price provider + technical indicator computation.

Uses yfinance (free, no API key required).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ── cache so repeated calls within a session are free ─────────────────────────
_cache: Dict[str, pd.DataFrame] = {}


def _get_raw(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download OHLCV data from Yahoo Finance (cached)."""
    key = f"{ticker}:{period}"
    if key in _cache:
        return _cache[key]
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            logger.warning("No price data returned for %s", ticker)
        _cache[key] = df
        return df
    except Exception as exc:
        logger.error("Error fetching price data for %s: %s", ticker, exc)
        return pd.DataFrame()


# ── indicator helpers ──────────────────────────────────────────────────────────

def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (MACD line, signal line, histogram)."""
    ema12 = _ema(series, 12)
    ema26 = _ema(series, 26)
    macd_line = ema12 - ema26
    signal = _ema(macd_line, 9)
    hist = macd_line - signal
    return macd_line, signal, hist


# ── public API ─────────────────────────────────────────────────────────────────

def get_technical_indicators(ticker: str) -> Dict[str, Optional[float]]:
    """
    Return a flat dict of technical indicator values for *ticker*.

    Keys
    ----
    close           – latest closing price
    price_change_1m – 1-month % price change
    price_change_3m – 3-month % price change
    price_change_1y – 1-year % price change
    volatility_30d  – 30-day annualised volatility (std of daily returns)
    sma50           – 50-day SMA
    sma200          – 200-day SMA
    ema20           – 20-day EMA
    sma50_cross     – 1 if price > SMA50, -1 if below, 0 if unavailable
    golden_cross    – 1 if SMA50 > SMA200, -1 if death cross, 0 otherwise
    rsi14           – 14-day RSI
    macd_hist       – MACD histogram value (positive = bullish momentum)
    """
    df = _get_raw(ticker, period="1y")
    if df.empty or "Close" not in df.columns:
        return {k: None for k in (
            "close", "price_change_1m", "price_change_3m", "price_change_1y",
            "volatility_30d", "sma50", "sma200", "ema20",
            "sma50_cross", "golden_cross", "rsi14", "macd_hist",
        )}

    # Flatten multi-level columns if needed (yfinance sometimes returns them)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].dropna()
    if len(close) < 2:
        return {k: None for k in (
            "close", "price_change_1m", "price_change_3m", "price_change_1y",
            "volatility_30d", "sma50", "sma200", "ema20",
            "sma50_cross", "golden_cross", "rsi14", "macd_hist",
        )}

    latest = float(close.iloc[-1])
    n = len(close)

    def pct_change(days: int) -> Optional[float]:
        if n <= days:
            return None
        old = float(close.iloc[-(days + 1)])
        if old == 0:
            return None
        return (latest - old) / old * 100

    daily_returns = close.pct_change().dropna()
    vol_30d: Optional[float] = None
    if len(daily_returns) >= 30:
        vol_30d = float(daily_returns.tail(30).std() * np.sqrt(252) * 100)

    sma50_val = float(_sma(close, 50).iloc[-1]) if n >= 50 else None
    sma200_val = float(_sma(close, 200).iloc[-1]) if n >= 200 else None
    ema20_val = float(_ema(close, 20).iloc[-1]) if n >= 20 else None

    sma50_cross: Optional[int] = None
    if sma50_val is not None:
        sma50_cross = 1 if latest > sma50_val else -1

    golden_cross: Optional[int] = None
    if sma50_val is not None and sma200_val is not None:
        golden_cross = 1 if sma50_val > sma200_val else -1

    rsi14: Optional[float] = None
    if n >= 30:
        rsi14 = float(_rsi(close, 14).iloc[-1])

    macd_hist_val: Optional[float] = None
    if n >= 40:
        _, _, hist = _macd(close)
        macd_hist_val = float(hist.iloc[-1])

    return {
        "close": latest,
        "price_change_1m": pct_change(21),
        "price_change_3m": pct_change(63),
        "price_change_1y": pct_change(252),
        "volatility_30d": vol_30d,
        "sma50": sma50_val,
        "sma200": sma200_val,
        "ema20": ema20_val,
        "sma50_cross": sma50_cross,
        "golden_cross": golden_cross,
        "rsi14": rsi14,
        "macd_hist": macd_hist_val,
    }
