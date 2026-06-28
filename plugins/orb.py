import pandas as pd

from config import (
    ORB_START_TIME,
    ORB_END_TIME,
    ORB_VOLUME_RATIO
)


class ORBScanner:

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
            /
            df["AVG_VOLUME"]
        )

        result = df[
            (df["HIGH"] > df["OPEN"])
            &
            (df["CLOSE"] > df["HIGH"] * 0.995)
            &
            (df["VOLUME_RATIO"] >= ORB_VOLUME_RATIO)
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = 0

        score += (
            (df["VOLUME_RATIO"] >= 2)
            .astype(int)
            * 40
        )

        score += (
            (df["CLOSE"] > df["OPEN"])
            .astype(int)
            * 30
        )

        score += (
            (df["CLOSE"] >= df["HIGH"] * 0.995)
            .astype(int)
            * 30
        )

        df["ORB_SCORE"] = score

        return df

    def top_candidates(self, df, limit=20):

        df = self.scan(df)

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "ORB_SCORE",
            ascending=False
        )

        return df.head(limit)


orb_scanner = ORBScanner()
