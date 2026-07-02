import pandas as pd

from config import ORB_VOLUME_RATIO


class ORBScanner:
    """
    True Opening Range Breakout: aaj 9:15-9:30 AM ke candle ka high todna
    chahiye, achhe volume ke saath. Yeh daily bhav-copy se possible NAHI
    hai (usme sirf ek single end-of-day row hota hai, intraday 9:15-9:30
    ka data hota hi nahi) - pehle wala code galti se "df['HIGH'] >
    df['OPEN']" jaisi proxy condition use kar raha tha jo ORB nahi hai,
    sirf "green day" check kar raha tha.

    Asal ORB ke liye yeh function ek alag DataFrame expect karta hai
    jisme app.py ne pehle se Upstox intraday candle API (1minute interval)
    se ORB_HIGH, ORB_LOW, aur CURRENT_PRICE columns nikal ke daale hon
    (dekhein app.py ke build_orb_dataframe function ko). Yeh sirf MARKET
    OPEN hone par hi meaningful results dega (live trading hours mein).
    """

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()
        df.columns = df.columns.str.strip()

        required = ["CURRENT_PRICE", "ORB_HIGH", "ORB_LOW", "TOTTRDQTY", "AVG_VOL_20"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            # ORB data nahi mila (market band hai, ya intraday fetch
            # fail hua) - khaali result, error nahi.
            return pd.DataFrame()

        df["VOLUME_RATIO"] = (
            df["TOTTRDQTY"] / df["AVG_VOL_20"]
        ).replace([float("inf"), -float("inf")], 0).fillna(0)

        df["BREAKOUT_PCT"] = (
            (df["CURRENT_PRICE"] - df["ORB_HIGH"]) / df["ORB_HIGH"]
        ) * 100

        result = df[
            (df["CURRENT_PRICE"] > df["ORB_HIGH"])
            &
            (df["VOLUME_RATIO"] >= ORB_VOLUME_RATIO)
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = (
            ((df["VOLUME_RATIO"] >= 2).astype(int) * 40)
            + ((df["BREAKOUT_PCT"] > 0).astype(int) * 30)
            + ((df["BREAKOUT_PCT"] <= 3).astype(int) * 30)  # too-extended breakout is riskier
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
        
