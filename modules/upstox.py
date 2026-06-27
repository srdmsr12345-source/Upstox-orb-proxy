import gzip
import json
import time
import requests

from modules.cache import cache

UPSTOX_BASE = "https://api.upstox.com"

INSTRUMENTS_URL = (
    "https://assets.upstox.com/"
    "market-quote/instruments/"
    "exchange/complete.json.gz"
)


class UpstoxAPI:

    def __init__(self, access_token):

        self.access_token = access_token

        self.session = requests.Session()

        self.session.headers.update({

            "Authorization": f"Bearer {access_token}",

            "Accept": "application/json",

            "Content-Type": "application/json"

        })


    def request_json(self, response):

        try:

            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:

            return {

                "status": "error",

                "message": str(e),

                "code": response.status_code

            }

        except Exception as e:

            return {

                "status": "error",

                "message": str(e)

            }


    def get(self, path, params=None):

        url = f"{UPSTOX_BASE}/{path}"

        r = self.session.get(

            url,

            params=params,

            timeout=30

        )

        return self.request_json(r)


    def post(self, path, payload=None):

        url = f"{UPSTOX_BASE}/{path}"

        r = self.session.post(

            url,

            json=payload,

            timeout=30

        )

        return self.request_json(r)


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

        return self.get(

            f"v2/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}"

        )


    def get_intraday(

        self,

        instrument_key,

        interval

    ):

        return self.get(

            f"v2/historical-candle/intraday/{instrument_key}/{interval}"

        )


    def get_instruments(self):

        cached = cache.get(

            "upstox_instruments",

            max_age=18 * 60 * 60

        )

        if cached is not None:

            return cached

        r = self.session.get(

            INSTRUMENTS_URL,

            timeout=120

        )

        r.raise_for_status()

        raw = gzip.decompress(

            r.content

        )

        data = json.loads(raw)

        instruments = []
