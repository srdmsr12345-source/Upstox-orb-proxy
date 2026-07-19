"""
History Module — Supabase Incremental Update
"""
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.datastore import (
    read_stock,
    write_stock_bulk,
    append_candle,
    read_meta,
    write_meta,
    list_stored_symbols
)

UPSTOX_BASE  = "https://api.upstox.com"
MAX_WORKERS  = 6
HISTORY_DAYS = 90


class HistoryManager:

    def __init__(self, access_token):
        self.token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def _fetch_candles(self, instrument_key, days=HISTORY_DAYS):
        to_date   = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"{UPSTOX_BASE}/v2/historical-candle/"
               f"{instrument_key}/day/{to_date}/{from_date}")
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            time.sleep(0.05)
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("status") != "success":
                return None
            candles = data.get("data", {}).get("candles", [])
            if not candles:
                return None
            candles = sorted(candles, key=lambda c: c[0])
            return [
                {
                    "date":   c[0][:10],
                    "open":   float(c[1]),
                    "high":   float(c[2]),
                    "low":    float(c[3]),
                    "close":  float(c[4]),
                    "volume": int(c[5]),
                }
                for c in candles
            ]
        except Exception as e:
            print(f"[WARN] fetch_candles {instrument_key}: {e}")
            return None

    def bulk_init(self, stocks, exchange="NSE", progress_cb=None):
        already_stored = set(list_stored_symbols(exchange))
        to_fetch = [s for s in stocks if s["symbol"] not in already_stored]
        print(f"[INFO] bulk_init: {len(already_stored)} already stored, {len(to_fetch)} to fetch")

        done = 0
        total = len(to_fetch)

        def fetch_and_store(stock):
            candles = self._fetch_candles(stock["instrument_key"])
            if candles:
                write_stock_bulk(exchange, stock["symbol"], candles)
                return stock["symbol"], True
            return stock["symbol"], False

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(fetch_and_store, s): s for s in to_fetch}
            for future in as_completed(futures):
                sym, ok = future.result()
                done += 1
                if progress_cb:
                    progress_cb(done, total, f"Init: {sym} {'ok' if ok else 'fail'}")

        return done

    def daily_update(self, stocks, exchange="NSE", progress_cb=None):
        today = datetime.now().strftime("%Y-%m-%d")
        done = 0

        def update_one(stock):
            candles = self._fetch_candles(stock["instrument_key"], days=5)
            if not candles:
                return False
            latest = candles[-1]
            if latest["date"] == today:
                return append_candle(exchange, stock["symbol"], latest)
            return False

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(update_one, s): s for s in stocks}
            for future in as_completed(futures):
                future.result()
                done += 1
                if progress_cb and done % 50 == 0:
                    progress_cb(done, len(stocks), f"Daily: {done}/{len(stocks)}")

        return done

    @staticmethod
    def compute_indicators(exchange, symbol):
        candles = read_stock(exchange, symbol)
        if not candles or len(candles) < 5:
            return None

        df = pd.DataFrame(candles)
        df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
        df["low"]    = pd.to_numeric(df["low"],    errors="coerce")

        df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

        delta = df["close"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        df["RSI14"] = 100 - (100 / (1 + rs))

        df["AVG_VOL_20"] = df["volume"].rolling(20).mean()

        low_120   = df["low"].min()
        close_20d = df["close"].iloc[-21] if len(df) >= 21 else df["close"].iloc[0]

        last = df.iloc[-1]
        return {
            "EMA20":        round(float(last["EMA20"]),  2) if pd.notna(last["EMA20"])  else None,
            "EMA50":        round(float(last["EMA50"]),  2) if pd.notna(last["EMA50"])  else None,
            "RSI14":        round(float(last["RSI14"]),  2) if pd.notna(last["RSI14"])  else None,
            "AVG_VOL_20":   round(float(last["AVG_VOL_20"]), 0) if pd.notna(last["AVG_VOL_20"]) else None,
            "LOW_120":      round(float(low_120), 2),
            "CLOSE_20D_AGO":round(float(close_20d), 2),
            "DAYS_STORED":  len(df),
        }


def build_history_manager(access_token):
    return HistoryManager(access_token)
            
