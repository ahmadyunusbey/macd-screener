"""
Weekly MACD Momentum Screener
==============================
Zieht wöchentliche Schlusskurse via yfinance, berechnet MACD (12/26/9)
und klassifiziert das Momentum-Signal für jede Position.

Usage:
    python macd_screener.py                    # Default-Watchlist
    python macd_screener.py --tickers X Y Z    # Eigene Tickers
    python macd_screener.py --json             # JSON-Output für Web-App
    python macd_screener.py --weeks 78         # Mehr Wochen (mehr EMA-History)
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("Bitte installieren: pip install yfinance pandas")
    sys.exit(1)


# ─── Default Watchlist ────────────────────────────────────────────────────────

DEFAULT_TICKERS = {
    # Ebene 1 – Core / Income
    "AV.L":      "AVIVA",
    "BATS.L":    "BRITISH AMERICAN TOBACCO",
    "HSBA.L":    "HSBC HOLDINGS",
    "HSBK.IL":   "HALYQ BANK",
    "INDT.ST":   "INDUTRADE",
    "INPP.L":    "INTERNATIONAL PUBLIC",
    "ITH.L":     "ITHACA",
    "KAP.IL":    "KAZATOM",
    "LGEN.L":    "LEGAL & GENERAL",
    "MNG.L":     "M&G",
    "PHNX.L":    "PHOENIX",
    "PBR-A":     "PETROBRAS",
    "RIO.L":     "RIO TINTO",
    "RWS.L":     "RWS",
    "SQZ.L":     "SERICA",
    "TRIG.L":    "THE RENEWABLE",
    "ZIG.L":     "ZIGUP",
    # Ebene 2 – Royalties Watchlist
    "FNV":       "FRANCO-NEVADA",
    "RGLD":      "ROYAL GOLD",
    "WPM":       "WHEATON PRECIOUS",
    # Ebene 3 – SE/CH Compounders
    "ADDT-B.ST": "ADDTECH",
    "BAKKA.OL":  "BAKKAFROST",
    "BEAN.SW":   "BELIMO",
    "BON":       "BONHEUR",
    "CEVI.ST":   "CELLAVISION",
    "DG.PA":     "VINCI",
    "DSV.CO":    "DSV A/S",
    "ESSITY-B.ST": "ESSITY",
    "FER":       "FERROVIAL",
    "LAGR-B.ST": "LAGERCRANTZ",
    "LIFCO-B.ST":"LIFCO",
    "MYCR.ST":   "MYCRONIC",
    "NDINSCKL1.CO": "NORDIC SM CAPS",
    "NVO":       "NOVO NORDISC",
    "SIKA.SW":   "SIKA",
    "VIT-B.ST":  "VITEC SOFTWARE",
    "VACN.SW":   "VAT GROUP",
    "YAR.OL":    "YARA",
    # Ebene 4 – Thematic ETFs
    "VEGI":      "iShares MSCI Agri ETF",
    "VIOG":      "Vanguard S&P SmallCap 600 Growth",
    "XBI":       "SPDR S&P Biotech ETF",
    # Ebene 5 – Speculation
    "ARQQ":      "ARQIT",
    "BLDP":      "BALLARD POWER",
    "DOKA.SW":   "DORMAKABA",
    "FXPO.L":    "FERREXPO",
    "KSPI":      "KASPI",
    "NEL.OL":    "NEL ASA",
    "RBREW.CO":  "ROYAL UNIBREW",
    "SANN.SW":   "SANTHERA",
    "WIE.VI":    "WIENERBERGER",
}


# ─── MACD Berechnung ──────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_macd(closes: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(closes, fast) - ema(closes, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def classify_momentum(macd_line: pd.Series, signal_line: pd.Series, histogram: pd.Series) -> str:
    if len(macd_line) < 2:
        return "Insufficient data"

    m_last, m_prev = macd_line.iloc[-1], macd_line.iloc[-2]
    s_last, s_prev = signal_line.iloc[-1], signal_line.iloc[-2]
    h_last, h_prev = histogram.iloc[-1], histogram.iloc[-2]

    crossed_up   = m_prev < s_prev and m_last > s_last
    crossed_down = m_prev > s_prev and m_last < s_last
    hist_rising  = h_last > h_prev
    above_zero   = m_last > 0

    if crossed_up   and above_zero:   return "Strong Bullish Crossover"
    if crossed_up:                    return "Bullish Crossover"
    if crossed_down and not above_zero: return "Strong Bearish Crossover"
    if crossed_down:                  return "Bearish Crossover"
    if above_zero   and hist_rising:  return "Bullish Momentum"
    if not above_zero and not hist_rising: return "Bearish Momentum"
    if above_zero:                    return "Bullish (Fading)"
    return "Bearish (Fading)"


# ─── Score für Sortierung ─────────────────────────────────────────────────────

MOMENTUM_SCORE = {
    "Strong Bullish Crossover":  6,
    "Bullish Crossover":         5,
    "Bullish Momentum":          4,
    "Bullish (Fading)":          3,
    "Bearish (Fading)":          2,
    "Bearish Momentum":          1,
    "Bearish Crossover":         0,
    "Strong Bearish Crossover": -1,
    "Insufficient data":        -99,
}

EMOJI = {
    "Strong Bullish Crossover":  "🚀",
    "Bullish Crossover":         "📈",
    "Bullish Momentum":          "⬆️ ",
    "Bullish (Fading)":          "〰️ ",
    "Bearish (Fading)":          "〰️ ",
    "Bearish Momentum":          "⬇️ ",
    "Bearish Crossover":         "📉",
    "Strong Bearish Crossover":  "🔻",
    "Insufficient data":         "❓",
}


# ─── Screener ────────────────────────────────────────────────────────────────

def screen(tickers: dict, weeks: int = 104) -> list[dict]:
    results = []
    period = f"{max(weeks, 60)}wk"   # yfinance weekly needs enough history

    print(f"\n  Lade {len(tickers)} Ticker (wöchentlich, {weeks} Wochen)...\n")

    for ticker, name in tickers.items():
        try:
            data = yf.download(
                ticker,
                period=period,
                interval="1wk",
                progress=False,
                auto_adjust=True,
            )
            if data.empty or len(data) < 35:
                print(f"  ⚠  {ticker:15s} – zu wenig Daten ({len(data)} Wochen)")
                continue

            closes = data["Close"].dropna()
            if hasattr(closes, "squeeze"):
                closes = closes.squeeze()

            macd_line, signal_line, histogram = calc_macd(closes)
            momentum = classify_momentum(macd_line, signal_line, histogram)

            price   = float(closes.iloc[-1])
            price_1 = float(closes.iloc[-2])
            chg_pct = (price - price_1) / price_1 * 100

            results.append({
                "ticker":    ticker,
                "name":      name,
                "price":     round(price, 2),
                "chg_pct":   round(chg_pct, 2),
                "macd":      round(float(macd_line.iloc[-1]), 4),
                "signal":    round(float(signal_line.iloc[-1]), 4),
                "histogram": round(float(histogram.iloc[-1]), 4),
                "momentum":  momentum,
                "score":     MOMENTUM_SCORE.get(momentum, -99),
                # Last 20 histogram values for sparkline
                "hist_series": [round(v, 4) for v in histogram.iloc[-20:].tolist()],
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            })
            print(f"  ✓  {ticker:15s}  {EMOJI.get(momentum,'')} {momentum}")

        except Exception as e:
            print(f"  ✗  {ticker:15s}  Fehler: {e}")

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


# ─── Console Table Output ─────────────────────────────────────────────────────

def print_table(results: list[dict]):
    print("\n" + "═" * 90)
    print(f"  {'TICKER':<14} {'NAME':<26} {'PREIS':>8}  {'WK%':>7}  {'MACD':>8}  {'HIST':>8}  SIGNAL")
    print("─" * 90)

    for r in results:
        chg_str  = f"{r['chg_pct']:+.2f}%"
        macd_str = f"{r['macd']:+.4f}"
        hist_str = f"{r['histogram']:+.4f}"
        em       = EMOJI.get(r["momentum"], "")
        label    = f"{em} {r['momentum']}"
        print(
            f"  {r['ticker']:<14} {r['name']:<26} "
            f"{r['price']:>8.2f}  {chg_str:>7}  {macd_str:>8}  {hist_str:>8}  {label}"
        )

    print("═" * 90)
    bull = sum(1 for r in results if "Bullish" in r["momentum"])
    bear = sum(1 for r in results if "Bearish" in r["momentum"])
    cross = sum(1 for r in results if "Crossover" in r["momentum"])
    print(f"\n  {bull} Bullish  ·  {bear} Bearish  ·  {cross} Crossovers  ·  {len(results)} total")
    print(f"  Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')} local\n")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weekly MACD Momentum Screener")
    parser.add_argument("--tickers", nargs="+", metavar="TICKER",
                        help="Eigene Ticker-Liste (Leerzeichen-getrennt)")
    parser.add_argument("--weeks",   type=int, default=104,
                        help="Historische Wochen laden (min 60, default 104)")
    parser.add_argument("--json",    action="store_true",
                        help="JSON-Output statt Tabelle (für Web-App)")
    parser.add_argument("--out",     metavar="FILE",
                        help="JSON in Datei schreiben (z.B. macd_data.json)")
    args = parser.parse_args()

    if args.tickers:
        tickers = {t: t for t in args.tickers}
    else:
        tickers = DEFAULT_TICKERS

    results = screen(tickers, weeks=args.weeks)

    if args.json or args.out:
        payload = json.dumps(results, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(payload)
            print(f"\n  JSON gespeichert → {args.out}")
        else:
            print(payload)
    else:
        print_table(results)


if __name__ == "__main__":
    main()
