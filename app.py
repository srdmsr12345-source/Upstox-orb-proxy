"""
Ultimate NSE Scanner — app.py (Complete Rewrite)
=================================================
Pehle wali app.py 131 lines pe adhoori kat gayi thi (file beech mein
khatam ho gayi thi). Yeh poori naye sar se likhi gayi hai.

Architecture:
1. /scan POST — main endpoint, frontend yahi call karta hai
   a. NSE bhav-copy download (aaj ka OHLCV + delivery%)
   b. Pre-filter: price >= 20, turnover >= 50L (to reduce ~2000 → ~300)
   c. Symbol → instrument_key mapping (Upstox instrument master se)
   d. History fetch: filtered ~300 stocks ke liye 90-day candles (parallel)
   e. Indicators inject: EMA20, EMA50, RSI14, AVG_VOL_20, LOW_120, CLOSE_20D_AGO
   f. Saare scanners chalao (Stage2, SmartMoney, Bottom, Volume, Momentum, RS)
   g. ORB: sirf market hours mein, intraday candles se
   h. AI ranking (optional, async)
   i. Merge + return JSON

2. /health — proxy health check
3. /symbols — available symbols list (debug)
"""

import traceback
import time
from datetime import datetime

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import (
    PREFILTER_MIN_PRICE,
    PREFILTER_MIN_TURNOVER_LAKH,
    PREFILTER_MAX_CANDIDATES,
)
from modules.nse import NSEData as NSEDataModule
from modules.upstox import UpstoxAPI as UpstoxModule
from modules.history import build_history_fetcher
from modules.ai import ai_ranker
from modules.cache import cache

from plugins.stage2 import stage2_scanner
from plugins.smartmoney import smartmoney_scanner
from plugins.bottom import bottom_scanner
from plugins.volume import volume_scanner
from plugins.momentum import momentum_scanner
from plugins.relativestrength import relative_strength_scanner
from plugins.orb import orb_scanner

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def is_market_open():
    """Market open hai kya abhi (9:15 AM – 3:30 PM IST, Mon-Fri)."""
    ist = datetime.utcnow().replace(tzinfo=None)
    # IST = UTC + 5:30
    from datetime import timedelta
    ist = ist + timedelta(hours=5, minutes=30)
    if ist.weekday() >= 5:  # Saturday/Sunday
        return False
    market_open  = ist.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= ist <= market_close


def get_access_token():
    """Request header se Bearer token nikalta hai."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def build_instrument_map(upstox, symbols):
    """
    Symbol list ke liye instrument_key map banata hai.
    Returns: { "RELIANCE": "NSE_EQ|INE002A01018", ... }
    """
    inst_map = {}
    try:
        instruments = upstox.get_instruments()
        for inst in instruments:
            sym = (inst.get("trading_symbol") or inst.get("tradingsymbol") or "").strip().upper()
            key = inst.get("instrument_key", "")
            if sym and key:
                inst_map[sym] = key
    except Exception as e:
        print(f"[WARN] Instrument map fetch failed: {e}")
    return inst_map


def inject_history_indicators(merged_df, history_map):
    """
    History DataFrame map se indicators inject karta hai merged DataFrame mein.
    Adds: EMA20, EMA50, RSI14, AVG_VOL_20, LOW_120, CLOSE_20D_AGO columns.
    """
    from modules.history import HistoryFetcher

    ema20_map = {}
    ema50_map = {}
    rsi14_map = {}
    avgvol_map = {}
    low120_map = {}
    close20_map = {}

    for inst_key, hist_df in history_map.items():
        indicators = HistoryFetcher.compute_indicators(hist_df)
        if indicators is None:
            continue

        # instrument_key → SYMBOL mapping reverse karne ke liye
        # hum merged_df mein INSTRUMENT_KEY column se dhundhenge
        ema20_map[inst_key]  = indicators.get("EMA20")
        ema50_map[inst_key]  = indicators.get("EMA50")
        rsi14_map[inst_key]  = indicators.get("RSI14")
        avgvol_map[inst_key] = indicators.get("AVG_VOL_20")

        # LOW_120 aur CLOSE_20D_AGO directly history series se
        if hist_df is not None and not hist_df.empty:
            closes = pd.to_numeric(hist_df["close"], errors="coerce")
            lows   = pd.to_numeric(hist_df["low"],   errors="coerce")
            low120_map[inst_key]  = float(lows.min())   if not lows.empty   else None
            close20_map[inst_key] = float(closes.iloc[-21]) if len(closes) >= 21 else None

    if "INSTRUMENT_KEY" not in merged_df.columns:
        # EMA injection ke liye hume INSTRUMENT_KEY column chahiye
        return merged_df

    df = merged_df.copy()
    df["EMA20"]        = df["INSTRUMENT_KEY"].map(ema20_map)
    df["EMA50"]        = df["INSTRUMENT_KEY"].map(ema50_map)
    df["RSI14"]        = df["INSTRUMENT_KEY"].map(rsi14_map)
    df["AVG_VOL_20"]   = df["INSTRUMENT_KEY"].map(avgvol_map)
    df["LOW_120"]      = df["INSTRUMENT_KEY"].map(low120_map)
    df["CLOSE_20D_AGO"]= df["INSTRUMENT_KEY"].map(close20_map)

    return df


def run_all_scanners(df):
    """Saare plugins chalata hai, results dict mein collect karta hai."""
    results = {}

    # Stage 2 (EMA20 > EMA50 + volume)
    try:
        r = stage2_scanner.top_candidates(df, limit=25)
        results["stage2"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["stage2"] = []
        print(f"[WARN] stage2 failed: {e}")

    # Smart Money (high vol + high delivery + green)
    try:
        r = smartmoney_scanner.top_candidates(df, limit=25)
        results["smartmoney"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["smartmoney"] = []
        print(f"[WARN] smartmoney failed: {e}")

    # Bottom Fishing (near 120-day low, volume surge)
    try:
        r = bottom_scanner.top_candidates(df, limit=25)
        results["bottom"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["bottom"] = []
        print(f"[WARN] bottom failed: {e}")

    # Volume Spike
    try:
        r = volume_scanner.top_candidates(df, limit=25)
        results["volume"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["volume"] = []
        print(f"[WARN] volume failed: {e}")

    # Momentum (RSI based)
    try:
        r = momentum_scanner.top_candidates(df, limit=25)
        results["momentum"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["momentum"] = []
        print(f"[WARN] momentum failed: {e}")

    # Relative Strength — requires CLOSE_20D_AGO
    try:
        r = relative_strength_scanner.top_candidates(df, None, limit=25)
        results["relative_strength"] = r.to_dict("records") if not r.empty else []
    except Exception as e:
        results["relative_strength"] = []
        print(f"[WARN] relative_strength failed: {e}")

    return results


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Ultimate NSE Scanner API",
        "endpoints": {
            "POST /scan": "Run all scanners",
            "GET /health": "Health check",
            "GET /symbols": "List available symbols"
        }
    })


@app.route("/symbols", methods=["GET"])
def symbols():
    """Available symbols return karta hai (bhav-copy se)."""
    try:
        nse = NSEDataModule()
        result = nse.latest_data()
        df = result["data"]
        syms = df["SYMBOL"].dropna().unique().tolist() if "SYMBOL" in df.columns else []
        return jsonify({"status": "success", "count": len(syms), "symbols": syms[:200]})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/scan", methods=["POST"])
def scan():
    t0 = time.time()
    token = get_access_token()
    if not token:
        return jsonify({"success": False, "error": "Authorization header missing"}), 401

    # ── STEP 1: NSE bhav-copy ──────────────────────────────────────────────
    try:
        nse = NSEDataModule()
        nse_result = nse.latest_data()
        bhav_df = nse_result["data"]
        scan_date = nse_result["date"]
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"NSE bhav-copy fetch failed: {e}"}), 500

    if bhav_df.empty:
        return jsonify({"success": False, "error": "Bhav-copy empty — market band hai ya NSE server down"}), 500

    print(f"[INFO] Bhav-copy loaded: {len(bhav_df)} rows for {scan_date}")

    # ── STEP 2: Pre-filter ────────────────────────────────────────────────
    df = bhav_df.copy()
    df.columns = df.columns.str.strip()

    for col in ["CLOSE", "TOTTRDQTY", "TOTTRDVAL"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "CLOSE" in df.columns:
        df = df[df["CLOSE"] >= PREFILTER_MIN_PRICE]

    if "TOTTRDVAL" in df.columns:
        df = df[df["TOTTRDVAL"] >= PREFILTER_MIN_TURNOVER_LAKH]
    elif "TOTTRDQTY" in df.columns and "CLOSE" in df.columns:
        df["_TURNOVER"] = df["TOTTRDQTY"] * df["CLOSE"] / 100000
        df = df[df["_TURNOVER"] >= PREFILTER_MIN_TURNOVER_LAKH]

    df = df.head(PREFILTER_MAX_CANDIDATES)
    print(f"[INFO] After pre-filter: {len(df)} candidates")

    # ── STEP 3: Symbol → instrument_key mapping ───────────────────────────
    try:
        upstox = UpstoxModule(token)
        inst_map = build_instrument_map(upstox, df["SYMBOL"].tolist() if "SYMBOL" in df.columns else [])
    except Exception as e:
        print(f"[WARN] Upstox instrument map failed: {e}")
        inst_map = {}

    if inst_map and "SYMBOL" in df.columns:
        df["INSTRUMENT_KEY"] = df["SYMBOL"].str.strip().str.upper().map(inst_map)
        df = df[df["INSTRUMENT_KEY"].notna()]
        print(f"[INFO] Instrument key matched: {len(df)} stocks")

    # ── STEP 4: History fetch ─────────────────────────────────────────────
    history_map = {}
    if "INSTRUMENT_KEY" in df.columns and not df["INSTRUMENT_KEY"].empty:
        fetcher = build_history_fetcher(token)
        keys = df["INSTRUMENT_KEY"].dropna().tolist()
        fetched = 0

        def prog(done, total):
            nonlocal fetched
            fetched = done

        history_map = fetcher.fetch_many(keys, progress_callback=prog)
        print(f"[INFO] History fetched for {sum(1 for v in history_map.values() if v is not None)}/{len(keys)} stocks")

    # ── STEP 5: Inject indicators ─────────────────────────────────────────
    df = inject_history_indicators(df, history_map)

    # ── STEP 6: Run all scanners ──────────────────────────────────────────
    scanner_results = run_all_scanners(df)

    # ── STEP 7: ORB (sirf market hours mein) ─────────────────────────────
    orb_results = []
    if is_market_open() and "INSTRUMENT_KEY" in df.columns:
        try:
            orb_rows = []
            for _, row in df.iterrows():
                ikey = row.get("INSTRUMENT_KEY")
                if not ikey:
                    continue
                try:
                    resp = upstox.get_intraday(ikey, "1minute")
                    candles = resp.get("data", {}).get("candles", []) if isinstance(resp, dict) else []
                    if candles and len(candles) >= 15:
                        orb_candles = [c for c in candles
                                       if "09:15" <= c[0][11:16] <= "09:30"]
                        if orb_candles:
                            orb_high = max(c[2] for c in orb_candles)
                            orb_low  = min(c[3] for c in orb_candles)
                            curr_price = candles[-1][4]
                            orb_row = row.to_dict()
                            orb_row["ORB_HIGH"] = orb_high
                            orb_row["ORB_LOW"]  = orb_low
                            orb_row["CURRENT_PRICE"] = curr_price
                            orb_rows.append(orb_row)
                except Exception:
                    continue
            if orb_rows:
                orb_df = pd.DataFrame(orb_rows)
                orb_out = orb_scanner.top_candidates(orb_df, limit=25)
                orb_results = orb_out.to_dict("records") if not orb_out.empty else []
        except Exception as e:
            print(f"[WARN] ORB scan failed: {e}")

    scanner_results["orb"] = orb_results

    # ── STEP 8: AI ranking ────────────────────────────────────────────────
    try:
        all_stocks = []
        seen = set()
        for scan_name, rows in scanner_results.items():
            for row in rows:
                sym = row.get("SYMBOL", "")
                if sym and sym not in seen:
                    row["_scanner"] = scan_name
                    all_stocks.append(row)
                    seen.add(sym)
        if all_stocks:
            ranked = ai_ranker.rank(all_stocks[:30])
        else:
            ranked = []
    except Exception as e:
        print(f"[WARN] AI ranking failed: {e}")
        ranked = []

    elapsed = round(time.time() - t0, 1)
    print(f"[INFO] Scan complete in {elapsed}s")

    return jsonify({
        "success": True,
        "date": scan_date,
        "elapsed_seconds": elapsed,
        "total_scanned": len(bhav_df),
        "candidates": len(df),
        "results": scanner_results,
        "ai_ranked": ranked,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
