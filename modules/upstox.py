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
