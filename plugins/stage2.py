import pandas as pd

from config import (
    STAGE2_MIN_PRICE,
    STAGE2_MIN_VOLUME_RATIO
)


class Stage2Scanner:

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()
        df.columns = df.columns.str.strip()

        volume_col = None

        for col in df.columns:
            if "TOTTRDQTY" in col.upper():
                volume_col = col
                break

        if volume_col is None:
            return pd.DataFrame()

        df["AVG_VOLUME"] = (
            df[volume_col]
            .rolling(20)
            .mean()
        )

        df["VOLUME_RATIO"] = (
            df[volume_col]
            / df["AVG_VOLUME"]
        )

        df["EMA20"] = (
            df["CLOSE"]
            .ewm(span=20, adjust=False)
            .mean()
        )

        df["EMA50"] = (
            df["CLOSE"]
            .ewm(span=50, adjust=False)
            .mean()
        )

        result = df[
            (df["CLOSE"] >= STAGE2_MIN_PRICE)
            &
            (df["EMA20"] > df["EMA50"])
            &
            (df["VOLUME_RATIO"] >= STAGE2_MIN_VOLUME_RATIO)
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = 0

        score += (
            (df["EMA20"] > df["EMA50"]).astype(int) * 40
        )

        score += (
            (df["VOLUME_RATIO"] >= 2).astype(int) * 35
        )

        score += (
            (df["CLOSE"] > df["OPEN"]).astype(int) * 25
        )

        df["STAGE2_SCORE"] = score

        return df

    def top_candidates(self, df, limit=20):

        df = self.scan(df)

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "STAGE2_SCORE",
            ascending=False
        )

        return df.head(limit)


stage2_scanner = Stage2Scanner()
