import pandas as pd

from config import (
    STAGE2_MIN_PRICE,
    STAGE2_MIN_VOLUME_RATIO
)


class Stage2Scanner:
    """
    Stage 2 (Weinstein-style breakout): price EMA20 EMA50 ke upar trade
    kar raha hai (uptrend confirm), saath mein volume bhi zyada hai.
    EMA20/EMA50/AVG_VOL_20 ab REAL historical data se calculate hote hain
    (modules/history.py) - pehle yeh single-day data par .ewm()/.rolling()
    laga ke nikale jaate the, jo EMA20≈EMA50≈close hi deta tha (galat
    signal, har stock "uptrend" mein dikhta tha).
    """

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()
        df.columns = df.columns.str.strip()

        required = ["CLOSE", "OPEN", "TOTTRDQTY", "AVG_VOL_20", "EMA20", "EMA50"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return pd.DataFrame()

        df["VOLUME_RATIO"] = (
            df["TOTTRDQTY"] / df["AVG_VOL_20"]
        ).replace([float("inf"), -float("inf")], 0).fillna(0)

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

        score = (
            ((df["EMA20"] > df["EMA50"]).astype(int) * 40)
            + ((df["VOLUME_RATIO"] >= 2).astype(int) * 35)
            + ((df["CLOSE"] > df["OPEN"]).astype(int) * 25)
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
        
