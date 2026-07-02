import pandas as pd

from config import RSI_MIN, RSI_MAX


class MomentumScanner:
    """
    Momentum: stock RSI ke healthy zone (40-80) mein hai aur price upar
    ja raha hai. RSI14 column real history se aata hai (modules/history.py).
    Pehle yeh file bilkul khaali thi - sirf comment tha, koi scanner nahi.
    """

    def __init__(self):
        pass

    def scan(self, df):
        df = df.copy()
        df.columns = df.columns.str.strip()

        required = ["CLOSE", "OPEN", "RSI14", "TOTTRDQTY", "AVG_VOL_20"]
        if any(c not in df.columns for c in required):
            return pd.DataFrame()

        df["VOLUME_RATIO"] = (
            df["TOTTRDQTY"] / df["AVG_VOL_20"]
        ).replace([float("inf"), -float("inf")], 0).fillna(0)

        result = df[
            (df["RSI14"] >= RSI_MIN)
            & (df["RSI14"] <= RSI_MAX + 20)
            & (df["CLOSE"] > df["OPEN"])
            & (df["VOLUME_RATIO"] >= 1.2)
        ]
        return result.reset_index(drop=True)

    def add_score(self, df):
        df = df.copy()
        df["MOMENTUM_SCORE"] = (
            ((df["RSI14"] >= 50) & (df["RSI14"] <= 70)).astype(int) * 40
            + (df["VOLUME_RATIO"] >= 1.5).astype(int) * 30
            + (df["CLOSE"] > df["OPEN"]).astype(int) * 30
        )
        return df

    def top_candidates(self, df, limit=20):
        df = self.scan(df)
        if df.empty:
            return df
        df = self.add_score(df)
        return df.sort_values("MOMENTUM_SCORE", ascending=False).head(limit)


momentum_scanner = MomentumScanner()
      
