"""
Ultimate NSE Scanner
Global Configuration
Production Version 2.0
"""

import os

# ==========================
# PROJECT
# ==========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")

CACHE_FOLDER = os.path.join(DATA_DIR, "cache")

BHAVCOPY_FOLDER = os.path.join(DATA_DIR, "bhavcopy")

DELIVERY_FOLDER = os.path.join(DATA_DIR, "delivery")

LOG_FOLDER = os.path.join(DATA_DIR, "logs")

# ==========================
# AUTO CREATE FOLDERS
# ==========================

for folder in [

    DATA_DIR,

    CACHE_FOLDER,

    BHAVCOPY_FOLDER,

    DELIVERY_FOLDER,

    LOG_FOLDER

]:

    os.makedirs(folder, exist_ok=True)

# ==========================
# API
# ==========================

UPSTOX_BASE_URL = "https://api.upstox.com"

UPSTOX_INSTRUMENT_URL = (
    "https://assets.upstox.com/"
    "market-quote/instruments/"
    "exchange/complete.json.gz"
)

ACCESS_TOKEN = os.getenv(
    "UPSTOX_ACCESS_TOKEN",
    ""
)

# ==========================
# MARKET
# ==========================

MARKET_OPEN = "09:15"

MARKET_CLOSE = "15:30"

AUTO_REFRESH_SECONDS = 60

# ==========================
# CACHE
# ==========================

CACHE_HOURS = 18

CACHE_SECONDS = CACHE_HOURS * 3600

# ==========================
# NSE
# ==========================

BOTTOM_LOOKBACK_DAYS = 120

BOTTOM_DISTANCE_PERCENT = 25

MIN_VOLUME_RATIO = 2.0

MIN_DELIVERY_PERCENT = 45

# ==========================
# EMA
# ==========================

EMA_FAST = 20

EMA_SLOW = 50

# ==========================
# RSI
# ==========================

RSI_PERIOD = 14

RSI_MIN = 40

RSI_MAX = 60

# ==========================
# STAGE 2
# ==========================

STAGE2_MIN_PRICE = 50

STAGE2_MIN_VOLUME_RATIO = 1.8

# ==========================
# SMART MONEY
# ==========================

ACCUMULATION_DAYS = 10

SMART_VOLUME_RATIO = 2.5

# ==========================
# ORB
# ==========================

ORB_START_TIME = "09:15"

ORB_END_TIME = "09:30"

ORB_VOLUME_RATIO = 2.0

# ==========================
# AI
# ==========================

AI_WEIGHT_BOTTOM = 30

AI_WEIGHT_SMART = 20

AI_WEIGHT_VOLUME = 15

AI_WEIGHT_STAGE2 = 15

AI_WEIGHT_RS = 10

AI_WEIGHT_DELIVERY = 5

AI_WEIGHT_UPPER = 5

MAX_RESULTS = 20

# ==========================
# PRE-FILTER (before history fetch)
# ==========================
# Saare scanners ko EMA/RSI ke liye historical data chahiye, jo fetch
# karna slow hai 2000 stocks ke liye. Isliye bhav-copy ke single-day
# data se pehle ek halka filter laga dete hain - sirf wahi stocks
# history fetch karenge jo basic liquidity/price criteria pass karte hain.

PREFILTER_MIN_PRICE = 20

PREFILTER_MIN_TURNOVER_LAKH = 50  # min turnover in lakhs (close * volume)

PREFILTER_MAX_CANDIDATES = 400  # itne se zyada stocks history fetch nahi karenge

# ==========================
# FILTERS
# ==========================

MIN_MARKET_CAP_CR = 1000

# ==========================
# LOGGING
# ==========================

LOG_LEVEL = "INFO"

DEBUG = False
    
