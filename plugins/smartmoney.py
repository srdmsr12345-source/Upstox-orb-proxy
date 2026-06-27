import pandas as pd

from config import (
    SMART_VOLUME_RATIO,
    MIN_DELIVERY_PERCENT
)


class SmartMoneyScanner:

    def __init__(self):
        pass


    def scan(self, df):

        df = df.copy()

        df.columns = df.columns.str.strip()

        volume_col = None
        delivery_col = None

        for col in df.columns:

            name = col.upper()

            if "TOTTRDQTY" in name:
                volume_col = col

            if "DELIV" in name:
                delivery_col = col

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

        if delivery_col is not None:

            df["DELIVERY_PERCENT"] = df[delivery_col]

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

        score = 0

        score += (

            (df["VOLUME_RATIO"] >= 2.5)

            .astype(int)

            * 40

        )

        score += (

            (df["DELIVERY_PERCENT"] >= 60)

            .astype(int)

            * 35

        )

        score += (

            (df["CLOSE"] > df["OPEN"])

            .astype(int)

            * 25

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
