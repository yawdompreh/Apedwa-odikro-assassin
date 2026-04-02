#!/usr/bin/env python3
"""
Stock Analyzer CLI

Usage
-----
  python cli.py analyze --tickers AAPL MSFT GOOGL AMZN TSLA
  python cli.py analyze --tickers AAPL MSFT GOOGL AMZN TSLA --output-dir ./reports
  python cli.py analyze --tickers AAPL MSFT GOOGL AMZN TSLA --format csv html

DISCLAIMER: This tool is for informational and educational purposes only.
It does NOT constitute financial advice. Always consult a licensed financial
advisor before making investment decisions.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("cli")


def _print_banner():
    print(
        "\n╔══════════════════════════════════════════════════════════════╗\n"
        "║       📈  Stock Analyzer – BUY / HOLD / SELL Engine         ║\n"
        "╚══════════════════════════════════════════════════════════════╝\n"
        "  ⚠️  DISCLAIMER: Not financial advice. Educational use only.\n"
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run the full analysis pipeline."""
    from stock_analyzer.features import extract_features
    from stock_analyzer.scoring import score_ticker
    from stock_analyzer.report import generate_csv, generate_html

    tickers: List[str] = [t.upper().strip() for t in args.tickers if t.strip()]

    if len(tickers) < 5:
        print(
            f"\n❌ Error: at least 5 ticker symbols are required. "
            f"You provided {len(tickers)}: {', '.join(tickers) or 'none'}.\n",
            file=sys.stderr,
        )
        return 1

    _print_banner()
    print(f"Analyzing {len(tickers)} tickers: {', '.join(tickers)}\n")
    print("This may take a minute – fetching live data…\n")

    results = []
    for ticker in tickers:
        print(f"  ⏳ {ticker} …", end=" ", flush=True)
        try:
            features = extract_features(ticker)
            result = score_ticker(features)
            results.append(result)
            rec = result["recommendation"]
            conf = result["confidence"]
            icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(rec, "⚪")
            print(f"{icon} {rec}  (confidence {conf:.0%})")
        except Exception as exc:
            logger.error("Failed to analyze %s: %s", ticker, exc)
            print(f"⚠️  ERROR – {exc}")

    if not results:
        print("No results generated.", file=sys.stderr)
        return 1

    # ── print summary table ──────────────────────────────────────────────────
    print("\n" + "═" * 80)
    print(f"{'TICKER':<8} {'COMPANY':<30} {'REC':<6} {'CONF':>6} {'SCORE':>7} {'PRICE':>8}")
    print("─" * 80)
    for r in results:
        name = (r.get("company_name") or r["ticker"])[:28]
        price_str = f"${r['close']:.2f}" if r.get("close") else "  N/A"
        print(
            f"{r['ticker']:<8} {name:<30} {r['recommendation']:<6} "
            f"{r['confidence']:>5.0%} {r['combined_score']:>+7.4f} {price_str:>8}"
        )
    print("═" * 80)

    # ── print per-ticker reasons ─────────────────────────────────────────────
    if not args.quiet:
        for r in results:
            print(f"\n── {r['ticker']} ({'BUY/HOLD/SELL: ' + r['recommendation']}) ──")
            for line in r.get("reasons", []):
                if line.startswith("==="):
                    print(f"\n  {line.strip('= ').strip()}")
                else:
                    print(f"  • {line}")

    # ── write report files ───────────────────────────────────────────────────
    output_dir = getattr(args, "output_dir", ".") or "."
    os.makedirs(output_dir, exist_ok=True)

    formats = set(f.lower() for f in (args.format or ["csv", "html"]))
    written: List[str] = []

    if "csv" in formats:
        path = os.path.join(output_dir, "stock_analysis_report.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(generate_csv(results))
        written.append(path)

    if "html" in formats:
        path = os.path.join(output_dir, "stock_analysis_report.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(generate_html(results))
        written.append(path)

    if written:
        print(f"\n📄 Reports saved:")
        for p in written:
            print(f"   {os.path.abspath(p)}")

    print("\n✅ Analysis complete.\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_analyzer",
        description=(
            "Stock analysis + BUY/HOLD/SELL recommendation tool.\n"
            "DISCLAIMER: Not financial advice. Educational use only."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one or more stock tickers (minimum 5 required).",
    )
    analyze_parser.add_argument(
        "--tickers",
        nargs="+",
        required=True,
        metavar="TICKER",
        help="Stock ticker symbols (at least 5, e.g. AAPL MSFT GOOGL AMZN TSLA).",
    )
    analyze_parser.add_argument(
        "--output-dir",
        default=".",
        metavar="DIR",
        help="Directory to save report files (default: current directory).",
    )
    analyze_parser.add_argument(
        "--format",
        nargs="+",
        choices=["csv", "html"],
        default=["csv", "html"],
        metavar="FORMAT",
        help="Output format(s): csv and/or html (default: both).",
    )
    analyze_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-ticker reason bullets; only show summary table.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
