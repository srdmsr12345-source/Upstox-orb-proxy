import requests
import zipfile
import io
import pandas as pd
from datetime import datetime

from modules.cache import cache
from config import BHAVCOPY_FOLDER, DELIVERY_FOLDER


class NSEData:

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({

            "User-Agent":
            "Mozilla/5.0",

            "Accept":
            "*/*"

        })

    def download(self, url):

        r = self.session.get(
            url,
            timeout=60
        )

        r.raise_for_status()

        return r.content

    def today(self):

        return datetime.now()

nse = NSEData()
import os
import pandas as pd

class NSEData:

    # Part 1 वाला code रहेगा

    def save_csv(self, df, folder, filename):

        os.makedirs(folder, exist_ok=True)

        path = os.path.join(folder, filename)

        df.to_csv(path, index=False)

        return path


    def load_csv(self, folder, filename):

        path = os.path.join(folder, filename)

        if not os.path.exists(path):
            return None

        return pd.read_csv(path)
          def download_bhavcopy(self, url):

        content = self.download(url)

        if url.endswith(".zip"):

            import zipfile
            import io

            z = zipfile.ZipFile(io.BytesIO(content))

            csv_name = z.namelist()[0]

            with z.open(csv_name) as f:

                df = pd.read_csv(f)

        else:

            from io import BytesIO

            df = pd.read_csv(BytesIO(content))

        return df


    def cache_bhavcopy(self, date, url):

        key = f"bhavcopy_{date}"

        data = cache.get(key, max_age=86400)

        if data:

            return pd.DataFrame(data)

        df = self.download_bhavcopy(url)

        cache.save(
            key,
            df.to_dict("records")
        )

        return df
      from datetime import datetime


    def get_bhavcopy_url(self, date=None):

        if date is None:
            date = datetime.now()

        dd = date.strftime("%d")
        mm = date.strftime("%m")
        yyyy = date.strftime("%Y")
        mon = date.strftime("%b").upper()

        return (
            f"https://nsearchives.nseindia.com/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{yyyy}{mm}{dd}_F_0000.csv.zip"
        )


  def get_delivery_url(self, date=None):

        if date is None:
            date = datetime.now()

        dd = date.strftime("%d")
        mm = date.strftime("%m")
        yyyy = date.strftime("%Y")
        mon = date.strftime("%b").upper()

        return (
            f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}{mon}{yyyy}.csv"
   )
      def get_security_master(self):

        key = "security_master"

        data = cache.get(key, max_age=86400)

        if data is not None:
            return pd.DataFrame(data)

        url = (
            "https://archives.nseindia.com/content/equities/"
            "EQUITY_L.csv"
        )

        df = pd.read_csv(url)

        cache.save(
            key,
            df.to_dict("records")
        )

        return df
        
