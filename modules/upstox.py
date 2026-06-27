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
        for item in data:

            if item.get("segment") != "NSE_EQ":
                continue

            symbol = (
                item.get("trading_symbol")
                or item.get("tradingsymbol")
                or ""
            )

            if not symbol:
                continue

            instruments.append({

                "symbol": symbol,

                "name": item.get("name", ""),

                "isin": item.get("isin", ""),

                "instrument_key": item.get(
                    "instrument_key",
                    ""
                ),

                "exchange": item.get(
                    "exchange",
                    "NSE"
                ),

                "lot_size": item.get(
                    "lot_size",
                    1
                ),

                "tick_size": item.get(
                    "tick_size",
                    0.05
                )

            })

        cache.save(

            "upstox_instruments",

            instruments

        )

        return instruments


    def instrument_lookup(self):

        instruments = self.get_instruments()

        lookup = {}

        for item in instruments:

            lookup[item["symbol"]] = item

        return lookup


    def instrument_key(self, symbol):

        lookup = self.instrument_lookup()

        stock = lookup.get(symbol)

        if stock is None:

            return None

        return stock["instrument_key"]


    def ltp_by_symbol(self, symbol):

        key = self.instrument_key(symbol)

        if key is None:

            return None

        return self.get_ltp(key)


    def ohlc_by_symbol(self, symbol):

        key = self.instrument_key(symbol)

        if key is None:

            return None

        return self.get_ohlc(key)


    def historical_by_symbol(

        self,

        symbol,

        interval,

        to_date,

        from_date

    ):

        key = self.instrument_key(symbol)

        if key is None:

            return None

        return self.get_historical(

            key,

            interval,

            to_date,

            from_date

        )


    def intraday_by_symbol(

        self,

        symbol,

        interval

    ):

        key = self.instrument_key(symbol)

        if key is None:

            return None

        return self.get_intraday(

            key,

            interval

        )
