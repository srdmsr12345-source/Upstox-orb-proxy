import io
import zipfile
import requests
import pandas as pd

from datetime import datetime

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

    def download(self, url):
        r = self.session.get(
            url,
            timeout=60
        )
        r.raise_for_status()
        return r.content

    def today(self):
        return datetime.now()

    def bhavcopy_url(self, date=None):
        if date is None:
            date = datetime.now()

        return (
            "https://nsearchives.nseindia.com/"
            "content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{date.strftime('%Y%m%d')}_F_0000.csv.zip"
        )

    def delivery_url(self, date=None):
        if date is None:
            date = datetime.now()

        return (
            "https://nsearchives.nseindia.com/"
            "products/content/"
            f"sec_bhavdata_full_{date.strftime('%d%b%Y').upper()}.csv"
        )

    def read_zip_csv(self, content):
        z = zipfile.ZipFile(io.BytesIO(content))
        name = z.namelist()[0]

        with z.open(name) as f:
            df = pd.read_csv(f)

        return df

    def read_csv(self, content):
        return pd.read_csv(io.BytesIO(content))

    def get_bhavcopy(self, date=None):

        key = f"bhavcopy_{(date or datetime.now()).strftime('%Y%m%d')}"

        cached = cache.get(key, max_age=86400)

        if cached is not None:
            return pd.DataFrame(cached)

        df = self.read_zip_csv(
            self.download(
                self.bhavcopy_url(date)
            )
        )

        cache.save(
            key,
            df.to_dict("records")
        )

        return df

    def get_delivery(self, date=None):

        key = f"delivery_{(date or datetime.now()).strftime('%Y%m%d')}"

        cached = cache.get(key, max_age=86400)

        if cached is not None:
            return pd.DataFrame(cached)

        df = self.read_csv(
            self.download(
                self.delivery_url(date)
            )
        )

        cache.save(
            key,
            df.to_dict("records")
        )

        return df

    def merge_bhav_delivery(self, date=None):

        bhav = self.get_bhavcopy(date)
        delivery = self.get_delivery(date)

        bhav.columns = bhav.columns.str.strip()
        delivery.columns = delivery.columns.str.strip()

        merged = bhav.merge(
            delivery,
            on="SYMBOL",
            how="left"
        )

        return merged


nse = NSEData()
