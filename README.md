# Stock Analyzer – BUY / HOLD / SELL Recommendation Engine

> **⚠️ DISCLAIMER:** This tool is for **informational and educational purposes only**. It does **NOT** constitute financial advice. Past performance is not indicative of future results. Always consult a licensed financial advisor before making any investment decisions. Predictions may be incorrect.

---

## Overview

A Python-based stock analysis and recommendation engine that accepts **5 or more stock tickers** and produces a **BUY / HOLD / SELL** recommendation per ticker with:

- **Historical price + technical analysis** (SMA, EMA, RSI, MACD, volatility)
- **Fundamental analysis** (P/E, EPS, revenue growth, profit margins, D/E, ROE)
- **Sentiment analysis** (VADER on live news headlines from Yahoo Finance / GNews)
- **Knowledge graph enrichment** (Wikidata SPARQL – sector, industry, HQ, country, CEO)
- **Downloadable reports** (CSV and HTML)
- **Transparent, rule-based scoring** with confidence score and human-readable reasons

---

## Project Structure

```
Apedwa-odikro-assassin/
├── app.py                          # Flask web application
├── cli.py                          # CLI entry point
├── requirements.txt
├── stock_analyzer/
│   ├── __init__.py
│   ├── features.py                 # Feature extraction (aggregates all providers)
│   ├── scoring.py                  # Scoring + recommendation engine
│   ├── report.py                   # CSV + HTML report generation
│   └── providers/
│       ├── historical.py           # yfinance historical prices + technical indicators
│       ├── fundamentals.py         # yfinance fundamental data
│       ├── sentiment.py            # VADER sentiment on news headlines
│       └── knowledge_graph.py      # Wikidata SPARQL KG enrichment
└── tests/
    ├── test_scoring.py
    ├── test_report.py
    ├── test_knowledge_graph.py
    └── test_features.py
```

---

## Setup

### Requirements

- Python 3.10+
- Internet access (for live data fetching)

### Install

```bash
pip install -r requirements.txt
```

---

## Usage

### Web Application (Flask)

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

1. Enter 5 or more stock ticker symbols (e.g. `AAPL MSFT GOOGL AMZN TSLA`)
2. Click **Analyse Tickers**
3. View the BUY / HOLD / SELL recommendations
4. Download the **CSV** or **HTML** report

**Screenshot**: The web UI shows a summary table and per-ticker detail sections with colour-coded recommendation badges, confidence bars, and Wikidata knowledge graph links.

### CLI

```bash
python cli.py analyze --tickers AAPL MSFT GOOGL AMZN TSLA
```

With options:

```bash
python cli.py analyze \
  --tickers AAPL MSFT GOOGL AMZN TSLA NVDA META NFLX JPM WMT \
  --output-dir ./reports \
  --format csv html \
  --quiet
```

**Options:**

| Option | Default | Description |
|---|---|---|
| `--tickers` | (required) | Space-separated list of stock symbols (≥5 required) |
| `--output-dir` | `.` | Directory to write report files |
| `--format` | `csv html` | Output format(s): `csv` and/or `html` |
| `--quiet` | off | Suppress per-ticker reason bullets |

**Example output:**

```
╔══════════════════════════════════════════════════════════════╗
║       📈  Stock Analyzer – BUY / HOLD / SELL Engine         ║
╚══════════════════════════════════════════════════════════════╝

  ⚠️  DISCLAIMER: Not financial advice. Educational use only.

Analysing 5 tickers: AAPL, MSFT, GOOGL, AMZN, TSLA

  ⏳ AAPL … 🟡 HOLD  (confidence 52%)
  ⏳ MSFT … 🟢 BUY   (confidence 68%)
  ⏳ GOOGL … 🟡 HOLD (confidence 45%)
  ⏳ AMZN … 🟢 BUY   (confidence 61%)
  ⏳ TSLA … 🔴 SELL  (confidence 58%)

════════════════════════════════════════════════════════════════════════════════
TICKER   COMPANY                        REC    CONF   SCORE    PRICE
────────────────────────────────────────────────────────────────────────────────
AAPL     Apple Inc                      HOLD    52%  +0.0420  $171.23
MSFT     Microsoft Corporation          BUY     68%  +0.3150  $415.50
...
```

### Input Validation

If fewer than 5 tickers are provided:

```bash
python cli.py analyze --tickers AAPL MSFT GOOGL
# ❌ Error: at least 5 ticker symbols are required. You provided 3: AAPL, MSFT, GOOGL.
```

---

## How It Works

### Scoring Architecture

Each analysis dimension produces a sub-score in **[-1, +1]**:

| Dimension | Weight | Key signals |
|---|---|---|
| Technical | **35%** | RSI, MACD histogram, Golden/Death cross, SMA50 position, 1-month price change |
| Fundamental | **35%** | P/E ratio, Revenue growth, Profit margin, D/E ratio, ROE |
| Sentiment | **20%** | VADER compound score on recent news headlines |
| Knowledge Graph | **10%** | Wikidata enrichment confidence boost |

**Combined score → Recommendation:**
- `score ≥ +0.20` → **BUY**
- `score ≤ -0.20` → **SELL**
- otherwise → **HOLD**

**Confidence** is derived from `|combined_score|` scaled to [40%, 95%].

### Data Sources (All Free, No API Keys Required)

| Data type | Source |
|---|---|
| Historical prices + fundamentals | [Yahoo Finance via yfinance](https://github.com/ranaroussi/yfinance) |
| Sentiment scoring | [VADER (vaderSentiment)](https://github.com/cjhutto/vaderSentiment) |
| News headlines | Yahoo Finance news / GNews free endpoint |
| Knowledge graph | [Wikidata SPARQL](https://query.wikidata.org/) |

### Knowledge Graph Enrichment

The engine queries Wikidata to enrich each ticker with:
- **Industry / sector**
- **Country of incorporation**
- **Headquarters location**
- **CEO / key people**
- **Parent organisation** (if applicable)

For well-known tickers (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, etc.) a hardcoded QID map ensures reliable resolution. For unknown tickers, the engine falls back to SPARQL property `P249` (stock ticker symbol) lookup.

---

## Reports

Both report formats include:
- Summary section (all tickers in one table)
- Per-ticker section: metrics, recommendation, confidence, reasons
- Wikidata links
- Full disclaimer

### CSV Report

```
Ticker,Company,Recommendation,Confidence,...
AAPL,Apple Inc,HOLD,0.52,...
```

### HTML Report

A styled, self-contained HTML file viewable in any browser. Includes colour-coded recommendation badges, confidence bars, clickable Wikidata links, and per-ticker analysis breakdowns.

---

## Testing

```bash
pytest tests/ -v
```

Tests cover (51 test cases, no network calls – all providers are mocked):
- Scoring logic (technical, fundamental, sentiment, KG sub-scorers)
- End-to-end `score_ticker` with buy/sell/hold scenarios
- Report generation (CSV and HTML structure, content, disclaimers)
- Knowledge graph response parsing and caching
- Feature extraction pipeline
- CLI input validation (< 5 tickers rejected)

---

## Caching

All data providers cache their results in-memory within a single run to avoid redundant network calls. This ensures:
- Deterministic output within a session
- Faster analysis when the same ticker appears in multiple contexts

---

## Limitations & Accuracy Notes

- Technical indicators are computed from 1-year of daily data (Yahoo Finance).
- Fundamental data availability depends on what Yahoo Finance reports for each ticker.
- Sentiment is based on a small set of recent headlines (≤10) and VADER's lexicon-based approach. It is not trained on financial text.
- The scoring model is **rule-based** (not ML-trained), which ensures transparency but limits accuracy.
- No backtesting guarantees 75%+ accuracy in live markets. Use as one signal among many.

---

## License

This project is part of the `yawdompreh/Apedwa-odikro-assassin` repository and is provided for educational purposes.
