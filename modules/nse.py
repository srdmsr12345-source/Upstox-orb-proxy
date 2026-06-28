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

    # ==========================================
    # DATE ENGINE
    # ==========================================

    def today(self):
        return datetime.now()

    def is_weekend(self, d):
        return d.weekday() >= 5

    def previous_day(self, d):
        return d - timedelta(days=1)

    def previous_trading_day(self, d):

        while self.is_weekend(d):
            d -= timedelta(days=1)

        return d

    def normalize_date(self, date=None):

        if date is None:
            date = self.today()

        if isinstance(date, str):

            try:

                date = datetime.strptime(
                    date,
                    "%Y-%m-%d"
                )

            except:

                date = datetime.strptime(
                    date,
                    "%d/%m/%Y"
                )

        return date

    def effective_date(self, date=None):

        date = self.normalize_date(date)

        now = self.today()

        if (
            date.date() == now.date()
            and
            now.hour < 19
        ):
            date -= timedelta(days=1)

        return self.previous_trading_day(date)

    # ==========================================
    # URL BUILDERS
    # ==========================================

    def bhavcopy_url(self, d):

        return (
            "https://nsearchives.nseindia.com/"
            "content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"
        )

    def delivery_url(self, d):

        return (
            "https://nsearchives.nseindia.com/"
            "products/content/"
            f"sec_bhavdata_full_{d.strftime('%d%b%Y').upper()}.csv"
        )

    # ==========================================
    # DOWNLOAD
    # ==========================================

    def download(self, url):

        r = self.session.get(
            url,
            timeout=60
        )

        r.raise_for_status()

        return r.content

    def safe_download(
        self,
        url_builder,
        date=None
    ):

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

    # ==========================================
    # READERS
    # ==========================================

    def read_zip_csv(self, content):

        z = zipfile.ZipFile(
            io.BytesIO(content)
        )

        filename = z.namelist()[0]

        with z.open(filename) as f:

            df = pd.read_csv(f)

        df.columns = df.columns.str.strip()

        return df

    def read_csv(self, content):

        df = pd.read_csv(
            io.BytesIO(content)
        )

        df.columns = df.columns.str.strip()

        return df

    # ==========================================
    # CACHE
    # ==========================================

    def cache_key(self, prefix, d):

        return (
            f"{prefix}_"
            f"{d.strftime('%Y%m%d')}"
        )
            # ==========================================
    # BHAVCOPY
    # ==========================================

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

        cache.save(
            key,
            df.to_dict("records")
        )

        return (
            df,
            actual_date
        )

    # ==========================================
    # DELIVERY
    # ==========================================

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

        cache.save(
            key,
            df.to_dict("records")
        )

        return (
            df,
            actual_date
        )

    # ==========================================
    # MERGE
    # ==========================================

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

    # ==========================================
    # PUBLIC API
    # ==========================================

    def latest_data(self, date=None):

        return self.merge_bhav_delivery(date)


# ==========================================
# GLOBAL OBJECT
# ==========================================

nse = NSEData()
