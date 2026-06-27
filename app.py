from flask import Flask
from flask import render_template
from flask import request

from modules.upstox import UpstoxAPI
from modules.nse import nse
from modules.scanner import scanner
from modules.ai import ai_ranker

from config import ACCESS_TOKEN


app = Flask(__name__)


upstox = UpstoxAPI(
    ACCESS_TOKEN
)


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.route("/scan", methods=["POST"])
def scan():

    scan_type = request.form.get(
        "scan_type",
        "bottom"
    )

    date = request.form.get(
        "date"
    )

    merged = nse.merge_bhav_delivery()

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

    return {

        "summary": summary,

        "data": result.to_dict(
            orient="records"
        )

    }


if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
    @app.route("/health")
def health():

    return {

        "status": "ok",

        "service": "scanner"

    }


@app.route("/symbols")
def symbols():

    data = upstox.get_instruments()

    return {

        "count": len(data),

        "data": data

    }


@app.route("/ltp/<symbol>")
def ltp(symbol):

    return upstox.ltp_by_symbol(symbol)


@app.route("/ohlc/<symbol>")
def ohlc(symbol):

    return upstox.ohlc_by_symbol(symbol)


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

    return upstox.historical_by_symbol(

        symbol,

        interval,

        to_date,

        from_date

)
