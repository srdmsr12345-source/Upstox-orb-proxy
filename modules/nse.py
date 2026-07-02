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

        # Nov-2025 ke baad NSE ne bhavcopy mein pre-open session data bhi
        # daalna shuru kar diya (session indicators I1/I2 for interim,
        # F1/F2 for final). Hum sirf regular EQ series + final session
        # chahte hain, warna duplicate/galat rows aa jate hain. Agar
        # SESSION column maujood ho to F session filter karo, warna
        # purana format hai (skip).
        if "SERIES" in df.columns:
            df = df[df["SERIES"] == "EQ"]

        session_col = None
        for col in df.columns:
            if col.upper() in ("SESSION", "SESS_ID", "SESSION_ID"):
                session_col = col
                break

        if session_col is not None:
            df = df[
                df[session_col].astype(str).str.upper().str.startswith("F")
            ]

        df = df.reset_index(drop=True)

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

        # Dono files mein SYMBOL column ke aas-paas whitespace/case
        # mismatch ho sakta hai - normalize karte hain merge se pehle
        # taaki rows silently drop na ho jayein.
        bhav = bhav.copy()
        delivery = delivery.copy()

        bhav.columns = bhav.columns.str.strip()
        delivery.columns = delivery.columns.str.strip()

        if "SYMBOL" in bhav.columns:
            bhav["SYMBOL"] = bhav["SYMBOL"].astype(str).str.strip().str.upper()

        if "SYMBOL" in delivery.columns:
            delivery["SYMBOL"] = delivery["SYMBOL"].astype(str).str.strip().str.upper()

        merged = bhav.merge(
            delivery,
            on="SYMBOL",
            how="left"
        )

        # Numeric columns ko explicitly numeric type mein convert karte
        # hain - bhavcopy/delivery CSV se aane wale string values ko
        # scanners ke saare numeric comparisons (>=, rolling, etc.) ke
        # liye float hona zaroori hai.
        numeric_cols = [
            "OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE",
            "TOTTRDQTY", "TOTTRDVAL", "TOTALTRADES"
        ]
        for col in numeric_cols:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")

        # Delivery % column ka naam file format ke hisaab se badal sakta
        # hai - dhoondh ke ek standard "DELIV_PER" naam de dete hain.
        deliv_col = None
        for col in merged.columns:
            cu = col.upper()
            if "DELIV" in cu and "PER" in cu:
                deliv_col = col
                break
            if cu == "% DLY QT TO TRADED QTY" or cu == "DELIV_PER":
                deliv_col = col
                break

        if deliv_col and deliv_col != "DELIV_PER":
            merged["DELIV_PER"] = pd.to_numeric(merged[deliv_col], errors="coerce")
        elif "DELIV_PER" in merged.columns:
            merged["DELIV_PER"] = pd.to_numeric(merged["DELIV_PER"], errors="coerce")
        else:
            merged["DELIV_PER"] = 0.0

        merged["DELIV_PER"] = merged["DELIV_PER"].fillna(0.0)

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
    
