"""
History Module — Incremental Update
=====================================
Pehli baar: 90 days bulk fetch → GitHub store
Roz: Sirf aaj ka candle fetch → append to GitHub
Scan: GitHub se load → EMA/RSI calculate

Isse Upstox API pe minimal load padta hai.
"""

import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.datastore import (
    read_stock, write_stock, append_candle,
    read_meta, write_meta, list_stored_symbols
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

    # ── FETCH FROM UPSTOX ──────────────────────────────────────────────

    def _fetch_candles(self, instrument_key, days=HISTORY_DAYS):
        """Upstox se daily candles fetch karta hai."""
        to_date   = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"{UPSTOX_BASE}/v2/historical-candle/"
               f"{instrument_key}/day/{to_date}/{from_date}")
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            time.sleep(0.05)  # Rate limit protection
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get("status") != "success":
                return None
            candles = data.get("data", {}).get("candles", [])
            if not candles:
                return None
            # Ascending order (purana → naya)
            candles = sorted(candles, key=lambda c: c[0])
            return [
                {
                    "date":   c[0][:10],  # YYYY-MM-DD
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

    # ── BULK INIT (Pehli Baar) ─────────────────────────────────────────

    def bulk_init(self, stocks, exchange="NSE", progress_cb=None):
        """
        Pehli baar: saare stocks ka 90-day history fetch karke
        GitHub pe store karta hai. Ek baar karo, phir daily updates.

        stocks: list of {"symbol": "RELIANCE", "instrument_key": "NSE_EQ|..."}
        """
        already_stored = set(list_stored_symbols(exchange))
        to_fetch = [s for s in stocks
                    if s["symbol"] not in already_stored]

        print(f"[INFO] bulk_init: {len(already_stored)} already stored, "
              f"{len(to_fetch)} to fetch")

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
                    progress_cb(done, total,
                                f"Init: {sym} {'✓' if ok else '✗'}")

        # Meta update
        meta = read_meta()
        meta["last_bulk_init"] = datetime.now().strftime("%Y-%m-%d")
        meta["total_symbols"]  = len(already_stored) + done
        write_meta(meta)
        return done

    # ── DAILY UPDATE (Roz) ─────────────────────────────────────────────

    def daily_update(self, stocks, exchange="NSE", progress_cb=None):
        """
        Roz chalao: sirf aaj ka 1 candle fetch karo aur GitHub pe append.
        2000 stocks × 1 call = bahut fast (2-3 minutes).
        """
        today = datetime.now().strftime("%Y-%m-%d")
        meta  = read_meta()

        if meta.get("last_daily_update") == today:
            print(f"[INFO] Already updated today ({today}), skip")
            return 0

        done = 0
        total = len(stocks)

        def update_one(stock):
            # Sirf aaj ka candle chahiye — last 5 days fetch karo
            # (weekend/holiday ke liye safety margin)
            candles = self._fetch_candles(stock["instrument_key"], days=5)
            if not candles:
                return False
            latest = candles[-1]  # Most recent candle
            if latest["date"] == today:
                return append_candle(exchange, stock["symbol"], latest)
            return False

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(update_one, s): s for s in stocks}
            for future in as_completed(futures):
                ok = future.result()
                done += 1
                if progress_cb and done % 50 == 0:
                    progress_cb(done, total, f"Daily update: {done}/{total}")

        meta["last_daily_update"] = today
        write_meta(meta)
        return done

    # ── COMPUTE INDICATORS ─────────────────────────────────────────────

    @staticmethod
    def compute_indicators(exchange, symbol):
        """
        GitHub se history load karke EMA20/EMA50/RSI14/AVG_VOL_20 calculate.
        Returns: dict of indicators ya None
        """
        candles = read_stock(exchange, symbol)
        if not candles or len(candles) < 5:
            return None

        df = pd.DataFrame(candles)
        df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
        df["low"]    = pd.to_numeric(df["low"],    errors="coerce")

        # EMA
        df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

        # RSI 14
        delta = df["close"].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        df["RSI14"] = 100 - (100 / (1 + rs))

        # Average Volume (20 day)
        df["AVG_VOL_20"] = df["volume"].rolling(20).mean()

        # 120-day low
        low_120 = df["low"].min() if len(df) >= 20 else df["low"].min()

        # 20-day ago close
        close_20d = (df["close"].iloc[-21]
                     if len(df) >= 21 else df["close"].iloc[0])

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
