from flask import Flask, render_template, request, jsonify

from modules.upstox import UpstoxAPI
from modules.nse import nse
from modules.scanner import scanner
from modules.ai import ai_ranker

from config import ACCESS_TOKEN

app = Flask(__name__)

upstox = UpstoxAPI(ACCESS_TOKEN)


@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# TEST PAGE
# -----------------------------
@app.route("/test")
def test():
    return render_template("test.html")


# -----------------------------
# API INFO
# -----------------------------
@app.route("/api")
def api():

    return jsonify({
        "name": "AI Stock Scanner API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": [
            "/",
            "/test",
            "/scan",
            "/health",
            "/symbols",
            "/ltp/<symbol>",
            "/ohlc/<symbol>",
            "/history/<symbol>",
            "/version"
        ]
    })


# -----------------------------
# VERSION
# -----------------------------
@app.route("/version")
def version():

    return jsonify({
        "application": "AI Stock Scanner",
        "version": "2.0.0"
    })


# -----------------------------
# HEALTH
# -----------------------------
@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "scanner"
    })


# -----------------------------
# SCAN
# -----------------------------
@app.route("/scan", methods=["POST"])
def scan():

    try:

        scan_type = request.form.get(
            "scan_type",
            "bottom"
        )

        requested_date = request.form.get(
            "date"
        )

        info = nse.merge_bhav_delivery(
            requested_date
        )

        merged = info["data"]

        actual_date = info["date"]

        result = scanner.run(
            scan_type,
            merged
        )

        result = ai_ranker.top(
            result
        )

        summary = ai_ranker.summary(
            result
        )

        return jsonify({

            "success": True,

            "scan_info": {

                "scanner": scan_type,

                "requested_date": requested_date,

                "actual_data_date": actual_date,

                "mode": "AUTO" if not requested_date else "MANUAL",

                "status": "SUCCESS"

            },

            "summary": summary,

            "rows": len(result),

            "data": result.to_dict(
                orient="records"
            )

        })

    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# -----------------------------
# SYMBOLS
# -----------------------------
@app.route("/symbols")
def symbols():

    data = upstox.get_instruments()

    return jsonify({

        "count": len(data),

        "data": data

    })


# -----------------------------
# LTP
# -----------------------------
@app.route("/ltp/<symbol>")
def ltp(symbol):

    return jsonify(

        upstox.ltp_by_symbol(symbol)

    )


# -----------------------------
# OHLC
# -----------------------------
@app.route("/ohlc/<symbol>")
def ohlc(symbol):

    return jsonify(

        upstox.ohlc_by_symbol(symbol)

    )


# -----------------------------
# HISTORY
# -----------------------------
@app.route("/history/<symbol>")
def history(symbol):

    interval = request.args.get(
        "interval",
        "day"
    )

    from_date = request.args.get(
        "from"
    )

    to_date = request.args.get(
        "to"
    )

    return jsonify(

        upstox.historical_by_symbol(

            symbol,

            interval,

            to_date,

            from_date

        )

    )


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
