import pandas as pd

from config import MIN_VOLUME_RATIO


class VolumeScanner:

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
            .rolling(20, min_periods=1)
            .mean()
        )

        df["VOLUME_RATIO"] = (
            df[volume_col]
            / df["AVG_VOLUME"]
        )

        result = df[
            df["VOLUME_RATIO"] >= MIN_VOLUME_RATIO
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = (
            ((df["VOLUME_RATIO"] >= 2).astype(int) * 40)
            + ((df["VOLUME_RATIO"] >= 3).astype(int) * 30)
            + ((df["CLOSE"] > df["OPEN"]).astype(int) * 30)
        )

        df["VOLUME_SCORE"] = score

        return df

    def top_candidates(self, df, limit=20):

        df = self.scan(df)

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "VOLUME_SCORE",
            ascending=False
        )

        return df.head(limit)


volume_scanner = VolumeScanner()
