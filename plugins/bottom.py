import pandas as pd

from config import (
    BOTTOM_DISTANCE_PERCENT,
    MIN_VOLUME_RATIO,
    MIN_DELIVERY_PERCENT
)


class BottomFishingScanner:
    """
    Bottom Fishing: stocks jo apne 120-day low ke kareeb hain lekin aaj
    high volume + high delivery% ke saath upar band hue (accumulation
    signal). Yeh scanner ab AVG_VOL_20 aur LOW_120 columns expect karta
    hai jo HISTORY se calculate hoke aate hain (modules/history.py se) -
    pehle yeh values galat tarike se single-day data par rolling() laga
    ke nikali jaati thi, jo hamesha NaN ya wahi single value deti thi.
    """

    def __init__(self):
        pass

    def scan(self, df):

        df = df.copy()
        df.columns = df.columns.str.strip()

        required = ["CLOSE", "OPEN", "LOW", "AVG_VOL_20", "LOW_120", "TOTTRDQTY"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            # History merge nahi hui hai - is scanner ko skip karte hain
            # khaali result ke saath, error throw nahi karte.
            return pd.DataFrame()

        df["BOTTOM_DISTANCE"] = (
            (df["CLOSE"] - df["LOW_120"])
            / df["LOW_120"]
        ) * 100

        df["VOLUME_RATIO"] = (
            df["TOTTRDQTY"] / df["AVG_VOL_20"]
        ).replace([float("inf"), -float("inf")], 0).fillna(0)

        if "DELIV_PER" in df.columns:
            df["DELIVERY_PERCENT"] = df["DELIV_PER"]
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
                 
