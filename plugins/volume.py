import pandas as pd

from config import MIN_VOLUME_RATIO


class VolumeScanner:
    """
    Volume Spike: aaj ka volume real 20-day average se kitna zyada hai.
    AVG_VOL_20 column history fetch se aata hai (modules/history.py) -
    pehle yeh wrongly single-day data par rolling() se calculate hota
    tha, jo galat (NaN/same-value) results deta tha.
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
        
