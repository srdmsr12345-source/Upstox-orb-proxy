import io
import zipfile
import requests
import pandas as pd

from datetime import datetime, timedelta

from modules.cache import cache
from config import (
    BHAVCOPY_FOLDER,
    DELIVERY_FOLDER
)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com"
}


class NSEData:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(NSE_HEADERS)

    # ------------------------------------
    # Smart Trading Day Engine
    # ------------------------------------

    def today(self):
        return datetime.now()

    def is_weekend(self, date):
        return date.weekday() >= 5

    def previous_day(self, date):
        return date - timedelta(days=1)

    def previous_trading_day(self, date):

        d = date

        while self.is_weekend(d):
            d = self.previous_day(d)

        return d

    def normalize_date(self, date=None):

        if date is None:
            date = self.today()

        if isinstance(date, str):
            date = datetime.strptime(
                date,
                "%Y-%m-%d"
            )

        return date

    def effective_date(self, date=None):

        date = self.normalize_date(date)

        now = self.today()

        # Market open hone se pehle
        if (
            date.date() == now.date()
            and
            now.hour < 19
        ):
            date = self.previous_day(date)

        date = self.previous_trading_day(date)

        return date

    # ------------------------------------
    # URL Builders
    # ------------------------------------

    def bhavcopy_url(self, date=None):

        date = self.effective_date(date)

        return (
            "https://nsearchives.nseindia.com/"
            "content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{date.strftime('%Y%m%d')}_F_0000.csv.zip"
        )

    def delivery_url(self, date=None):

        date = self.effective_date(date)

        return (
            "https://nsearchives.nseindia.com/"
            "products/content/"
            f"sec_bhavdata_full_{date.strftime('%d%b%Y').upper()}.csv"
)
            # ------------------------------------
    # Download Engine
    # ------------------------------------

    def download(self, url):

        r = self.session.get(
            url,
            timeout=60
        )

        r.raise_for_status()

        return r.content


    def safe_download(self, url_builder, date):

        """
        Try current date.
        If 404 comes, automatically move to previous
        trading day (maximum 10 attempts).
        """

        current = self.effective_date(date)

        for _ in range(10):

            try:

                content = self.download(
                    url_builder(current)
                )

                return current, content

            except requests.HTTPError as e:

                if e.response.status_code == 404:

                    current = self.previous_trading_day(
                        current - timedelta(days=1)
                    )

                    continue

                raise

        raise Exception(
            "No NSE file found for last 10 trading days."
        )


    # ------------------------------------
    # File Readers
    # ------------------------------------

    def read_zip_csv(self, content):

        z = zipfile.ZipFile(
            io.BytesIO(content)
        )

        filename = z.namelist()[0]

        with z.open(filename) as f:

            df = pd.read_csv(f)

        return df


    def read_csv(self, content):

        return pd.read_csv(
            io.BytesIO(content)
        )


    # ------------------------------------
    # Cache Helpers
    # ------------------------------------

    def cache_key(self, prefix, date):

        return (
            f"{prefix}_"
            f"{date.strftime('%Y%m%d')}"
)
            # ------------------------------------
    # Bhavcopy
    # ------------------------------------

    def get_bhavcopy(self, date=None):

        actual_date, content = self.safe_download(
            self.bhavcopy_url,
            date
        )

        key = self.cache_key(
            "bhavcopy",
            actual_date
        )

        cached = cache.get(
            key,
            max_age=86400
        )

        if cached is not None:

            return (
                pd.DataFrame(cached),
                actual_date
            )

        df = self.read_zip_csv(content)

        df.columns = df.columns.str.strip()

        cache.save(
            key,
            df.to_dict("records")
        )

        return (
            df,
            actual_date
        )

    # ------------------------------------
    # Delivery
    # ------------------------------------

    def get_delivery(self, date=None):

        actual_date, content = self.safe_download(
            self.delivery_url,
            date
        )

        key = self.cache_key(
            "delivery",
            actual_date
        )

        cached = cache.get(
            key,
            max_age=86400
        )

        if cached is not None:

            return (
                pd.DataFrame(cached),
                actual_date
            )

        df = self.read_csv(content)

        df.columns = df.columns.str.strip()

        cache.save(
            key,
            df.to_dict("records")
        )

        return (
            df,
            actual_date
        )

    # ------------------------------------
    # Merge
    # ------------------------------------

    def merge_bhav_delivery(self, date=None):

        bhav, actual_date = self.get_bhavcopy(date)

        delivery, _ = self.get_delivery(actual_date)

        merged = bhav.merge(
            delivery,
            on="SYMBOL",
            how="left"
        )

        return {
            "date": actual_date.strftime("%d-%b-%Y"),
            "data": merged
}
            # ------------------------------------
    # Utility
    # ------------------------------------

    def latest_data(self, date=None):
        """
        Returns:
        {
            "date": "26-Jun-2026",
            "data": DataFrame
        }
        """
        return self.merge_bhav_delivery(date)


# Global Object
nse = NSEData()
