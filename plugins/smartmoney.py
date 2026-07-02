import pandas as pd

from config import (
    SMART_VOLUME_RATIO,
    MIN_DELIVERY_PERCENT
)


class SmartMoneyScanner:
    """
    Smart Money: high volume + high delivery% + green candle - institutional
    accumulation ka signal. AVG_VOL_20 history se aata hai (real 20-day
    average), single-day data se fake calculate nahi hota ab.
    """

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()
        df.columns = df.columns.str.strip()

        if "TOTTRDQTY" not in df.columns or "AVG_VOL_20" not in df.columns:
            return pd.DataFrame()

        df["VOLUME_RATIO"] = (
            df["TOTTRDQTY"] / df["AVG_VOL_20"]
        ).replace([float("inf"), -float("inf")], 0).fillna(0)

        if "DELIV_PER" in df.columns:
            df["DELIVERY_PERCENT"] = df["DELIV_PER"]
        else:
            df["DELIVERY_PERCENT"] = 0

        result = df[
            (df["VOLUME_RATIO"] >= SMART_VOLUME_RATIO)
            &
            (df["DELIVERY_PERCENT"] >= MIN_DELIVERY_PERCENT)
            &
            (df["CLOSE"] > df["OPEN"])
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = (
            ((df["VOLUME_RATIO"] >= 2.5).astype(int) * 40)
            + ((df["DELIVERY_PERCENT"] >= 60).astype(int) * 35)
            + ((df["CLOSE"] > df["OPEN"]).astype(int) * 25)
        )

        df["SMART_SCORE"] = score

        return df

    def top_candidates(self, df, limit=20):

        df = self.scan(df)

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "SMART_SCORE",
            ascending=False
        )

        return df.head(limit)


smartmoney_scanner = SmartMoneyScanner()
            
