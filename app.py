"""
Upstox CORS Proxy Server
=========================
Yeh chhota Flask server browser aur Upstox API ke beech proxy ka kaam karta hai.
Browser is server ko call karta hai, yeh server Upstox ko call karta hai
(server-to-server call mein CORS restriction nahi lagti), aur response
wapas browser ko CORS headers ke saath bhej deta hai.

Koi data store nahi hota - access token har request ke saath browser se
aata hai aur seedha Upstox ko forward ho jaata hai.
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
# Allow all origins on ALL routes (including /health and /) - yeh public proxy
# hai, koi sensitive data yahan store nahi hota. Pehle sirf /api/* par CORS
# tha jiski wajah se browser se /health fetch() CORS error deta tha (address
# bar se direct kholna kaam karta tha kyunki navigation requests CORS check
# nahi karte, lekin JS fetch() karta hai).
CORS(app, resources={r"/*": {"origins": "*"}})

UPSTOX_BASE = "https://api.upstox.com"


def forward_request(path):
    """Upstox ko request forward karta hai, original query params ke saath.
    Query params sirf yahan ek baar add hote hain (request.args se) -
    pehle yeh bug tha ki route handler bhi query string jodta tha aur
    yeh function bhi params= se jodta tha, jisse params duplicate ho
    jaate the (e.g. interval=1d,1d) aur Upstox 'Invalid interval' error deta tha.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return jsonify({"status": "error", "message": "Authorization header missing"}), 401

    url = f"{UPSTOX_BASE}/{path}"
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
    }

    try:
        resp = requests.get(url, headers=headers, params=request.args, timeout=20)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "Upstox API timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": str(e)}), 502


@app.route("/api/v2/market-quote/ohlc", methods=["GET"])
def ohlc():
    return forward_request("v2/market-quote/ohlc")


@app.route("/api/v2/market-quote/ltp", methods=["GET"])
def ltp():
    return forward_request("v2/market-quote/ltp")


@app.route("/api/v2/historical-candle/intraday/<path:instrument_key>/<interval>", methods=["GET"])
def intraday_candle(instrument_key, interval):
    return forward_request(f"v2/historical-candle/intraday/{instrument_key}/{interval}")


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Upstox CORS Proxy is running",
        "usage": "Point your scanner's API_BASE to this URL + /api"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
