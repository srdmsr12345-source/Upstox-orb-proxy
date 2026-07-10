"""
Supabase Data Store Module
===========================
GitHub ki jagah Supabase PostgreSQL database use karta hai.
- Render restart pe data safe rehta hai (persistent)
- Fast queries (index se)
- No rate limits
- Free tier: 500MB (kaafi hai ~2000 stocks ke liye)
"""

import os
import time
import requests
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# In-memory cache to avoid repeated DB calls within same scan
_memory_cache = {}


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }


def _rest_url(table):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def read_stock(exchange, symbol):
    """Supabase se ek stock ki history padhta hai."""
    cache_key = f"{exchange}_{symbol}"
    if cache_key in _memory_cache:
        return _memory_cache[cache_key]

    url = _rest_url("stock_history")
    params = {
        "exchange": f"eq.{exchange}",
        "symbol": f"eq.{symbol}",
        "order": "date.asc",
        "limit": "200"
    }
    headers = {**_headers(), "Prefer": ""}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        candles = [
            {
                "date":   row["date"],
                "open":   float(row["open"] or 0),
                "high":   float(row["high"] or 0),
                "low":    float(row["low"] or 0),
                "close":  float(row["close"] or 0),
                "volume": int(row["volume"] or 0),
            }
            for row in data
        ]
        _memory_cache[cache_key] = candles
        return candles
    except Exception as e:
        print(f"[WARN] read_stock {exchange}/{symbol}: {e}")
        return []


def write_stock_bulk(exchange, symbol, candles):
    """
    Supabase mein bulk upsert karta hai (insert or update on conflict).
    Ek hi call mein saare candles insert ho jaate hain.
    """
    if not candles:
        return True

    url = _rest_url("stock_history")
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates"}

    rows = [
        {
            "exchange": exchange,
            "symbol":   symbol,
            "date":     c["date"],
            "open":     c["open"],
            "high":     c["high"],
            "low":      c["low"],
            "close":    c["close"],
            "volume":   c["volume"],
        }
        for c in candles
    ]

    try:
        r = requests.post(url, headers=headers, json=rows, timeout=30)
        if r.status_code in (200, 201, 204):
            _memory_cache[f"{exchange}_{symbol}"] = candles
            return True
        print(f"[WARN] write_stock_bulk {exchange}/{symbol}: {r.status_code} {r.text[:100]}")
        return False
    except Exception as e:
        print(f"[ERROR] write_stock_bulk {exchange}/{symbol}: {e}")
        return False


def append_candle(exchange, symbol, new_candle):
    """Ek naya candle append karta hai (upsert)."""
    url = _rest_url("stock_history")
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates"}
    row = {
        "exchange": exchange,
        "symbol":   symbol,
        "date":     new_candle["date"],
        "open":     new_candle["open"],
        "high":     new_candle["high"],
        "low":      new_candle["low"],
        "close":    new_candle["close"],
        "volume":   new_candle["volume"],
    }
    try:
        r = requests.post(url, headers=headers, json=[row], timeout=10)
        # Invalidate cache
        _memory_cache.pop(f"{exchange}_{symbol}", None)
        return r.status_code in (200, 201, 204)
    except Exception as e:
        print(f"[ERROR] append_candle {exchange}/{symbol}: {e}")
        return False


def read_meta():
    """Meta table se last update info padhta hai."""
    url = _rest_url("stock_history")
    headers = {**_headers(), "Prefer": ""}
    try:
        # Count stored symbols
        r = requests.get(
            url,
            headers=headers,
            params={"select": "symbol,exchange", "limit": "1"},
            timeout=5
        )
        # Simple count query
        count_r = requests.get(
            f"{SUPABASE_URL}/rest/v1/stock_history?select=count",
            headers={**headers, "Prefer": "count=exact"},
            timeout=5
        )
        count = 0
        if count_r.status_code == 200:
            ct = count_r.headers.get("Content-Range", "0")
            try:
                count = int(ct.split("/")[-1])
            except Exception:
                count = 0
        return {"total_rows": count}
    except Exception:
        return {}


def write_meta(meta_dict):
    """Meta info update — Supabase mein separate table nahi, skip."""
    pass


def list_stored_symbols(exchange="NSE"):
    """Supabase mein jo symbols stored hain unki list."""
    url = _rest_url("stock_history")
    headers = {**_headers(), "Prefer": ""}
    try:
        r = requests.get(
            url,
            headers=headers,
            params={
                "select": "symbol",
                "exchange": f"eq.{exchange}",
                "limit": "10000"
            },
            timeout=15
        )
        if r.status_code != 200:
            return []
        data = r.json()
        return list(set(row["symbol"] for row in data))
    except Exception as e:
        print(f"[WARN] list_stored_symbols: {e}")
        return []


def get_stored_count():
    """Total stored rows count."""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/stock_history",
            headers={**_headers(), "Prefer": "count=exact"},
            params={"select": "count", "limit": "1"},
            timeout=5
        )
        ct = r.headers.get("Content-Range", "0/0")
        return int(ct.split("/")[-1])
    except Exception:
        return 0


def clear_memory_cache():
    global _memory_cache
    _memory_cache = {}
