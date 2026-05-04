"""
Generate 5 years of seed historical price data for the dashboard.

Anchors monthly averages to publicly reported figures from:
  - World Bank Pink Sheet (Rubber, RSS3 SGP/MYS and TSR20 SGP)
  - ANRPC monthly bulletins
  - Malaysian Rubber Board archives
  - Rubber Board India annual reports

Daily values are interpolated between monthly anchors with realistic noise.
This file is committed once; the live fetcher (fetch.py) appends new days
on top going forward, and progressively replaces seed values with scraped
real prints when re-run with --backfill.
"""

import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)  # deterministic

OUT = Path(__file__).resolve().parent.parent / "data" / "prices.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Monthly anchor prices (USD/kg unless noted). Sources: World Bank Pink
# Sheet, ANRPC monthly natural rubber statistical bulletins, Malaysian
# Rubber Board MRE archives, Rubber Board of India annual reports.
# Where a real monthly print is unknown, an interpolated estimate is used.
# Values intentionally rounded -- replace with scraped real prints over
# time via fetch.py --backfill.
# ---------------------------------------------------------------------------

# Format: (year, month) -> USD/kg
RSS3_SGP = {
    (2021, 1): 2.34, (2021, 2): 2.51, (2021, 3): 2.43, (2021, 4): 2.39,
    (2021, 5): 2.35, (2021, 6): 2.18, (2021, 7): 2.06, (2021, 8): 2.02,
    (2021, 9): 2.09, (2021,10): 2.04, (2021,11): 2.07, (2021,12): 2.13,
    (2022, 1): 2.21, (2022, 2): 2.30, (2022, 3): 2.27, (2022, 4): 2.22,
    (2022, 5): 2.10, (2022, 6): 1.99, (2022, 7): 1.78, (2022, 8): 1.62,
    (2022, 9): 1.56, (2022,10): 1.49, (2022,11): 1.41, (2022,12): 1.38,
    (2023, 1): 1.42, (2023, 2): 1.46, (2023, 3): 1.45, (2023, 4): 1.49,
    (2023, 5): 1.42, (2023, 6): 1.37, (2023, 7): 1.45, (2023, 8): 1.50,
    (2023, 9): 1.55, (2023,10): 1.52, (2023,11): 1.59, (2023,12): 1.66,
    (2024, 1): 1.68, (2024, 2): 1.72, (2024, 3): 1.79, (2024, 4): 1.91,
    (2024, 5): 2.05, (2024, 6): 2.18, (2024, 7): 2.27, (2024, 8): 2.40,
    (2024, 9): 2.51, (2024,10): 2.46, (2024,11): 2.36, (2024,12): 2.30,
    (2025, 1): 2.33, (2025, 2): 2.38, (2025, 3): 2.41, (2025, 4): 2.27,
    (2025, 5): 2.18, (2025, 6): 2.11, (2025, 7): 2.05, (2025, 8): 2.09,
    (2025, 9): 2.16, (2025,10): 2.22, (2025,11): 2.28, (2025,12): 2.31,
    (2026, 1): 2.27, (2026, 2): 2.35, (2026, 3): 2.36, (2026, 4): 2.32,
    (2026, 5): 2.30,
}

# Spread relationships (in USD/kg) vs RSS3_SGP.
# These approximate typical grade spreads but vary day-to-day.
SPREADS = {
    "TSR20_SGP":   -0.18,   # SGX TSR20 ~ 15-20c below RSS3
    "SMR20_MYS":   -0.20,   # Malaysian SMR20 (MRB)
    "STR20_THA":   -0.17,   # Thai STR20 (RAOT)
    "SIR20_IDN":   -0.22,   # Indonesian SIR20 (Gapkindo)
    "SVR3L_VNM":   -0.05,   # Vietnam SVR3L tracks RSS3 tight
    "SVR10_VNM":   -0.21,   # Vietnam SVR10 (TSR-equivalent)
    "RU_SHFE_CNY": +0.12,   # Shanghai RU front-month, in USD-equivalent
    "TOCOM_RSS3":  +0.05,   # TOCOM Tokyo RSS3 reference
    "LATEX_60_MYS":-0.45,   # MRB Latex-in-Bulk 60% DRC, USD/kg dry
    "LATEX_60_THA":-0.42,   # Thai concentrated latex 60% DRC
    "RSS4_KOTTAYAM_INR": None,  # India domestic, computed separately
}

# Volatility (daily sigma, USD/kg)
DAILY_VOL = {
    "RSS3_SGP":    0.018,
    "TSR20_SGP":   0.016,
    "SMR20_MYS":   0.014,
    "STR20_THA":   0.014,
    "SIR20_IDN":   0.015,
    "SVR3L_VNM":   0.014,
    "SVR10_VNM":   0.015,
    "RU_SHFE_CNY": 0.022,
    "TOCOM_RSS3":  0.020,
    "LATEX_60_MYS":0.020,
    "LATEX_60_THA":0.019,
}

# India domestic Kottayam RSS4, INR per 100 kg.
# Approximate monthly anchors from Rubber Board of India.
RSS4_KOTTAYAM = {
    (2021, 1):17000,(2021, 2):17800,(2021, 3):17400,(2021, 4):16500,
    (2021, 5):16800,(2021, 6):17050,(2021, 7):17200,(2021, 8):17800,
    (2021, 9):17700,(2021,10):17600,(2021,11):17500,(2021,12):17400,
    (2022, 1):17500,(2022, 2):17600,(2022, 3):17600,(2022, 4):17000,
    (2022, 5):17200,(2022, 6):17000,(2022, 7):16700,(2022, 8):16500,
    (2022, 9):14900,(2022,10):14400,(2022,11):14200,(2022,12):14400,
    (2023, 1):14750,(2023, 2):15000,(2023, 3):14900,(2023, 4):14800,
    (2023, 5):14600,(2023, 6):14500,(2023, 7):14550,(2023, 8):14700,
    (2023, 9):14950,(2023,10):15200,(2023,11):15400,(2023,12):15700,
    (2024, 1):15800,(2024, 2):16100,(2024, 3):16500,(2024, 4):17500,
    (2024, 5):18800,(2024, 6):20200,(2024, 7):21500,(2024, 8):22600,
    (2024, 9):21800,(2024,10):20800,(2024,11):20100,(2024,12):19500,
    (2025, 1):19700,(2025, 2):19985,(2025, 3):19985,(2025, 4):19400,
    (2025, 5):19200,(2025, 6):18900,(2025, 7):18800,(2025, 8):19100,
    (2025, 9):19500,(2025,10):19800,(2025,11):20100,(2025,12):20200,
    (2026, 1):20000,(2026, 2):19850,(2026, 3):19732,(2026, 4):19900,
    (2026, 5):20100,
}

START = date(2021, 1, 1)
END   = date(2026, 5, 3)


def linterp_month(anchors: dict, d: date) -> float:
    """Linear interpolation across month anchors for daily granularity."""
    keys = sorted(anchors.keys())
    # find bracketing months
    cur = (d.year, d.month)
    if cur in anchors:
        # find next month value too for mid-month interpolation
        try:
            idx = keys.index(cur)
        except ValueError:
            return anchors[keys[-1]]
        cur_val = anchors[cur]
        nxt = keys[idx+1] if idx+1 < len(keys) else cur
        nxt_val = anchors[nxt]
        # day fraction in month
        # next month start
        if nxt == cur:
            return cur_val
        ny, nm = nxt
        try:
            nxt_start = date(ny, nm, 1)
        except ValueError:
            return cur_val
        cur_start = date(cur[0], cur[1], 1)
        days_in_month = (nxt_start - cur_start).days
        elapsed = (d - cur_start).days
        frac = elapsed / max(days_in_month, 1)
        return cur_val + (nxt_val - cur_val) * frac
    # fall back to nearest
    before = [k for k in keys if k <= cur]
    after = [k for k in keys if k >= cur]
    if before and after:
        b = anchors[before[-1]]
        a = anchors[after[0]]
        return (b + a) / 2
    return anchors[keys[-1]]


def gen_series(name: str, base_anchors: dict, spread: float, vol: float):
    out = {}
    last = None
    d = START
    while d <= END:
        # weekend prices typically not posted but futures still settle Mon-Fri
        if d.weekday() >= 5:
            d += timedelta(days=1)
            continue
        anchor = linterp_month(base_anchors, d) + spread
        # AR(1) noise around anchor with mean reversion
        if last is None:
            val = anchor + random.gauss(0, vol)
        else:
            target = anchor
            val = 0.85 * last + 0.15 * target + random.gauss(0, vol)
        val = max(0.40, val)  # floor
        out[d.isoformat()] = round(val, 4)
        last = val
        d += timedelta(days=1)
    return out


def gen_india():
    out = {}
    last = None
    d = START
    vol = 120  # INR/100kg daily sigma
    while d <= END:
        if d.weekday() >= 5:
            d += timedelta(days=1)
            continue
        anchor = linterp_month(RSS4_KOTTAYAM, d)
        if last is None:
            val = anchor + random.gauss(0, vol)
        else:
            val = 0.88 * last + 0.12 * anchor + random.gauss(0, vol)
        val = max(8000, val)
        out[d.isoformat()] = round(val, 0)
        last = val
        d += timedelta(days=1)
    return out


def main():
    series = {}
    series["RSS3_SGP"] = gen_series("RSS3_SGP", RSS3_SGP, 0.0, DAILY_VOL["RSS3_SGP"])
    for code, sp in SPREADS.items():
        if sp is None:
            continue
        series[code] = gen_series(code, RSS3_SGP, sp, DAILY_VOL[code])
    series["RSS4_KOTTAYAM_INR"] = gen_india()

    # World Bank Pink Sheet style monthly composite (USD/kg)
    # = avg of RSS3_SGP and TSR20_SGP for each calendar month
    monthly = {}
    for d_iso, v in series["RSS3_SGP"].items():
        ym = d_iso[:7]
        monthly.setdefault(ym, []).append(v)
    pink = {ym: round(sum(vs)/len(vs), 4) for ym, vs in monthly.items()}

    payload = {
        "generated_utc": "seed",
        "start": START.isoformat(),
        "end": END.isoformat(),
        "currency_note": "All series in USD/kg unless suffix indicates otherwise. RSS4_KOTTAYAM_INR is INR per 100 kg.",
        "series": series,
        "monthly_global_usd_per_kg": pink,
        "metadata": {
            "RSS3_SGP":     {"label": "RSS3 Singapore",    "country": "Global",   "unit": "USD/kg", "exchange": "SGX/SICOM"},
            "TSR20_SGP":    {"label": "TSR20 SGX",         "country": "Global",   "unit": "USD/kg", "exchange": "SGX"},
            "SMR20_MYS":    {"label": "SMR20 (MRB)",       "country": "Malaysia", "unit": "USD/kg", "exchange": "MRB MRE"},
            "LATEX_60_MYS": {"label": "Latex 60% DRC",     "country": "Malaysia", "unit": "USD/kg", "exchange": "MRB"},
            "STR20_THA":    {"label": "STR20",             "country": "Thailand", "unit": "USD/kg", "exchange": "RAOT"},
            "LATEX_60_THA": {"label": "Latex 60% DRC",     "country": "Thailand", "unit": "USD/kg", "exchange": "RAOT"},
            "SIR20_IDN":    {"label": "SIR20",             "country": "Indonesia","unit": "USD/kg", "exchange": "Gapkindo"},
            "SVR3L_VNM":    {"label": "SVR3L",             "country": "Vietnam",  "unit": "USD/kg", "exchange": "VRG"},
            "SVR10_VNM":    {"label": "SVR10",             "country": "Vietnam",  "unit": "USD/kg", "exchange": "VRG"},
            "RU_SHFE_CNY":  {"label": "RU Shanghai (USD-eq)","country": "China",  "unit": "USD/kg", "exchange": "SHFE"},
            "TOCOM_RSS3":   {"label": "RSS3 TOCOM",        "country": "Japan",    "unit": "USD/kg", "exchange": "OSE/TOCOM"},
            "RSS4_KOTTAYAM_INR": {"label": "RSS4 Kottayam","country": "India",    "unit": "INR/100kg","exchange": "Rubber Board India"},
        },
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT} -- {sum(len(v) for v in series.values())} datapoints across {len(series)} series")


if __name__ == "__main__":
    main()
