import requests
import time
import gzip
import json

UPSTOX_BASE = "https://api.upstox.com"

INSTRUMENTS_URL = (
    "https://assets.upstox.com/"
    "market-quote/instruments/"
    "exchange/complete.json.gz"
)

CACHE_TTL = 18 * 60 * 60

instrument_cache = {
    "updated": 0,
    "data": []
}


class UpstoxAPI:

    def __init__(self, access_token):

        self.access_token = access_token

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get(self, path, params=None):

        url = f"{UPSTOX_BASE}/{path}"

        r = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30
        )

        return r

    def post(self, path, payload=None):

        url = f"{UPSTOX_BASE}/{path}"

        r = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        return r
    def get_ltp(self, instrument_key):

        return self.get(
            "v2/market-quote/ltp",
            {
                "instrument_key": instrument_key
            }
        )

    def get_ohlc(self, instrument_key):

        return self.get(
            "v2/market-quote/ohlc",
            {
                "instrument_key": instrument_key
            }
        )

    def get_quotes(self, instrument_keys):

        if isinstance(instrument_keys, list):
            instrument_keys = ",".join(instrument_keys)

        return self.get(
            "v2/market-quote/quotes",
            {
                "instrument_key": instrument_keys
            }
        )

    def get_historical(
        self,
        instrument_key,
        interval,
        to_date,
        from_date
    ):

        path = (
            f"v2/historical-candle/"
            f"{instrument_key}/"
            f"{interval}/"
            f"{to_date}/"
            f"{from_date}"
        )

        return self.get(path)

    def get_intraday(
        self,
        instrument_key,
        interval
    ):

        path = (
            f"v2/historical-candle/intraday/"
            f"{instrument_key}/"
            f"{interval}"
        )

        return self.get(path)
    def get_instruments(self):

        global instrument_cache

        now = time.time()

        if (
            instrument_cache["data"]
            and
            now - instrument_cache["updated"] < CACHE_TTL
        ):
            return instrument_cache["data"]

        response = requests.get(
            INSTRUMENTS_URL,
            timeout=60
        )

        response.raise_for_status()

        raw = gzip.decompress(response.content)

        data = json.loads(raw)

        instruments = []

        for item in data:

            if item.get("segment") != "NSE_EQ":
                continue

            symbol = (
                item.get("trading_symbol")
                or
                item.get("tradingsymbol")
                or
                ""
            )

            if "|" in symbol:
                continue

            instruments.append({

                "symbol":
                    symbol,

                "name":
                    item.get("name", ""),

                "isin":
                    item.get("isin", ""),

                "instrument_key":
                    item.get(
                        "instrument_key",
                        ""
                    ),

                "lot_size":
                    item.get(
                        "lot_size",
                        1
                    )

            })

        instrument_cache["updated"] = now

        instrument_cache["data"] = instruments

        return instruments
