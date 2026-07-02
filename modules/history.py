"""
History Module
===============
Pehle wala bug yeh tha ki EMA/RSI/Stage2/ORB/SmartMoney scanners ek
single-day bhav-copy (jisme har stock ka sirf EK row hota hai) par
.rolling(20) aur .ewm() jaisi time-series calculations laga rahe the -
yeh silently galat (ya hamesha NaN/same-value) results deta hai, kyunki
rolling window ka matlab hi nahi banta jab har "group" mein sirf 1 row ho.

Yeh module Upstox Historical Candle API se HAR stock ka asli 60-din ka
daily OHLCV data fetch karta hai, aur usi history se EMA20/EMA50/RSI14/
20-day-avg-volume sahi tarike se calculate karta hai - phir result ko
bhav-copy ke single-day row ke saath merge kar dete hain taaki scanners
ko sahi numbers milein.

Performance ke liye: saare ~2000 stocks ke liye history fetch karna bahut
slow/risky hai (rate limits + 2000 sequential calls). Isliye app.py mein
pehle bhav-copy se basic filter (price/volume) laga ke list chhoti karte
hain (~150-400 stocks), phir unhi ke liye yeh module history fetch karta
hai, parallel threads ke saath taaki time kam lage.
"""

import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.cache import cache
from modules.utils import ema, rsi, sma

UPSTOX_BASE = "https://api.upstox.com"

# Kitne dino ka history chahiye - EMA50 ke liye kam se kam 50+ trading
# din chahiye taaki EMA stabilize ho jaye, isliye 90 calendar din maangte
# hain (~60-65 trading din milte hain weekends/holidays minus karke).
HISTORY_DAYS = 90

# Ek saath kitne parallel requests bhejne hain - zyada se rate limit lag
# sakta hai, kam se scan bahut slow ho jayega. 8 reasonable balance hai.
MAX_WORKERS = 8

# Har request ke beech chhota gap (seconds) - Upstox rate limit se bachne
# ke liye. Upstox free tier ~25 req/sec allow karta hai per user.
REQUEST_DELAY = 0.05


class HistoryFetcher:

    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def _date_range(self):
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
        return to_date, from_date

    def fetch_one(self, instrument_key):
        """Single stock ke liye daily candles fetch karta hai (cached)."""

        cache_key = f"hist_{instrument_key.replace('|', '_').replace(':', '_')}"
        cached = cache.get(cache_key, max_age=6 * 3600)  # 6 hour cache
        if cached is not None:
            return instrument_key, cached

        to_date, from_date = self._date_range()
        url = f"{UPSTOX_BASE}/v2/historical-candle/{instrument_key}/day/{to_date}/{from_date}"

        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            time.sleep(REQUEST_DELAY)

            if r.status_code != 200:
                return instrument_key, None

            data = r.json()
            if data.get("status") != "success":
                return instrument_key, None

            candles = data.get("data", {}).get("candles", [])
            if not candles:
                return instrument_key, None

            # Candles aate hain latest-first, hum ascending (purana->naya) order
            # chahte hain taaki rolling/ewm calculations sahi direction mein chalein.
            candles = sorted(candles, key=lambda c: c[0])

            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "oi"
            ])

            cache.save(cache_key, df.to_dict("records"))
            return instrument_key, df.to_dict("records")

        except Exception:
            return instrument_key, None

    def fetch_many(self, instrument_keys, progress_callback=None):
        """
        Multiple stocks ke liye parallel mein history fetch karta hai.
        Returns: { instrument_key: DataFrame or None }
        """
        results = {}
        total = len(instrument_keys)
        done = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self.fetch_one, key): key
                for key in instrument_keys
            }

            for future in as_completed(futures):
                key, records = future.result()
                if records is not None:
                    results[key] = pd.DataFrame(records)
                else:
                    results[key] = None

                done += 1
                if progress_callback:
                    progress_callback(done, total)

        return results

    @staticmethod
    def compute_indicators(history_df):
        """
        Ek stock ke historical DataFrame se EMA20, EMA50, RSI14, aur
        20-day average volume calculate karta hai - sirf AAKHRI (latest)
        din ki values return karta hai, kyunki scanner ko sirf "abhi"
        ke indicator values chahiye, poori series nahi.
        """
        if history_df is None or history_df.empty or len(history_df) < 5:
            return None

        df = history_df.copy()
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        df["EMA20"] = ema(df["close"], 20)
        df["EMA50"] = ema(df["close"], 50)
        df["RSI14"] = rsi(df["close"], 14)
        df["AVG_VOL_20"] = sma(df["volume"], 20)

        last = df.iloc[-1]

        return {
            "EMA20": float(last["EMA20"]) if pd.notna(last["EMA20"]) else None,
            "EMA50": float(last["EMA50"]) if pd.notna(last["EMA50"]) else None,
            "RSI14": float(last["RSI14"]) if pd.notna(last["RSI14"]) else None,
            "AVG_VOL_20": float(last["AVG_VOL_20"]) if pd.notna(last["AVG_VOL_20"]) else None,
            "HISTORY_DAYS_AVAILABLE": len(df),
        }


def build_history_fetcher(access_token):
    return HistoryFetcher(access_token)
