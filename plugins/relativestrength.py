import pandas as pd


class RelativeStrengthScanner:
    """
    Relative Strength: stock ka 20-din ka return vs index (NIFTY) ka
    20-din ka return - stock jo index se behtar perform kar raha hai.

    CLOSE_20D_AGO column real history se aata hai (modules/history.py),
    pehle yeh galti se single-day data par .shift(20) laga ke nikala
    jaata tha jo hamesha NaN deta (kyunki ek row ko 20 se shift karoge
    to result hamesha empty hota hai).
    """

    def __init__(self):
        pass

    def scan(self, stock_df, index_df):

        stock_df = stock_df.copy()

        stock_df.columns = stock_df.columns.str.strip()

        required = ["CLOSE", "CLOSE_20D_AGO"]
        missing = [c for c in required if c not in stock_df.columns]
        if missing:
            return pd.DataFrame()

        stock_df["STOCK_RETURN"] = (
            (stock_df["CLOSE"] - stock_df["CLOSE_20D_AGO"])
            / stock_df["CLOSE_20D_AGO"]
        ) * 100

        # index_df: single dict/row with index's own 20-day return,
        # passed in by app.py after computing it once from NIFTY history.
        index_return = 0.0
        if index_df is not None and len(index_df) > 0:
            if isinstance(index_df, dict):
                index_return = index_df.get("INDEX_RETURN_20D", 0.0)
            elif "INDEX_RETURN_20D" in index_df.columns:
                index_return = float(index_df["INDEX_RETURN_20D"].iloc[0])

        stock_df["RS"] = stock_df["STOCK_RETURN"] - index_return

        result = stock_df[
            stock_df["RS"] > 0
        ]

        return result.reset_index(drop=True)

    def add_score(self, df):

        df = df.copy()

        score = (
            ((df["RS"] > 0).astype(int) * 40)
            + ((df["RS"] > 5).astype(int) * 30)
            + ((df["CLOSE"] > df["OPEN"]).astype(int) * 30)
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
        
