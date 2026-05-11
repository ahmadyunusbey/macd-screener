"""
Weekly MACD Momentum Screener (mit Follow-Through Filter)
==========================================================
Zieht wöchentliche Schlusskurse via yfinance, berechnet MACD (12/26/9)
und klassifiziert das Momentum-Signal für jede Position.

Follow-Through Logik:
  Ein Crossover gilt erst als bestätigt wenn MACD mindestens N Wochen
  konsistent auf der richtigen Seite der Signallinie bleibt.

Usage:
    python macd_screener.py                      # Default-Watchlist
    python macd_screener.py --tickers X Y Z      # Eigene Tickers
    python macd_screener.py --json               # JSON-Output für Web-App
    python macd_screener.py --followthrough 3    # 3 Wochen Follow-Through
    python macd_screener.py --weeks 156          # Mehr History
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
    "ASHM.L":       "ASHMORE GROUP",
    "AV.L":         "AVIVA",
    "BATS.L":       "BRITISH AMERICAN TOBACCO",
    "DNLM.L":       "DUNELM GROUP",
    "ENOG.L":       "ENERGEAN",
    "FLNG":         "FLEX LNG",
    "GCP.L":        "GCP INFRASTRUCTRE",
    "HSBA.L":       "HSBC HOLDINGS",
    "HSBK.IL":      "HALYQ BANK",
    "INPP.L":       "INTERNATIONAL PUBLIC",
    "ITH.L":        "ITHACA",
    "KAP.IL":       "KAZATOM",
    "LAND.L":       "LAND SECURITIES",
    "LGEN.L":       "LEGAL & GENERAL",
    "MNG.L":        "M&G",
    "MONY.L":       "MONEY GROUP",
    "NESN.SW":      "NESTLE",
    "OSB.L":        "OSB GROUP",
    "PBR-A":        "PETROBRAS",
    "RIO.L":        "RIO TINTO",
    "RWS.L":        "RWS",
    "SDLF.L":       "STANDARD LIFE",
    "SQZ.L":        "SERICA",
    "SREN.SW":      "SWISS RE",
    "TRIG.L":       "THE RENEWABLE",
    "UKW.L":        "GREENCOAT UK",
    "VCT.L":        "VICTREX",
    "VOD.L":        "VODAFONE",
    "ZIG.L":        "ZIGUP",
    # Ebene 2 – Royalties Watchlist
    "FNV":          "FRANCO-NEVADA",
    "OR":           "OR ROYALTIES",
    "RGLD":         "ROYAL GOLD",
    "TFPM":         "TRIPLE FLAG PM",
    "WPM":          "WHEATON PRECIOUS",
    # Ebene 3 – SE/CH Compounders
    "ALC.SW":       "ALCON",
    "ATCO-A.ST":    "ATLAS COPCO",
    "ADDT-B.ST":    "ADDTECH",
    "BAKKA.OL":     "BAKKAFROST",
    "BAYN.DE":      "BAYER AG",
    "BEAN.SW":      "BELIMO",
    "BON":          "BONHEUR",
    "CEVI.ST":      "CELLAVISION",
    "DG.PA":        "VINCI",
    "DSV.CO":       "DSV A/S",
    "ESSITY-B.ST":  "ESSITY",
    "FER":          "FERROVIAL",
    "HLMA.L":       "HALMA",
    "HOLN.SW":      "HOLCIM",
    "INDT.ST":      "INDUTRADE",
    "LAGR-B.ST":    "LAGERCRANTZ",
    "LIFCO-B.ST":   "LIFCO",
    "MYCR.ST":      "MYCRONIC",
    "NDINSCKL1.CO": "NORDIC SM CAPS",
    "NVO":          "NOVO NORDISC",
    "SAND.ST":      "SANDVIK",
    "SIKA.SW":      "SIKA",
    "SKA-B.ST":     "SKANSKA",
    "TOM.OL":       "TOMRA",
    "VIT-B.ST":     "VITEC SOFTWARE",
    "VACN.SW":      "VAT GROUP",
    "VITR.ST":      "VITROLIFE",
    "YAR.OL":       "YARA",
    # Ebene 4 – Thematic ETFs
    "VEGI":         "iShares MSCI Agri ETF",
    "VIOG":         "Vanguard S&P SmallCap 600 Growth",
    "XBI":          "SPDR S&P Biotech ETF",
    "FTEC":         "FIDELITY INFORMATION TECHNOLOGY",
    "UKRN.D":       "UKRAINE RECONSTRUCTION",
    # Ebene 5 – Speculation
    "9618.HK":      "JD.COM",
    "ARQQ":         "ARQIT",
    "BLDP":         "BALLARD POWER",
    "DGE.L":        "DIAGEO",
    "DOKA.SW":      "DORMAKABA",
    "FXPO.L":       "FERREXPO",
    "INFX.DE":      "INFINEON",
    "ITM.L":        "ITM POWER",
    "KSPI":         "KASPI",
    "NEL.OL":       "NEL ASA",
    "NU":           "NU HOLDING",
    "RBREW.CO":     "ROYAL UNIBREW",
    "RBI.VI":       "RAIFFEISEN",
    "RI.PA":        "PERNOD RICARD",
    "SANN.SW":      "SANTHERA",
    "TRN.MI":       "TERNA",
    "WIE.VI":       "WIENERBERGER",
    # Makro – Rohstoffe & FX
    "GC=F":         "GOLD",
    "SI=F":         "SILBER",
    "CL=F":         "ÖL (WTI)",
    "BZ=F":         "ÖL (BRENT)",
    "HG=F":         "COPPER",
    "NG=F":         "NATURAL GAS",
    "EURUSD=X":     "EUR/USD",
    "GBPUSD=X":     "GBP/USD",
    "JPY=X":        "USD/JPY",
    "CHF=X":        "USD/CHF",
    "000016.SS":    "SSE 50 INDEX",
    "510050.SS":    "CHINA AMC SS50 ETF",
    # Ukraine-Aufbau
    "ENR.DE":       "SIEMENS ENERGY",
    "BA.L":         "BAE SYSTEMS",
    "CAT":          "CATERPILLAR",
    "JCI":          "JOHNSON CONTROLS",
    "ABBN.SW":      "ABB",
    "ETN":          "EATON",
    "CRH.L":        "CRH",
    "SU.PA":        "SCHNEIDER ELECTRIC",
    "EMR":          "EMERSON ELECTRIC",
    "RHM.DE":       "RHEINMETALL",
    "FLR":          "FLUOR",
    "PWR":          "QUANTA SERVICES",
    "J":            "JACOBS SOLUTIONS",
    "ACM":          "AECOM",
    "KBR":          "KBR",
    "WOR.AX":       "WORLEY",
    "TE.PA":        "TECHNIP ENERGIES",
    "SPM.MI":       "SAIPEM",
    "ANA.MC":       "ACCIONA",
    "EN.PA":        "BOUYGUES",
    "HOT.DE":       "HOCHTIEF",
    "STR.VI":       "STRABAG",
    "NEE":          "NEXTERA ENERGY",
    "ENGI.PA":      "ENGIE",
    "RWE.DE":       "RWE",
    "EOAN.DE":      "E.ON",
    "IBE.MC":       "IBERDROLA",
    "ORSTED.CO":    "ØRSTED",
    "HEI.DE":       "HEIDELBERG MATERIALS",
    "SGO.PA":       "SAINT-GOBAIN",
    "VMC":          "VULCAN MATERIALS",
    "MLM":          "MARTIN MARIETTA",
    "DE":           "DEERE & COMPANY",
    "6301.T":       "KOMATSU",
    "METSO.HE":     "METSO",
    "WEIR.L":       "WEIR GROUP",
    "LMT":          "LOCKHEED MARTIN",
    "NOC":          "NORTHROP GRUMMAN",
    "GD":           "GENERAL DYNAMICS",
    "HO.PA":        "THALES",
    "LDO.MI":       "LEONARDO",
    "HON":          "HONEYWELL",
    "PH":           "PARKER-HANNIFIN",
    "ITW":          "ILLINOIS TOOL WORKS",
    # SKAGEN VEKST
# Health Care
"NOVO-B.CO":  "NOVO NORDISK",
"HLUN-B.CO":   "H. LUNDBECK",
# Industrials
"ISS.CO":     "ISS A/S",
"SKF-B.ST":   "SKF B",
"VOLV-B.ST":  "VOLVO B",
"0001.HK":    "CK HUTCHISON",
"CDLR":       "CADELER",
"BRAV.ST":    "BRAVIDA",
"EZJ.L":      "EASYJET",
"VWS.CO":     "VESTAS WIND",
"TASK":       "TASKUS",
# Financials
"2318.HK":    "PING AN INSURANCE",
"086790.KS":  "HANA FINANCIAL",
"NDA-FI.HE":  "NORDEA BANK",
"105560.KS":  "KB FINANCIAL",
"ENX.PA":     "EURONEXT",
"C":          "CITIGROUP",
"LSEG.L":     "LONDON STOCK EXCHANGE",
"003690.KS":  "KOREAN REINSURANCE",
"B3SA3.SA":   "B3 BRASIL",
"AIG":        "AIG",
"KINV-B.ST":  "KINNEVIK B",
# Materials
"UPM.HE":     "UPM-KYMMENE",
"WIE.VI":     "WIENERBERGER",
"BOL.ST":     "BOLIDEN",
"ELO.OL":     "ELOPAK",
"ELK.OL":     "ELKEM",
"SGZH.ME":    "SEGEZHA",  
# Consumer Staples
"CARL-B.CO":  "CARLSBERG B",
"NOMD":       "NOMAD FOODS",
"TAP":        "MOLSON COORS",
"TSN":        "TYSON FOODS",
"WALMEX.MX":  "WAL-MART MEXICO",
# Information Technology
"005930.KS":  "SAMSUNG ELECTRONICS",
"NOKIA.HE":   "NOKIA",
"TIETO.HE":   "TIETOEVRY",
# Real Estate
"1113.HK":    "CK ASSET HOLDINGS",
"PUBLI.OL":   "PUBLIC PROPERTY INVEST",
"BALD-B.ST":"FASTIGHETS BALDER",
"SVEAF.ST":   "SVEAFASTIGHETER",
# Communication Services
"TEL.OL":     "TELENOR",
"GOOGL":      "ALPHABET",
# Energy
"HYDR":       "HYDROGEN ETF",
"SHELL.AS":   "SHELL",
"TGS.OL":     "TGS GEOPHYSICAL",
"PLSV.OL":    "PARATUS ENERGY",
# Halbleiter
"ALAB":	"Astera Labs",
"AMAT":	"Applied Materials",
"AMD":	"AMD",
"ADI":	"Analog Devices",
"ARM":	"Arm Holdings",
"ASML":	"ASML",
"AVGO":	"Broadcom",
"AIXA.DE": "Aixtron",
"CRDO":	"Credo Technology",
"GFS":	"GLOBALFOUNDRIES",
"IFX.DE":   "Infineon",
"INTC":	"Intel",
"KLAC":	"KLA",
"LRCX":	"Lam Research",
"MCHP":	"Microchip Technology",
"MPWR":	"Monolithic Power",
"MRVL":	"Marvell",
"MU":	"Micron",
"NVDA":	"NVIDIA",
"NXPI":	"NXP",
"0700.HK":  "MediaTek",
"6963.T":   "KIOXIA",
"ON":	"ON Semiconductor",
"QCOM":	"QUALCOMM",
"SLN.DE": "Siltronic",
"SNDK":	"SanDisk",
"STM":	"STMicroelectronics",
"STX":	"Seagate",
"SWKS":	"Skyworks",
"TSM":	"TSMC",
"TXN":	"Texas Instruments",
"005930.KS": "Samsung Electronics",
"000660.KS": "SK Hynix",
"WDC":	"Western Digital",
# Metalls
"AREC": "AMERICAN RESSOURCES",
"ALI1.F": "Almonty Industries",
"CRML": "Critical Metals",
"DC-A.TO": "Dundee Corporation",
"EUA.L": "Eurasia Mining",
"GLEN.L": "Glencore plc",
"IDR": "Idaho Strategic Resources",
"IMPUY": "Impala Platinum",
"MP": "MP Materials",
"REB.F": "Arafura Rare Earths",
"SBSW": "Sibanye Stillwater",
"UAMY": "United States Antimony",
"UROY": "URANIUM ROYALTY",
"USAR": "USA RARE EARTH",
"UUUU": "ENERGY FUELS",
# China
    "KWEB": "KraneShares CSI China Internet ETF",
    "0006.HK": "POWER ASSETS",
}


# ─── MACD Berechnung ──────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_macd(closes: pd.Series, fast=12, slow=26, signal=9):
    macd_line   = ema(closes, fast) - ema(closes, slow)
    signal_line = ema(macd_line, signal)
    histogram   = macd_line - signal_line
    return macd_line, signal_line, histogram


# ─── Follow-Through Klassifikation ───────────────────────────────────────────

def classify_momentum(
    macd_line:   pd.Series,
    signal_line: pd.Series,
    histogram:   pd.Series,
    followthrough: int = 2,
) -> dict:
    n = len(macd_line)
    if n < followthrough + 2:
        return {"momentum": "Insufficient data", "confirmed": False, "ft_weeks": 0, "above_zero": False}

    m_last = macd_line.iloc[-1]
    s_last = signal_line.iloc[-1]
    h_last = histogram.iloc[-1]
    h_prev = histogram.iloc[-2]

    above_zero  = m_last > 0
    hist_rising = h_last > h_prev
    bullish_now = m_last > s_last

    # 1) Aufeinanderfolgende Wochen auf der richtigen Seite der Signallinie
    ft_weeks = 0
    for i in range(1, min(followthrough + 3, n)):
        m = macd_line.iloc[-i]
        s = signal_line.iloc[-i]
        if bullish_now and m > s:
            ft_weeks += 1
        elif not bullish_now and m < s:
            ft_weeks += 1
        else:
            break

    confirmed = ft_weeks >= followthrough

    # 2) Higher Highs / Lower Lows im Histogramm
    #    Jeder Balken der letzten ft_weeks muss höher (bull) / tiefer (bear)
    #    sein als der vorherige — nur prüfen wenn Crossover bereits bestätigt
    hh_weeks = 0
    if confirmed and ft_weeks >= 1:
        for i in range(1, ft_weeks + 1):
            if -i - 1 < -n:
                break
            h_cur  = float(histogram.iloc[-i])
            h_prev = float(histogram.iloc[-i - 1])
            if bullish_now and h_cur > h_prev:
                hh_weeks += 1
            elif not bullish_now and h_cur < h_prev:
                hh_weeks += 1
            else:
                break

    hh_confirmed = hh_weeks >= followthrough

    if bullish_now:
        if hh_confirmed and above_zero:
            momentum = "Strong Bullish Crossover ↑↑"
        elif hh_confirmed:
            momentum = "Bullish Crossover ↑↑"
        elif confirmed and above_zero:
            momentum = "Strong Bullish Crossover"
        elif confirmed:
            momentum = "Bullish Crossover"
        elif above_zero and hist_rising:
            momentum = "Bullish Momentum"
        elif above_zero:
            momentum = "Bullish (Fading)"
        else:
            momentum = f"Unconfirmed Bullish ({ft_weeks}/{followthrough}W)"
    else:
        if hh_confirmed and not above_zero:
            momentum = "Strong Bearish Crossover ↓↓"
        elif hh_confirmed:
            momentum = "Bearish Crossover ↓↓"
        elif confirmed and not above_zero:
            momentum = "Strong Bearish Crossover"
        elif confirmed:
            momentum = "Bearish Crossover"
        elif not above_zero and not hist_rising:
            momentum = "Bearish Momentum"
        elif not above_zero:
            momentum = "Bearish (Fading)"
        else:
            momentum = f"Unconfirmed Bearish ({ft_weeks}/{followthrough}W)"

    return {
        "momentum":     momentum,
        "confirmed":    confirmed,
        "hh_confirmed": hh_confirmed,
        "ft_weeks":     ft_weeks,
        "hh_weeks":     hh_weeks,
        "above_zero":   above_zero,
    }


# ─── Score für Sortierung ─────────────────────────────────────────────────────

def momentum_score(momentum: str) -> int:
    if "Strong Bullish Crossover ↑↑" in momentum: return 8
    if "Bullish Crossover ↑↑"        in momentum: return 7
    if "Strong Bullish Crossover"     in momentum: return 6
    if "Bullish Crossover"            in momentum: return 5
    if "Bullish Momentum"             in momentum: return 4
    if "Bullish (Fading)"             in momentum: return 3
    if "Unconfirmed Bullish"          in momentum: return 2
    if "Unconfirmed Bearish"          in momentum: return -1
    if "Bearish (Fading)"             in momentum: return -2
    if "Bearish Momentum"             in momentum: return -3
    if "Bearish Crossover ↓↓"         in momentum: return -4
    if "Strong Bearish Crossover ↓↓"  in momentum: return -5
    if "Bearish Crossover"            in momentum: return -6
    if "Strong Bearish Crossover"     in momentum: return -7
    return -99

EMOJI = {
    "Strong Bullish Crossover ↑↑": "🚀🚀",
    "Bullish Crossover ↑↑":        "📈📈",
    "Strong Bullish Crossover":    "🚀",
    "Bullish Crossover":           "📈",
    "Bullish Momentum":            "⬆️ ",
    "Bullish (Fading)":            "〰️ ",
    "Unconfirmed Bullish":         "⏳",
    "Unconfirmed Bearish":         "⏳",
    "Bearish (Fading)":            "〰️ ",
    "Bearish Momentum":            "⬇️ ",
    "Strong Bearish Crossover ↓↓": "🔻🔻",
    "Bearish Crossover ↓↓":        "📉📉",
    "Strong Bearish Crossover":    "🔻",
    "Bearish Crossover":           "📉",
    "Insufficient data":           "❓",
}

def get_emoji(m: str) -> str:
    for k, v in EMOJI.items():
        if k in m: return v
    return ""


# ─── Screener ────────────────────────────────────────────────────────────────

def screen(tickers: dict, weeks: int = 104, followthrough: int = 2) -> list[dict]:
    results = []
    period  = f"{max(weeks, 60)}wk"

    print(f"\n  Lade {len(tickers)} Ticker · wöchentlich · Follow-Through: {followthrough}W\n")

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
            res = classify_momentum(macd_line, signal_line, histogram, followthrough)

            price   = float(closes.iloc[-1])
            price_1 = float(closes.iloc[-2])
            chg_pct = (price - price_1) / price_1 * 100

            momentum = res["momentum"]
            results.append({
                "ticker":       ticker,
                "name":         name,
                "price":        round(price, 2),
                "chg_pct":      round(chg_pct, 2),
                "macd":         round(float(macd_line.iloc[-1]), 4),
                "signal":       round(float(signal_line.iloc[-1]), 4),
                "histogram":    round(float(histogram.iloc[-1]), 4),
                "momentum":     momentum,
                "confirmed":    res["confirmed"],
                "hh_confirmed": res["hh_confirmed"],
                "ft_weeks":     res["ft_weeks"],
                "hh_weeks":     res["hh_weeks"],
                "ft_required":  followthrough,
                "score":        momentum_score(momentum),
                "hist_series":  [round(v, 4) for v in histogram.iloc[-20:].tolist()],
                "fetched_at":   datetime.utcnow().isoformat() + "Z",
            })
            hh = "↑↑" if res["hh_confirmed"] else ("↑" if res["confirmed"] else "")
            conf = f"{'✓✓' if res['hh_confirmed'] else ('✓' if res['confirmed'] else '⏳')}{res['ft_weeks']}/{followthrough}W {hh}"
            print(f"  {get_emoji(momentum)}  {ticker:15s}  {momentum:<42s}  {conf}")

        except Exception as e:
            print(f"  ✗  {ticker:15s}  Fehler: {e}")

    results.sort(key=lambda r: r["score"], reverse=True)
    return results


# ─── Console Table Output ─────────────────────────────────────────────────────

def print_table(results: list[dict]):
    ft = results[0]["ft_required"] if results else 2
    print("\n" + "═" * 108)
    print(f"  {'TICKER':<15} {'NAME':<24} {'PREIS':>8}  {'WK%':>7}  {'MACD':>8}  {'HIST':>8}  {'FT':>8}  SIGNAL")
    print("─" * 108)
    for r in results:
        hh = r.get("hh_confirmed", False)
        ft_str = f"{'✓✓' if hh else ('✓' if r['confirmed'] else '⏳')}{r['ft_weeks']}/{r['ft_required']}W"
        print(
            f"  {r['ticker']:<15} {r['name']:<24} "
            f"{r['price']:>8.2f}  {r['chg_pct']:>+7.2f}%  {r['macd']:>+8.4f}  "
            f"{r['histogram']:>+8.4f}  {ft_str:>8}  {get_emoji(r['momentum'])} {r['momentum']}"
        )
    print("═" * 108)
    hh_bull = sum(1 for r in results if "↑↑" in r["momentum"])
    bull    = sum(1 for r in results if "Bullish" in r["momentum"] and "Unconfirmed" not in r["momentum"] and "↑↑" not in r["momentum"])
    bear    = sum(1 for r in results if "Bearish" in r["momentum"] and "Unconfirmed" not in r["momentum"])
    unconf  = sum(1 for r in results if "Unconfirmed" in r["momentum"])
    print(f"\n  {hh_bull} Bullish ✓✓(HH)  ·  {bull} Bullish ✓  ·  {bear} Bearish  ·  {unconf} Unbestätigt  ·  {len(results)} total")
    print(f"  Follow-Through: {ft}W + Higher Highs  ·  Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Weekly MACD Momentum Screener mit Follow-Through")
    parser.add_argument("--tickers",       nargs="+", metavar="TICKER")
    parser.add_argument("--weeks",         type=int, default=104)
    parser.add_argument("--followthrough", type=int, default=2,
                        help="Wochen Follow-Through für Crossover-Bestätigung (default: 2)")
    parser.add_argument("--json",          action="store_true")
    parser.add_argument("--out",           metavar="FILE")
    args = parser.parse_args()

    tickers = {t: t for t in args.tickers} if args.tickers else DEFAULT_TICKERS
    results = screen(tickers, weeks=args.weeks, followthrough=args.followthrough)

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
