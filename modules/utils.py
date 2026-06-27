from datetime import datetime
import math


def safe_divide(a, b):

    if b == 0:

        return 0

    return a / b


def percentage_change(old, new):

    if old == 0:

        return 0

    return ((new - old) / old) * 100


def volume_ratio(current_volume, average_volume):

    return safe_divide(

        current_volume,

        average_volume

    )


def round_price(price):

    return round(price, 2)


def format_number(value):

    if value >= 10000000:

        return f"{value/10000000:.2f} Cr"

    if value >= 100000:

        return f"{value/100000:.2f} L"

    if value >= 1000:

        return f"{value/1000:.2f} K"

    return str(value)


def today():

    return datetime.now().strftime("%Y-%m-%d")


def ema(series, period):

    return series.ewm(

        span=period,

        adjust=False

    ).mean()


def sma(series, period):

    return series.rolling(

        period

    ).mean()


def highest(series, period):

    return series.rolling(

        period

    ).max()


def lowest(series, period):

    return series.rolling(

        period

    ).min()


def rsi(close, period=14):

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(

        alpha=1/period,

        adjust=False

    ).mean()

    avg_loss = loss.ewm(

        alpha=1/period,

        adjust=False

    ).mean()

    rs = safe_divide(

        avg_gain,

        avg_loss

    )

    return 100 - (100 / (1 + rs))


def atr(df, period=14):

    high = df["HIGH"]

    low = df["LOW"]

    close = df["CLOSE"]

    tr = (

        high - low

    ).combine(

        (high - close.shift()).abs(),

        max

    ).combine(

        (low - close.shift()).abs(),

        max

    )

    return tr.rolling(

        period

    ).mean()


def percent_from_low(price, low):

    return safe_divide(

        price - low,

        low

    ) * 100


def percent_from_high(price, high):

    return safe_divide(

        high - price,

        high

    ) * 100
