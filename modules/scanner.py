import pandas as pd

from plugins.bottom import bottom_scanner
from plugins.volume import volume_scanner
from plugins.smartmoney import smartmoney_scanner
from plugins.stage2 import stage2_scanner
from plugins.orb import orb_scanner
from plugins.relativestrength import relative_strength_scanner


class ScannerEngine:

    def __init__(self):
        pass

    def bottom(self, df):
        return bottom_scanner.top_candidates(df)

    def volume(self, df):
        return volume_scanner.top_candidates(df)

    def smartmoney(self, df):
        return smartmoney_scanner.top_candidates(df)

    def stage2(self, df):
        return stage2_scanner.top_candidates(df)

    def orb(self, df):
        return orb_scanner.top_candidates(df)

    def relativestrength(self, stock_df, index_df):
        return relative_strength_scanner.top_candidates(
            stock_df,
            index_df
        )

    def run(self, scan_type, stock_df, index_df=None):

        scan_type = scan_type.lower()

        if scan_type == "bottom":
            return self.bottom(stock_df)

        elif scan_type == "volume":
            return self.volume(stock_df)

        elif scan_type == "smartmoney":
            return self.smartmoney(stock_df)

        elif scan_type == "stage2":
            return self.stage2(stock_df)

        elif scan_type == "orb":
            return self.orb(stock_df)

        elif scan_type == "relativestrength":

            if index_df is None:
                raise ValueError(
                    "index_df is required for Relative Strength scan"
                )

            return self.relativestrength(
                stock_df,
                index_df
            )

        else:
            raise ValueError(
                f"Unknown scan type: {scan_type}"
            )


scanner = ScannerEngine()
