"""
Minimal Flask web application for the stock analysis feature.

Routes
------
GET  /            – landing page with input form
POST /analyze     – run analysis, show results
GET  /download/csv  – download the last CSV report
GET  /download/html – download the last HTML report
"""

from __future__ import annotations

import io
import logging
import threading
from typing import List

from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    url_for,
    send_file,
    flash,
    session,
)

from stock_analyzer.features import extract_features
from stock_analyzer.scoring import score_ticker
from stock_analyzer.report import generate_csv, generate_html, DISCLAIMER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "stock-analyzer-dev-key-change-in-production"

# In-memory store for last analysis result per session (simple single-user approach)
_last_results: dict = {}
_lock = threading.Lock()

# ── HTML templates (inline for minimal footprint) ─────────────────────────────

_BASE_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #333; }
  .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
  header { background: #0a3a4a; color: #f5f2ea; padding: 18px 20px; }
  header h1 { font-size: 1.6em; }
  header p { font-size: 0.9em; opacity: 0.8; }
  .card { background: #fff; border-radius: 8px; padding: 24px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .disclaimer { background: #fff3cd; border: 1px solid #ffeeba; padding: 12px 16px; border-radius: 6px; margin: 16px 0; font-size: 0.88em; }
  .btn { display: inline-block; padding: 10px 24px; border-radius: 4px; border: none; cursor: pointer; font-size: 1em; text-decoration: none; }
  .btn-primary { background: #0a3a4a; color: #fff; }
  .btn-success { background: #1a7c3e; color: #fff; }
  .btn-warning { background: #b8860b; color: #fff; }
  .btn:hover { opacity: 0.9; }
  input[type=text] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; margin-top: 6px; }
  label { font-weight: bold; }
  .flash-error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 10px 16px; border-radius: 4px; margin: 12px 0; }
  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th { background: #0a3a4a; color: #fff; padding: 10px 12px; text-align: left; }
  td { padding: 9px 12px; border-bottom: 1px solid #eee; }
  tr:hover td { background: #f5f5f5; }
  .badge-buy { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; padding: 3px 10px; border-radius: 12px; font-weight: bold; }
  .badge-hold { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 3px 10px; border-radius: 12px; font-weight: bold; }
  .badge-sell { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; padding: 3px 10px; border-radius: 12px; font-weight: bold; }
  .conf-bar-outer { background: #eee; border-radius: 4px; height: 10px; width: 100px; display: inline-block; vertical-align: middle; }
  .conf-bar-inner { height: 10px; border-radius: 4px; }
  details { margin: 6px 0; }
  summary { cursor: pointer; font-weight: bold; color: #0a3a4a; }
</style>
"""

_INDEX_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Stock Analyzer – BUY/HOLD/SELL Recommendations</title>
""" + _BASE_STYLE + """
</head>
<body>
<header>
  <div class="container">
    <h1>📈 Stock Analyzer</h1>
    <p>AI-assisted BUY / HOLD / SELL recommendations powered by technical, fundamental, sentiment &amp; knowledge-graph analysis.</p>
  </div>
</header>
<div class="container">
  <div class="disclaimer">⚠️ {{ disclaimer }}</div>
  {% for msg in get_flashed_messages(category_filter=["error"]) %}
    <div class="flash-error">{{ msg }}</div>
  {% endfor %}
  <div class="card">
    <h2 style="margin-bottom:16px;">Enter Stock Tickers</h2>
    <form method="POST" action="/analyze">
      <label for="tickers">Ticker symbols (space or comma separated – minimum 5 required):</label>
      <input type="text" id="tickers" name="tickers"
             placeholder="e.g. AAPL MSFT GOOGL AMZN TSLA NVDA"
             value="{{ last_tickers }}" required>
      <p style="margin-top:8px;font-size:0.85em;color:#666;">
        Examples: AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, JPM, WMT
      </p>
      <button type="submit" class="btn btn-primary" style="margin-top:14px;">
        🔍 Analyze Tickers
      </button>
    </form>
  </div>
</div>
</body></html>
"""

_RESULTS_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Analysis Results – Stock Analyzer</title>
""" + _BASE_STYLE + """
</head>
<body>
<header>
  <div class="container">
    <h1>📈 Stock Analyzer – Results</h1>
    <p>Analysis for: <strong>{{ tickers_str }}</strong></p>
  </div>
</header>
<div class="container">
  <div class="disclaimer">⚠️ {{ disclaimer }}</div>
  <div class="card" style="margin-bottom:16px;">
    <strong>Download Report:</strong> &nbsp;
    <a href="/download/csv" class="btn btn-success">⬇️ CSV Report</a> &nbsp;
    <a href="/download/html" class="btn btn-warning">⬇️ HTML Report</a> &nbsp;
    <a href="/" class="btn btn-primary">🔄 New Analysis</a>
  </div>

  <div class="card">
    <h2>Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Ticker</th><th>Company</th><th>Recommendation</th>
          <th>Confidence</th><th>Price</th><th>P/E</th>
          <th>RSI</th><th>Sentiment</th><th>Country (KG)</th>
        </tr>
      </thead>
      <tbody>
      {% for r in results %}
        <tr>
          <td><strong>{{ r.ticker }}</strong></td>
          <td>{{ r.company_name }}</td>
          <td>
            {% if r.recommendation == 'BUY' %}<span class="badge-buy">BUY</span>
            {% elif r.recommendation == 'SELL' %}<span class="badge-sell">SELL</span>
            {% else %}<span class="badge-hold">HOLD</span>{% endif %}
          </td>
          <td>
            <div class="conf-bar-outer">
              <div class="conf-bar-inner"
                   style="width:{{ (r.confidence*100)|int }}%;background:{% if r.confidence>=0.65 %}#1a7c3e{% else %}#b8860b{% endif %};"></div>
            </div>
            {{ "%.0f"|format(r.confidence*100) }}%
          </td>
          <td>{{ r.close|default('N/A') }}</td>
          <td>{{ r.pe_ratio|default('N/A') }}</td>
          <td>{{ r.rsi14|default('N/A') }}</td>
          <td>{{ r.sentiment_label|default('N/A') }}</td>
          <td>{{ r.kg_country|default('N/A') }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>

  {% for r in results %}
  <div class="card">
    <h2 style="color:{% if r.recommendation=='BUY' %}#1a7c3e{% elif r.recommendation=='SELL' %}#b22222{% else %}#b8860b{% endif %};">
      {{ r.ticker }}
      {% if r.recommendation == 'BUY' %}<span class="badge-buy">BUY</span>
      {% elif r.recommendation == 'SELL' %}<span class="badge-sell">SELL</span>
      {% else %}<span class="badge-hold">HOLD</span>{% endif %}
      <small style="color:#555;font-size:0.65em;">{{ r.company_name }}</small>
    </h2>
    <table style="margin-top:12px;">
      <tr>
        <th>Close</th><th>P/E</th><th>EPS</th><th>Rev Growth</th>
        <th>RSI(14)</th><th>MACD Hist</th><th>Volatility</th>
      </tr>
      <tr>
        <td>{{ "%.2f"|format(r.close) if r.close is not none else 'N/A' }}</td>
        <td>{{ "%.1f"|format(r.pe_ratio) if r.pe_ratio is not none else 'N/A' }}</td>
        <td>{{ "%.2f"|format(r.eps_ttm) if r.eps_ttm is not none else 'N/A' }}</td>
        <td>{{ "%.1f%%"|format(r.revenue_growth*100) if r.revenue_growth is not none else 'N/A' }}</td>
        <td>{{ "%.1f"|format(r.rsi14) if r.rsi14 is not none else 'N/A' }}</td>
        <td>{{ "%.4f"|format(r.macd_hist) if r.macd_hist is not none else 'N/A' }}</td>
        <td>{{ "%.1f%%"|format(r.volatility_30d) if r.volatility_30d is not none else 'N/A' }}</td>
      </tr>
    </table>
    {% if r.wikidata_qid %}
    <p style="margin-top:10px;font-size:0.88em;">
      🌐 <strong>Wikidata:</strong>
      <a href="https://www.wikidata.org/wiki/{{ r.wikidata_qid }}" target="_blank">{{ r.wikidata_qid }}</a>
      {% if r.kg_industry %} | Industry: {{ r.kg_industry }}{% endif %}
      {% if r.kg_country %} | Country: {{ r.kg_country }}{% endif %}
      {% if r.kg_hq %} | HQ: {{ r.kg_hq }}{% endif %}
    </p>
    {% endif %}
    <details style="margin-top:12px;">
      <summary>📋 Full Analysis Reasons</summary>
      <ul style="margin-top:8px;padding-left:20px;">
      {% for line in r.reasons %}
        {% if line.startswith('===') %}
          <li style="list-style:none;font-weight:bold;margin-top:6px;">{{ line.strip('= ').strip() }}</li>
        {% else %}
          <li>{{ line }}</li>
        {% endif %}
      {% endfor %}
      </ul>
    </details>
  </div>
  {% endfor %}
</div>
</body></html>
"""


# ── routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    last_tickers = session.get("last_tickers", "AAPL MSFT GOOGL AMZN TSLA")
    return render_template_string(
        _INDEX_TEMPLATE,
        disclaimer=DISCLAIMER,
        last_tickers=last_tickers,
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    raw = request.form.get("tickers", "").strip()
    # Normalise separators
    import re
    tickers: List[str] = [
        t.upper().strip()
        for t in re.split(r"[\s,;]+", raw)
        if t.strip()
    ]

    if len(tickers) < 5:
        flash(
            f"Please enter at least 5 ticker symbols. You entered {len(tickers)}.",
            "error",
        )
        return redirect(url_for("index"))

    session["last_tickers"] = " ".join(tickers)

    results = []
    for ticker in tickers:
        try:
            features = extract_features(ticker)
            result = score_ticker(features)
            results.append(result)
        except Exception as exc:
            logger.error("Error analysing %s: %s", ticker, exc)
            results.append({
                "ticker": ticker,
                "company_name": ticker,
                "recommendation": "HOLD",
                "confidence": 0.4,
                "combined_score": 0.0,
                "technical_score": 0.0,
                "fundamental_score": 0.0,
                "sentiment_score_val": 0.0,
                "kg_score": 0.0,
                "reasons": [f"Error during analysis: {exc}"],
                "close": None,
                "pe_ratio": None,
                "eps_ttm": None,
                "revenue_growth": None,
                "rsi14": None,
                "macd_hist": None,
                "volatility_30d": None,
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "headline_count": 0,
                "wikidata_qid": None,
                "kg_industry": None,
                "kg_country": None,
                "kg_hq": None,
                "sector": None,
                "industry": None,
            })

    # Cache results for download
    with _lock:
        _last_results["results"] = results

    tickers_str = ", ".join(r["ticker"] for r in results)
    return render_template_string(
        _RESULTS_TEMPLATE,
        results=results,
        tickers_str=tickers_str,
        disclaimer=DISCLAIMER,
    )


@app.route("/download/csv")
def download_csv():
    with _lock:
        results = _last_results.get("results", [])
    if not results:
        return redirect(url_for("index"))
    csv_content = generate_csv(results)
    return send_file(
        io.BytesIO(csv_content.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="stock_analysis_report.csv",
    )


@app.route("/download/html")
def download_html():
    with _lock:
        results = _last_results.get("results", [])
    if not results:
        return redirect(url_for("index"))
    html_content = generate_html(results)
    return send_file(
        io.BytesIO(html_content.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name="stock_analysis_report.html",
    )


if __name__ == "__main__":
    import os
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 8888))
    app.run(debug=debug_mode, host="127.0.0.1", port=port)
