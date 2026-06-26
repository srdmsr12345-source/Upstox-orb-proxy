from datetime import datetime
import math


def safe_divide(a, b):
    """Division by zero से बचने के लिए"""
    if b == 0:
        return 0
    return a / b


def percentage_change(old, new):
    """Percentage Change निकालता है"""
    if old == 0:
        return 0
    return ((new - old) / old) * 100


def volume_ratio(current_volume, average_volume):
    """Current Volume / Average Volume"""
    return safe_divide(current_volume, average_volume)


def round_price(price):
    """Price को 2 Decimal तक Round करता है"""
    return round(price, 2)


def format_number(value):
    """Large Numbers को Readable Format में बदलता है"""
    if value >= 10000000:
        return f"{value/10000000:.2f} Cr"
    elif value >= 100000:
        return f"{value/100000:.2f} L"
    return str(value)


def today():
    """आज की Date लौटाता है"""
    return datetime.now().strftime("%Y-%m-%d")
