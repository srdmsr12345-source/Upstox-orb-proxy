import pandas as pd


class RelativeStrengthScanner:

    def __init__(self):
        pass

    def scan(self, stock_df, index_df):

        stock_df = stock_df.copy()
        index_df = index_df.copy()

        stock_df.columns = stock_df.columns.str.strip()
        index_df.columns = index_df.columns.str.strip()

        stock_return = (
            (stock_df["CLOSE"] - stock_df["CLOSE"].shift(20))
            / stock_df["CLOSE"].shift(20)
        ) * 100

        index_return = (
            (index_df["CLOSE"] - index_df["CLOSE"].shift(20))
            / index_df["CLOSE"].shift(20)
        ) * 100

        stock_df["RS"] = stock_return - index_return

        result = stock_df[
            stock_df["RS"] > 0
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = 0

        score += (
            (df["RS"] > 0).astype(int) * 40
        )

        score += (
            (df["RS"] > 5).astype(int) * 30
        )

        score += (
            (df["CLOSE"] > df["OPEN"]).astype(int) * 30
        )

        df["RS_SCORE"] = score

        return df

    def top_candidates(self, stock_df, index_df, limit=20):

        df = self.scan(
            stock_df,
            index_df
        )

        if df.empty:
            return df

        df = self.add_score(df)

        df = df.sort_values(
            "RS_SCORE",
            ascending=False
        )

        return df.head(limit)


relative_strength_scanner = RelativeStrengthScanner()
