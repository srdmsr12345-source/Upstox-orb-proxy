from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import requests
import gzip
import json
import time

app = Flask(name)
CORS(app, resources={r"/": {"origins": ""}})

UPSTOX_BASE = "https://api.upstox.com"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

_instruments_cache = {}
CACHE_TTL = 18 * 3600

def forward_request(path):

auth_header = request.headers.get("Authorization", "")

if not auth_header:
    return jsonify({
        "status": "error",
        "message": "Authorization header missing"
    }), 401

url = f"{UPSTOX_BASE}/{path}"

headers = {
    "Authorization": auth_header,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

try:

    if request.method == "POST":
        resp = requests.post(
            url,
            headers=headers,
            json=request.get_json(silent=True),
            timeout=30
        )
    else:
        resp = requests.get(
            url,
            headers=headers,
            params=request.args,
            timeout=30
        )

    return Response(
        resp.content,
        status=resp.status_code,
        content_type=resp.headers.get(
            "Content-Type",
            "application/json"
        )
    )

except requests.exceptions.Timeout:
    return jsonify({
        "status": "error",
        "message": "Upstox API timeout"
    }), 504

except Exception as e:
    return jsonify({
        "status": "error",
        "message": str(e)
    }), 500

def fetch_nse_instruments():

global _instruments_cache

now = time.time()

if (
    _instruments_cache.get("data")
    and (now - _instruments_cache.get("fetched_at", 0)) < CACHE_TTL
):
    return _instruments_cache["data"], None

try:

    resp = requests.get(INSTRUMENTS_URL, timeout=60)

    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"

    raw = gzip.decompress(resp.content)
    all_instruments = json.loads(raw)

except Exception as e:
    return None, str(e)

nse_eq = []

for inst in all_instruments:

    if (
        inst.get("segment") == "NSE_EQ"
        and inst.get("instrument_type") in ("EQ", "BE", "SM")
    ):

        symbol = (
            inst.get("trading_symbol")
            or inst.get("tradingsymbol")
            or ""
        )

        if "|" in symbol:
            continue

        nse_eq.append({
            "symbol": symbol,
            "name": inst.get("name", ""),
            "isin": inst.get("isin", ""),
            "instrument_key": inst.get("instrument_key", ""),
            "lot_size": inst.get("lot_size", 1)
        })

_instruments_cache = {
    "data": nse_eq,
    "fetched_at": now
}

return nse_eq, None

@app.route("/", methods=["GET"])
def frontend():
return send_from_directory(".", "index.html")

@app.route("/api/info", methods=["GET"])
def api_info():

cached = len(_instruments_cache.get("data") or [])

return jsonify({
    "status": "ok",
    "message": "Upstox Scanner Proxy Running",
    "instruments_cached": cached
})

@app.route("/health", methods=["GET"])
def health():
return jsonify({
"status": "healthy"
})

@app.route("/instruments/nse", methods=["GET"])
def instruments_nse():

data, err = fetch_nse_instruments()

if err:
    return jsonify({
        "status": "error",
        "message": err
    }), 500

return jsonify({
    "status": "success",
    "count": len(data),
    "data": data
})

@app.route("/scanner/universe", methods=["GET"])
def scanner_universe():

data, err = fetch_nse_instruments()

if err:
    return jsonify({
        "status": "error",
        "message": err
    }), 500

return jsonify({
    "status": "success",
    "count": len(data),
    "data": data
})

@app.route("/scanner/info", methods=["GET"])
def scanner_info():

return jsonify({
    "scanner": "enabled",
    "version": "2.0",
    "features": [
        "ORB",
        "Volume Build Up",
        "Bottom Fishing",
        "Momentum",
        "Stage 2",
        "Relative Strength"
    ]
})

@app.route("/api/v2/market-quote/ohlc", methods=["GET"])
def ohlc():
return forward_request("v2/market-quote/ohlc")

@app.route("/api/v2/market-quote/ltp", methods=["GET"])
def ltp():
return forward_request("v2/market-quote/ltp")

@app.route("/api/v2/market-quote/quotes", methods=["GET"])
def quotes():
return forward_request("v2/market-quote/quotes")

@app.route("/scanner/quotes", methods=["POST"])
def scanner_quotes():

auth_header = request.headers.get("Authorization", "")

if not auth_header:
    return jsonify({
        "status": "error",
        "message": "Authorization header missing"
    }), 401

payload = request.get_json(silent=True) or {}

instruments = payload.get("instruments", [])

if not instruments:
    return jsonify({
        "status": "error",
        "message": "No instruments supplied"
    }), 400

try:

    url = f"{UPSTOX_BASE}/v2/market-quote/quotes"

    headers = {
        "Authorization": auth_header,
        "Accept": "application/json"
    }

    params = {
        "instrument_key": ",".join(instruments)
    }

    resp = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    return Response(
        resp.content,
        status=resp.status_code,
        content_type="application/json"
    )

except Exception as e:
    return jsonify({
        "status": "error",
        "message": str(e)
    }), 500

@app.route(
"/api/v2/historical-candle/intraday/"path:instrument_key" (path:instrument_key)/<interval>",
methods=["GET"]
)
def intraday_candle(instrument_key, interval):

return forward_request(
    f"v2/historical-candle/intraday/{instrument_key}/{interval}"
)

if name == "main":
app.run(
host="0.0.0.0",
port=5000
)
