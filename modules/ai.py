import pandas as pd


class AIRanker:

    def __init__(self):
        pass

    def rank(self, df):

        if df.empty:
            return df

        df = df.copy()

        score_columns = [
            c for c in df.columns
            if c.endswith("_SCORE")
        ]

        if not score_columns:
            df["AI_SCORE"] = 0
            return df

        df["AI_SCORE"] = (
            df[score_columns]
            .fillna(0)
            .sum(axis=1)
        )

        df = df.sort_values(
            "AI_SCORE",
            ascending=False
        )

        return df.reset_index(drop=True)

    def confidence(self, df):

        df = df.copy()

        df["CONFIDENCE"] = "LOW"

        df.loc[
            df["AI_SCORE"] >= 80,
            "CONFIDENCE"
        ] = "HIGH"

        df.loc[
            (df["AI_SCORE"] >= 60)
            &
            (df["AI_SCORE"] < 80),
            "CONFIDENCE"
        ] = "MEDIUM"

        return df

    def top(self, df, limit=20):

        if df.empty:
            return df

        df = self.rank(df)
        df = self.confidence(df)

        return df.head(limit)

    def summary(self, df):

        if df.empty:
            return {
                "total": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }

        return {
            "total": len(df),
            "high": len(df[df["CONFIDENCE"] == "HIGH"]),
            "medium": len(df[df["CONFIDENCE"] == "MEDIUM"]),
            "low": len(df[df["CONFIDENCE"] == "LOW"])
        }


ai_ranker = AIRanker()
