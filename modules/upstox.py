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
