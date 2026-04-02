"""
Report generation: CSV and HTML downloadable reports.
"""

from __future__ import annotations

import csv
import io
import datetime
from typing import List, Dict, Any

DISCLAIMER = (
    "DISCLAIMER: This report is for informational and educational purposes only. "
    "It does NOT constitute financial advice. Past performance is not indicative "
    "of future results. Always consult a licensed financial advisor before making "
    "any investment decisions. Predictions may be incorrect."
)

_REPORT_DATE = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ── CSV report ─────────────────────────────────────────────────────────────────

_CSV_COLUMNS = [
    "Ticker",
    "Company",
    "Recommendation",
    "Confidence",
    "Combined Score",
    "Technical Score",
    "Fundamental Score",
    "Sentiment Score",
    "KG Score",
    "Close Price",
    "P/E Ratio",
    "EPS (TTM)",
    "Revenue Growth %",
    "RSI(14)",
    "MACD Hist",
    "Volatility 30d %",
    "Sentiment Label",
    "Sentiment Score (VADER)",
    "Headlines Analyzed",
    "Wikidata QID",
    "KG Industry",
    "KG Country",
    "KG Headquarters",
    "Sector (Yahoo)",
    "Industry (Yahoo)",
    "Reasons",
]


def _fmt(val: Any, decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


def generate_csv(results: List[Dict[str, Any]]) -> str:
    """Return CSV content as a string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for r in results:
        rev_growth = r.get("revenue_growth")
        rev_growth_pct = f"{rev_growth*100:.1f}" if rev_growth is not None else "N/A"

        reasons_text = " | ".join(
            line for line in r.get("reasons", [])
            if not line.startswith("===")
        )

        writer.writerow({
            "Ticker": r.get("ticker", ""),
            "Company": r.get("company_name", ""),
            "Recommendation": r.get("recommendation", ""),
            "Confidence": _fmt(r.get("confidence"), 3),
            "Combined Score": _fmt(r.get("combined_score"), 4),
            "Technical Score": _fmt(r.get("technical_score"), 4),
            "Fundamental Score": _fmt(r.get("fundamental_score"), 4),
            "Sentiment Score": _fmt(r.get("sentiment_score_val"), 4),
            "KG Score": _fmt(r.get("kg_score"), 4),
            "Close Price": _fmt(r.get("close"), 2),
            "P/E Ratio": _fmt(r.get("pe_ratio"), 2),
            "EPS (TTM)": _fmt(r.get("eps_ttm"), 2),
            "Revenue Growth %": rev_growth_pct,
            "RSI(14)": _fmt(r.get("rsi14"), 2),
            "MACD Hist": _fmt(r.get("macd_hist"), 4),
            "Volatility 30d %": _fmt(r.get("volatility_30d"), 2),
            "Sentiment Label": r.get("sentiment_label", ""),
            "Sentiment Score (VADER)": _fmt(r.get("sentiment_score"), 4),
            "Headlines Analyzed": r.get("headline_count", 0),
            "Wikidata QID": r.get("wikidata_qid") or "N/A",
            "KG Industry": r.get("kg_industry") or "N/A",
            "KG Country": r.get("kg_country") or "N/A",
            "KG Headquarters": r.get("kg_hq") or "N/A",
            "Sector (Yahoo)": r.get("sector") or "N/A",
            "Industry (Yahoo)": r.get("industry") or "N/A",
            "Reasons": reasons_text,
        })

    # Append disclaimer at the bottom
    output.write(f"\n\"{DISCLAIMER}\"\n")
    return output.getvalue()


# ── HTML report ────────────────────────────────────────────────────────────────

_REC_COLORS = {
    "BUY": "#1a7c3e",
    "HOLD": "#b8860b",
    "SELL": "#b22222",
}

_BADGE_STYLES = {
    "BUY": "background:#d4edda;color:#155724;border:1px solid #c3e6cb;",
    "HOLD": "background:#fff3cd;color:#856404;border:1px solid #ffeeba;",
    "SELL": "background:#f8d7da;color:#721c24;border:1px solid #f5c6cb;",
}


def _confidence_bar(conf: float) -> str:
    pct = int(conf * 100)
    color = "#1a7c3e" if pct >= 65 else "#b8860b"
    return (
        f'<div style="background:#eee;border-radius:4px;height:12px;width:100%;">'
        f'<div style="background:{color};width:{pct}%;height:12px;border-radius:4px;"></div>'
        f'</div><small>{pct}%</small>'
    )


def _reasons_html(reasons: List[str]) -> str:
    html_parts = []
    for line in reasons:
        if line.startswith("==="):
            section = line.strip("= ").strip()
            html_parts.append(f'<strong>{section}</strong>')
        else:
            html_parts.append(f'<li>{line}</li>')
    return "<ul>" + "".join(html_parts) + "</ul>"


def generate_html(results: List[Dict[str, Any]]) -> str:
    """Return a full HTML report as a string."""
    date_str = _REPORT_DATE()
    tickers_str = ", ".join(r.get("ticker", "") for r in results)

    # Summary table
    summary_rows = ""
    for r in results:
        rec = r.get("recommendation", "HOLD")
        badge_style = _BADGE_STYLES.get(rec, "")
        conf = r.get("confidence", 0.5)
        summary_rows += f"""
        <tr>
          <td><strong>{r.get('ticker','')}</strong><br><small>{r.get('company_name','')}</small></td>
          <td><span style="padding:3px 8px;border-radius:4px;font-weight:bold;{badge_style}">{rec}</span></td>
          <td>{_confidence_bar(conf)}</td>
          <td>{_fmt(r.get('combined_score'), 4)}</td>
          <td>{_fmt(r.get('close'), 2)}</td>
          <td>{_fmt(r.get('pe_ratio'), 1)}</td>
          <td>{_fmt(r.get('rsi14'), 1)}</td>
          <td>{r.get('sentiment_label','N/A')}</td>
          <td>{r.get('kg_country') or 'N/A'}</td>
        </tr>"""

    # Per-ticker detail sections
    detail_sections = ""
    for r in results:
        rec = r.get("recommendation", "HOLD")
        color = _REC_COLORS.get(rec, "#333")
        rev_growth = r.get("revenue_growth")
        rev_growth_str = f"{rev_growth*100:.1f}%" if rev_growth is not None else "N/A"
        wikidata_link = ""
        qid = r.get("wikidata_qid")
        if qid:
            wikidata_link = (
                f'<a href="https://www.wikidata.org/wiki/{qid}" target="_blank">'
                f'Wikidata: {qid}</a>'
            )
        detail_sections += f"""
        <div id="{r.get('ticker','')}" style="margin:20px 0;padding:20px;border:1px solid #ddd;border-radius:8px;">
          <h2 style="color:{color};">{r.get('ticker','')} – {rec}
            <span style="font-size:0.7em;color:#555;">({r.get('company_name','')})</span>
          </h2>
          <p><strong>Confidence:</strong> {_confidence_bar(r.get('confidence', 0.5))}
             &nbsp;&nbsp;<strong>Combined Score:</strong> {_fmt(r.get('combined_score'), 4)}</p>
          <table style="border-collapse:collapse;width:100%;font-size:0.9em;margin-top:10px;">
            <tr style="background:#f5f5f5;">
              <th colspan="2" style="padding:6px;text-align:left;border-bottom:2px solid #ddd;">Technical</th>
              <th colspan="2" style="padding:6px;text-align:left;border-bottom:2px solid #ddd;">Fundamental</th>
              <th colspan="2" style="padding:6px;text-align:left;border-bottom:2px solid #ddd;">Sentiment / KG</th>
            </tr>
            <tr>
              <td style="padding:4px 8px;">Close Price</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('close'), 2)}</strong></td>
              <td style="padding:4px 8px;">P/E Ratio</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('pe_ratio'), 1)}</strong></td>
              <td style="padding:4px 8px;">Sentiment</td><td style="padding:4px 8px;"><strong>{r.get('sentiment_label','N/A')}</strong></td>
            </tr>
            <tr style="background:#fafafa;">
              <td style="padding:4px 8px;">RSI(14)</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('rsi14'), 1)}</strong></td>
              <td style="padding:4px 8px;">EPS (TTM)</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('eps_ttm'), 2)}</strong></td>
              <td style="padding:4px 8px;">VADER Score</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('sentiment_score'), 4)}</strong></td>
            </tr>
            <tr>
              <td style="padding:4px 8px;">MACD Hist</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('macd_hist'), 4)}</strong></td>
              <td style="padding:4px 8px;">Rev. Growth</td><td style="padding:4px 8px;"><strong>{rev_growth_str}</strong></td>
              <td style="padding:4px 8px;">Headlines</td><td style="padding:4px 8px;"><strong>{r.get('headline_count',0)}</strong></td>
            </tr>
            <tr style="background:#fafafa;">
              <td style="padding:4px 8px;">Volatility 30d</td><td style="padding:4px 8px;"><strong>{_fmt(r.get('volatility_30d'), 1)}%</strong></td>
              <td style="padding:4px 8px;">Sector</td><td style="padding:4px 8px;"><strong>{r.get('sector') or r.get('kg_industry') or 'N/A'}</strong></td>
              <td style="padding:4px 8px;">KG Country</td><td style="padding:4px 8px;"><strong>{r.get('kg_country') or 'N/A'}</strong></td>
            </tr>
            <tr>
              <td style="padding:4px 8px;">KG Source</td>
              <td colspan="5" style="padding:4px 8px;">{wikidata_link or 'N/A'}</td>
            </tr>
          </table>
          <div style="margin-top:14px;">
            <strong>Analysis reasons:</strong>
            {_reasons_html(r.get('reasons', []))}
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stock Analysis Report – {date_str}</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; color: #333; }}
    h1 {{ color: #0a3a4a; border-bottom: 3px solid #0a3a4a; padding-bottom: 8px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
    th {{ background: #0a3a4a; color: #fff; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .disclaimer {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 6px; margin: 20px 0; font-size: 0.9em; }}
    ul {{ margin: 4px 0; padding-left: 20px; }}
    li {{ margin: 2px 0; }}
    a {{ color: #0a3a4a; }}
  </style>
</head>
<body>
  <h1>📈 Stock Analysis Report</h1>
  <p><strong>Generated:</strong> {date_str} &nbsp;|&nbsp; <strong>Tickers:</strong> {tickers_str}</p>

  <div class="disclaimer">⚠️ {DISCLAIMER}</div>

  <h2>Summary</h2>
  <table>
    <thead>
      <tr>
        <th>Ticker / Company</th><th>Recommendation</th><th>Confidence</th>
        <th>Score</th><th>Price</th><th>P/E</th><th>RSI</th>
        <th>Sentiment</th><th>Country</th>
      </tr>
    </thead>
    <tbody>{summary_rows}</tbody>
  </table>

  <h2 style="margin-top:30px;">Per-Ticker Detail</h2>
  {detail_sections}

  <footer style="margin-top:40px;padding-top:10px;border-top:1px solid #ccc;font-size:0.8em;color:#888;">
    Generated by Stock Analyzer v1.0 | {date_str} | {DISCLAIMER}
  </footer>
</body>
</html>"""
    return html
