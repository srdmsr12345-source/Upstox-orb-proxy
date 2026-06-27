import pandas as pd

from config import (
    BOTTOM_DISTANCE_PERCENT,
    MIN_VOLUME_RATIO,
    MIN_DELIVERY_PERCENT
)


class BottomFishingScanner:

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()

        df.columns = df.columns.str.strip()

        # Find today's low (replace with 120-day low later if history is available)
        df["LOW_120"] = df["LOW"]

        df["BOTTOM_DISTANCE"] = (
            (df["CLOSE"] - df["LOW_120"])
            / df["LOW_120"]
        ) * 100

        volume_col = None
        delivery_col = None

        for col in df.columns:

            name = col.upper()

            if "DELIV" in name:
                delivery_col = col

            if "TOTTRDQTY" in name:
                volume_col = col

        if volume_col is None:
            volume_col = "TOTTRDQTY"

        df["VOLUME_RATIO"] = (
            df[volume_col]
            / df[volume_col].rolling(20, min_periods=1).mean()
        )

        if delivery_col is not None:
            df["DELIVERY_PERCENT"] = df[delivery_col]
        else:
            df["DELIVERY_PERCENT"] = 0

        result = df[
            (df["BOTTOM_DISTANCE"] <= BOTTOM_DISTANCE_PERCENT)
            &
            (df["VOLUME_RATIO"] >= MIN_VOLUME_RATIO)
            &
            (df["DELIVERY_PERCENT"] >= MIN_DELIVERY_PERCENT)
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = (
            ((df["BOTTOM_DISTANCE"] <= 10).astype(int) * 30)
            + ((df["VOLUME_RATIO"] >= 3).astype(int) * 25)
            + ((df["DELIVERY_PERCENT"] >= 60).astype(int) * 20)
            + ((df["CLOSE"] > df["OPEN"]).astype(int) * 10)
            + ((df["CLOSE"] > df["LOW"]).astype(int) * 15)
        )

        df["BOTTOM_SCORE"] = score

        return df

    def top_candidates(self, df, limit=20):

        df = self.scan(df)

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "BOTTOM_SCORE",
            ascending=False
        )

        return df.head(limit)


bottom_scanner = BottomFishingScanner()
