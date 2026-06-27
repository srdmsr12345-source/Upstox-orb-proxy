    def run(
        self,
        scan_type,
        stock_df,
        index_df=None
    ):

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
