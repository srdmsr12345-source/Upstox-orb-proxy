"""
GitHub Data Store Module
=========================
Historical OHLCV data ko GitHub ke 'data' branch mein store karta hai.

Architecture:
- har stock ka data ek alag JSON file mein: data/history/NSE/RELIANCE.json
- meta.json mein last update info
- GitHub REST API se read/write (no git commands needed)

Incremental Update Logic:
1. Pehli baar: 90 days history fetch karo, GitHub pe save karo
2. Roz: sirf aaj ka candle fetch karo, existing data mein append karo
3. Scan: GitHub se load karo, EMA/RSI calculate karo
"""

import os
import json
import base64
import time
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "srdmsr12345-source/Upstox-orb-proxy")
GITHUB_BRANCH = os.getenv("GITHUB_DATA_BRANCH", "data")
GITHUB_API   = "https://api.github.com"

# In-memory cache to avoid repeated GitHub API calls within same scan
_memory_cache = {}


def _headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


def _file_path(exchange, symbol):
    """GitHub mein file path banata hai."""
    return f"data/history/{exchange}/{symbol}.json"


def read_stock(exchange, symbol):
    """
    GitHub se ek stock ki history padhta hai.
    Returns: list of candle dicts, ya [] agar nahi mili
    """
    cache_key = f"{exchange}_{symbol}"
    if cache_key in _memory_cache:
        return _memory_cache[cache_key]

    path = _file_path(exchange, symbol)
    url  = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"

    try:
        r = requests.get(url, headers=_headers(),
                        params={"ref": GITHUB_BRANCH}, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        data = json.loads(content)
        _memory_cache[cache_key] = data
        return data
    except Exception as e:
        print(f"[WARN] read_stock {exchange}/{symbol}: {e}")
        return []


def write_stock(exchange, symbol, candles):
    """
    GitHub pe ek stock ki history likhta hai (create ya update).
    candles: list of dicts with keys: date, open, high, low, close, volume
    """
    path    = _file_path(exchange, symbol)
    url     = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
    content = base64.b64encode(
        json.dumps(candles, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")

    # Existing file ka SHA chahiye update ke liye (409 Conflict avoid karne ke liye)
    # GitHub API response mein file ka SHA root level pe hota hai
    sha = None
    try:
        r = requests.get(url, headers=_headers(),
                        params={"ref": GITHUB_BRANCH}, timeout=10)
        if r.status_code == 200:
            resp_json = r.json()
            # SHA file object ke root mein hota hai (not inside content)
            sha = resp_json.get("sha")
    except Exception:
        pass

    payload = {
        "message": f"update {exchange}/{symbol} {datetime.now().strftime('%Y-%m-%d')}",
        "content": content,
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, headers=_headers(),
                        json=payload, timeout=20)
        r.raise_for_status()
        # Cache update
        _memory_cache[f"{exchange}_{symbol}"] = candles
        return True
    except Exception as e:
        print(f"[ERROR] write_stock {exchange}/{symbol}: {e}")
        return False


def append_candle(exchange, symbol, new_candle):
    """
    Existing history mein ek naya candle append karta hai.
    Duplicate dates automatically skip hote hain.
    """
    existing = read_stock(exchange, symbol)
    existing_dates = {c["date"] for c in existing}

    if new_candle["date"] in existing_dates:
        return True  # Already exists, skip

    existing.append(new_candle)
    # Sirf last 200 candles rakhte hain (EMA50 ke liye 50+ enough hai)
    existing = sorted(existing, key=lambda c: c["date"])[-200:]
    return write_stock(exchange, symbol, existing)


def read_meta():
    """meta.json padhta hai — last update info."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/data/meta.json"
    try:
        r = requests.get(url, headers=_headers(),
                        params={"ref": GITHUB_BRANCH}, timeout=10)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        return json.loads(content)
    except Exception:
        return {}


def write_meta(meta_dict):
    """meta.json update karta hai."""
    url     = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/data/meta.json"
    content = base64.b64encode(
        json.dumps(meta_dict, indent=2, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")

    sha = None
    try:
        r = requests.get(url, headers=_headers(),
                        params={"ref": GITHUB_BRANCH}, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass

    payload = {
        "message": f"meta update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": content,
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(url, headers=_headers(),
                        json=payload, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] write_meta: {e}")
        return False


def list_stored_symbols(exchange="NSE"):
    """GitHub pe jo symbols stored hain unki list."""
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/data/history/{exchange}"
    try:
        r = requests.get(url, headers=_headers(),
                        params={"ref": GITHUB_BRANCH}, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        files = r.json()
        return [f["name"].replace(".json", "") for f in files
                if f["name"].endswith(".json")]
    except Exception as e:
        print(f"[WARN] list_stored_symbols: {e}")
        return []


def clear_memory_cache():
    """Scan ke baad memory cache clear karo."""
    global _memory_cache
    _memory_cache = {}
