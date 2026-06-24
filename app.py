"""
Upstox CORS Proxy Server — Full NSE Scanner Edition
=====================================================
Naye features:
1. /instruments/nse  — Upstox ke instrument master se saare NSE_EQ stocks
                       fetch karta hai. Result cache hota hai raat 11 PM tak
                       (file roz 6 AM pe refresh hoti hai), taaki bar bar
                       download na karna pade.
2. /api/v2/market-quote/quotes — Full market quote (volume + OHLC + last_price
                                  sab ek saath), 500 instruments per call.
3. /api/v2/market-quote/ohlc   — Pehle wala OHLC endpoint (backward compat).
4. /health  /  — Health check aur info.
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
import gzip
import json
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

UPSTOX_BASE   = "https://api.upstox.com"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

# Simple in-memory cache for instrument list
# { "data": [...], "fetched_at": timestamp }
_instruments_cache = {}
CACHE_TTL = 18 * 3600  # 18 hours (file refreshes daily at 6 AM)


def forward_request(path):
    """Upstox ko request forward karta hai."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return jsonify({"status": "error", "message": "Authorization header missing"}), 401
    url = f"{UPSTOX_BASE}/{path}"
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, params=request.args, timeout=25)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "Upstox API timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": str(e)}), 502


# ── INSTRUMENT LIST ──────────────────────────────────────────────────────────

def fetch_nse_instruments():
    """Upstox complete instrument JSON (gzipped) download karke NSE_EQ filter karta hai."""
    global _instruments_cache
    now = time.time()

    # Cache valid hai?
    if _instruments_cache.get("data") and (now - _instruments_cache.get("fetched_at", 0)) < CACHE_TTL:
        return _instruments_cache["data"], None

    try:
        resp = requests.get(INSTRUMENTS_URL, timeout=60)
        if resp.status_code != 200:
            return None, f"Instrument file download failed: HTTP {resp.status_code}"
        raw = gzip.decompress(resp.content)
        all_instruments = json.loads(raw)
    except Exception as e:
        return None, f"Instrument file parse error: {str(e)}"

    # Sirf NSE Equity (segment=NSE_EQ, instrument_type=EQ) filter karo
    nse_eq = [
        {
            "symbol":       inst.get("trading_symbol") or inst.get("tradingsymbol") or "",
            "name":         inst.get("name", ""),
            "isin":         inst.get("isin", ""),
            "instrument_key": inst.get("instrument_key", ""),
            "lot_size":     inst.get("lot_size", 1),
        }
        for inst in all_instruments
        if inst.get("segment") == "NSE_EQ"
        and inst.get("instrument_type") in ("EQ", "BE", "SM")
        and inst.get("trading_symbol") and "|" not in inst.get("trading_symbol", "")
    ]

    _instruments_cache = {"data": nse_eq, "fetched_at": now}
    return nse_eq, None


@app.route("/instruments/nse", methods=["GET"])
def instruments_nse():
    """
    Saare NSE equity stocks ki list return karta hai.
    Response: { "status": "success", "count": N, "data": [{symbol, name, isin, instrument_key}...] }
    """
    data, err = fetch_nse_instruments()
    if err:
        return jsonify({"status": "error", "message": err}), 500
    return jsonify({"status": "success", "count": len(data), "data": data})


# ── MARKET QUOTE ROUTES ───────────────────────────────────────────────────────

@app.route("/api/v2/market-quote/ohlc", methods=["GET"])
def ohlc():
    return forward_request("v2/market-quote/ohlc")


@app.route("/api/v2/market-quote/ltp", methods=["GET"])
def ltp():
    return forward_request("v2/market-quote/ltp")


@app.route("/api/v2/market-quote/quotes", methods=["GET"])
def full_quotes():
    """
    Full market quote — volume, OHLC, last_price, circuit limits sab ek saath.
    500 instruments per call.
    """
    return forward_request("v2/market-quote/quotes")


@app.route("/api/v2/historical-candle/intraday/<path:instrument_key>/<interval>", methods=["GET"])
def intraday_candle(instrument_key, interval):
    return forward_request(f"v2/historical-candle/intraday/{instrument_key}/{interval}")


# ── HEALTH / INFO ────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    cached = len(_instruments_cache.get("data") or [])
    return jsonify({
        "status": "ok",
        "message": "Upstox CORS Proxy is running",
        "instruments_cached": cached,
        "usage": "GET /instruments/nse for all NSE stocks | GET /api/v2/market-quote/quotes for live quotes"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
        
