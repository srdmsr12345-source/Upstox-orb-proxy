"""
Ultimate NSE Scanner
Global Configuration
Version 1.0
"""

# ==========================
# API URLS
# ==========================

UPSTOX_BASE_URL = "https://api.upstox.com"

UPSTOX_INSTRUMENT_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)

# ==========================
# MARKET TIMING
# ==========================

MARKET_OPEN = "09:15"

MARKET_CLOSE = "15:30"

AUTO_REFRESH_SECONDS = 60

# ==========================
# CACHE
# ==========================

CACHE_FOLDER = "data/cache"

CACHE_HOURS = 18

# ==========================
# NSE DATA
# ==========================

BHAVCOPY_FOLDER = "data/bhavcopy"

DELIVERY_FOLDER = "data/delivery"

# ==========================
# BOTTOM FISHING
# ==========================

BOTTOM_LOOKBACK_DAYS = 120

BOTTOM_DISTANCE_PERCENT = 25

MIN_VOLUME_RATIO = 2.0

MIN_DELIVERY_PERCENT = 45

RSI_MIN = 40

RSI_MAX = 60

EMA_FAST = 20

EMA_SLOW = 50

# ==========================
# STAGE-2
# ==========================

STAGE2_MIN_PRICE = 50

STAGE2_MIN_VOLUME_RATIO = 1.8

# ==========================
# SMART MONEY
# ==========================

ACCUMULATION_DAYS = 10

SMART_VOLUME_RATIO = 2.5

# ==========================
# AI SCORE
# ==========================

AI_WEIGHT_BOTTOM = 30

AI_WEIGHT_SMART = 20

AI_WEIGHT_VOLUME = 15

AI_WEIGHT_STAGE2 = 15

AI_WEIGHT_RS = 10

AI_WEIGHT_DELIVERY = 5

AI_WEIGHT_UPPER = 5

# ==========================
# FILTERS
# ==========================

MIN_MARKET_CAP_CR = 1000

MAX_RESULTS = 20

# ==========================
# LOGGING
# ==========================

LOG_LEVEL = "INFO"
