"""
Ultimate NSE+BSE Scanner v2.0
================================
Routes:
  POST /scan          — daily scan (GitHub history + today's Upstox data)
  POST /init-history  — pehli baar bulk 90-day history fetch (ek baar chalao)
  POST /daily-update  — roz subah chalao, sirf aaj ka candle update
  GET  /status        — system status (kitne stocks stored, last update)
  GET  /health        — health check
"""

import os
import time
import traceback
from datetime import datetime, timedelta

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import PREFILTER_MIN_PRICE, PREFILTER_MIN_TURNOVER_LAKH
from modules.upstox import UpstoxAPI
from modules.history import build_history_manager
from modules.datastore import read_meta, list_stored_symbols, clear_memory_cache
from modules.ai import ai_ranker

from plugins.stage2 import stage2_scanner
from plugins.smartmoney import smartmoney_scanner
from plugins.bottom import bottom_scanner
from plugins.volume import volume_scanner
from plugins.momentum import momentum_scanner
from plugins.relativestrength import relative_strength_scanner
from plugins.orb import orb_scanner

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


# ── HELPERS ──────────────────────────────────────────────────────────────────

def get_token():
    auth = request.headers.get("Authorization", "")
    return auth[7:].strip() if auth.startswith("Bearer ") else ""


def is_market_open():
    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    if ist.weekday() >= 5:
        return False
    return (ist.replace(hour=9, minute=15) <=
            ist <= ist.replace(hour=15, minute=30))


def get_quality_stocks(upstox, exchange="NSE_EQ"):
    """
    Upstox instrument list se quality stocks filter karta hai.
    upstox.get_instruments() already NSE_EQ filtered list deta hai
    format: [{symbol, name, isin, instrument_key, exchange, ...}]
    """
    instruments = upstox.get_instruments()
    quality = []
    for inst in instruments:
        sym = (inst.get("symbol") or inst.get("trading_symbol") or
               inst.get("tradingsymbol") or "").strip().upper()
        key = inst.get("instrument_key", "")
        if sym and key:
            quality.append({
                "symbol": sym,
                "instrument_key": key,
                "exchange": "NSE"
            })

    print(f"[INFO] Quality stocks: {len(quality)}")
    return quality


def inject_indicators(df, exchange="NSE"):
    """
    DataFrame mein EMA20/EMA50/RSI14/AVG_VOL_20/LOW_120 inject karta hai
    GitHub stored history se.
    """
    from modules.history import HistoryManager

    indicators_map = {}
    for _, row in df.iterrows():
        sym = row.get("SYMBOL", "")
        if sym:
            ind = HistoryManager.compute_indicators(exchange, sym)
            if ind:
                indicators_map[sym] = ind

    df = df.copy()
    df["EMA20"]        = df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("EMA20"))
    df["EMA50"]        = df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("EMA50"))
    df["RSI14"]        = df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("RSI14"))
    df["AVG_VOL_20"]   = df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("AVG_VOL_20"))
    df["LOW_120"]      = df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("LOW_120"))
    df["CLOSE_20D_AGO"]= df["SYMBOL"].map(lambda s: indicators_map.get(s, {}).get("CLOSE_20D_AGO"))
    return df


def run_scanners(df):
    results = {}
    scanners = {
        "stage2":           lambda: stage2_scanner.top_candidates(df, 25),
        "smartmoney":       lambda: smartmoney_scanner.top_candidates(df, 25),
        "bottom":           lambda: bottom_scanner.top_candidates(df, 25),
        "volume":           lambda: volume_scanner.top_candidates(df, 25),
        "momentum":         lambda: momentum_scanner.top_candidates(df, 25),
        "relative_strength":lambda: relative_strength_scanner.top_candidates(df, None, 25),
    }
    for name, fn in scanners.items():
        try:
            r = fn()
            results[name] = r.to_dict("records") if not r.empty else []
        except Exception as e:
            results[name] = []
            print(f"[WARN] {name} failed: {e}")
    return results


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/init", methods=["GET"])
def init_page():
    """Init tool page serve karta hai."""
    from flask import render_template
    return render_template("init-tool.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Ultimate NSE+BSE Scanner v2.0",
        "routes": {
            "POST /init-history":  "Pehli baar 90-day history fetch (ek baar)",
            "POST /daily-update":  "Roz aaj ka candle update karo",
            "POST /scan":          "Scan karo (GitHub history + today's data)",
            "GET  /status":        "System status",
        }
    })


@app.route("/status", methods=["GET"])
def status():
    """System ka current status — kitne stocks stored hain."""
    meta = read_meta()
    nse_count = len(list_stored_symbols("NSE"))
    bse_count = len(list_stored_symbols("BSE"))
    return jsonify({
        "status": "ok",
        "nse_stored": nse_count,
        "bse_stored": bse_count,
        "total_stored": nse_count + bse_count,
        "last_bulk_init": meta.get("last_bulk_init", "never"),
        "last_daily_update": meta.get("last_daily_update", "never"),
    })


import threading
_init_status = {"running": False, "done": 0, "total": 0, "message": "idle"}

@app.route("/init-history", methods=["POST"])
def init_history():
    global _init_status
    if _init_status["running"]:
        return jsonify({"success": True, "status": _init_status,
                        "message": "Already running — /init-status se progress dekho"})

    token = get_token()
    if not token:
        return jsonify({"success": False, "error": "Token missing"}), 401

    def run_bg():
        global _init_status
        _init_status = {"running": True, "done": 0, "total": 0, "message": "Starting..."}
        try:
            upstox  = UpstoxAPI(token)
            manager = build_history_manager(token)
            stocks  = get_quality_stocks(upstox)
            _init_status["total"] = len(stocks)
            _init_status["message"] = f"{len(stocks)} stocks mili, history fetch ho rahi hai..."

            def prog(done, total, msg=""):
                _init_status["done"] = done
                _init_status["message"] = msg or f"{done}/{total} done"

            manager.bulk_init(stocks, exchange="NSE", progress_cb=prog)
            _init_status["running"] = False
            _init_status["message"] = "✓ Complete!"
        except Exception as e:
            _init_status["running"] = False
            _init_status["message"] = f"Error: {e}"

    threading.Thread(target=run_bg, daemon=True).start()
    return jsonify({"success": True,
                    "message": "Background mein shuru ho gaya! /init-status se progress dekho."})


@app.route("/init-status", methods=["GET"])
def init_status_route():
    return jsonify(_init_status)


@app.route("/daily-update", methods=["POST"])
def daily_update():
    """
    Roz subah chalao (9:30 AM ke baad) — sirf aaj ka candle update karo.
    2000 stocks × 1 candle = fast aur minimal API calls.
    """
    token = get_token()
    if not token:
        return jsonify({"success": False, "error": "Token missing"}), 401

    t0 = time.time()
    try:
        upstox  = UpstoxAPI(token)
        manager = build_history_manager(token)
        stocks  = get_quality_stocks(upstox)

        done = manager.daily_update(stocks, exchange="NSE")
        elapsed = round(time.time() - t0, 1)
        return jsonify({
            "success": True,
            "updated": done,
            "elapsed_seconds": elapsed
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/scan", methods=["POST"])
def scan():
    """
    Main scan endpoint:
    1. Upstox se aaj ka live OHLCV fetch (500 stocks per batch)
    2. GitHub se history load karke EMA/RSI inject
    3. Quality filter apply
    4. Saare scanners chalao
    5. AI ranking
    """
    token = get_token()
    if not token:
        return jsonify({"success": False, "error": "Token missing"}), 401

    t0 = time.time()
    clear_memory_cache()

    try:
        upstox = UpstoxAPI(token)
        stocks = get_quality_stocks(upstox)

        # ── TODAY'S LIVE DATA (Upstox bulk quotes) ──────────────────────
        quote_map = {}
        keys = [s["instrument_key"] for s in stocks]
        for i in range(0, len(keys), 500):
            batch = keys[i:i+500]
            try:
                resp = upstox.get_quotes(batch)
                if isinstance(resp, dict) and resp.get("status") == "success":
                    quote_map.update(resp.get("data", {}))
            except Exception as e:
                print(f"[WARN] quotes batch {i}: {e}")
            time.sleep(0.2)

        # ── BUILD DATAFRAME ─────────────────────────────────────────────
        rows = []
        for s in stocks:
            q = quote_map.get(s["instrument_key"]) or quote_map.get(
                next((k for k in quote_map if s["symbol"] in k), ""), None)
            if not q:
                continue

            ohlc    = q.get("ohlc") or {}
            close   = q.get("last_price") or ohlc.get("close") or 0
            prev    = q.get("prev_close") or ohlc.get("close") or close
            volume  = q.get("volume") or q.get("total_buy_quantity", 0)
            turnover = close * volume / 100000 if close and volume else 0

            # Basic quality filter
            if close < PREFILTER_MIN_PRICE:
                continue
            if turnover < PREFILTER_MIN_TURNOVER_LAKH:
                continue

            chg_pct = ((close - prev) / prev * 100) if prev else 0

            rows.append({
                "SYMBOL":      s["symbol"],
                "INSTRUMENT_KEY": s["instrument_key"],
                "CLOSE":       round(close, 2),
                "OPEN":        round(ohlc.get("open", close), 2),
                "HIGH":        round(ohlc.get("high", close), 2),
                "LOW":         round(ohlc.get("low",  close), 2),
                "PREVCLOSE":   round(prev, 2),
                "TOTTRDQTY":   int(volume),
                "TOTTRDVAL":   round(turnover, 2),
                "CHG_PCT":     round(chg_pct, 2),
                "DELIV_PER":   0,  # Not available from quotes endpoint
            })

        if not rows:
            return jsonify({
                "success": False,
                "error": "Koi bhi stock live data se nahi mila. Market band hai ya token expired hai."
            }), 500

        df = pd.DataFrame(rows)
        print(f"[INFO] Live data: {len(df)} stocks")

        # ── INJECT HISTORY INDICATORS ───────────────────────────────────
        df = inject_indicators(df, exchange="NSE")

        # ── RUN SCANNERS ────────────────────────────────────────────────
        scanner_results = run_scanners(df)

        # ── ORB (Market hours only) ─────────────────────────────────────
        orb_results = []
        if is_market_open():
            try:
                orb_rows = []
                for _, row in df.head(200).iterrows():
                    ikey = row.get("INSTRUMENT_KEY")
                    if not ikey:
                        continue
                    try:
                        resp = upstox.get_intraday(ikey, "1minute")
                        candles = (resp.get("data", {}).get("candles", [])
                                   if isinstance(resp, dict) else [])
                        if candles and len(candles) >= 15:
                            orb_c = [c for c in candles
                                     if "09:15" <= c[0][11:16] <= "09:30"]
                            if orb_c:
                                orb_row = row.to_dict()
                                orb_row["ORB_HIGH"] = max(c[2] for c in orb_c)
                                orb_row["ORB_LOW"]  = min(c[3] for c in orb_c)
                                orb_row["CURRENT_PRICE"] = candles[-1][4]
                                orb_rows.append(orb_row)
                    except Exception:
                        continue
                if orb_rows:
                    orb_df  = pd.DataFrame(orb_rows)
                    orb_out = orb_scanner.top_candidates(orb_df, 25)
                    orb_results = orb_out.to_dict("records") if not orb_out.empty else []
            except Exception as e:
                print(f"[WARN] ORB: {e}")
        scanner_results["orb"] = orb_results

        # ── AI RANKING ──────────────────────────────────────────────────
        try:
            all_stocks = []
            seen = set()
            for sname, srows in scanner_results.items():
                for row in srows:
                    sym = row.get("SYMBOL", "")
                    if sym and sym not in seen:
                        row["_scanner"] = sname
                        all_stocks.append(row)
                        seen.add(sym)
            ranked = ai_ranker.rank(all_stocks[:30]) if all_stocks else []
        except Exception as e:
            print(f"[WARN] AI ranking: {e}")
            ranked = []

        elapsed = round(time.time() - t0, 1)
        return jsonify({
            "success":       True,
            "date":          datetime.now().strftime("%d-%b-%Y"),
            "elapsed_seconds": elapsed,
            "total_scanned": len(stocks),
            "candidates":    len(df),
            "results":       scanner_results,
            "ai_ranked":     ranked,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
  
