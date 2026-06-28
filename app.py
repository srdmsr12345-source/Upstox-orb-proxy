from flask import Flask, render_template, request, jsonify
import traceback

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


@app.route("/test")
def test():
    return render_template("test.html")


@app.route("/api")
def api():
    return jsonify({
        "name": "AI Stock Scanner API",
        "version": "2.0.0",
        "status": "running"
    })


@app.route("/version")
def version():
    return jsonify({
        "application": "AI Stock Scanner",
        "version": "2.0.0"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


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

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e),

            "type": type(e).__name__

        }), 500


@app.route("/symbols")
def symbols():

    data = upstox.get
