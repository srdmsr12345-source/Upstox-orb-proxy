import os
import json
import time
from pathlib import Path

CACHE_DIR = "data/cache"

# Cache Folder बनाओ
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


class Cache:

    def __init__(self, folder=CACHE_DIR):
        self.folder = folder

    def _file(self, key):
        return os.path.join(self.folder, f"{key}.json")

    def save(self, key, data):

        payload = {
            "timestamp": int(time.time()),
            "data": data
        }

        with open(self._file(key), "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def load(self, key):

        path = self._file(key)

        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        return payload

    def get(self, key, max_age=3600):

        payload = self.load(key)

        if payload is None:
            return None

        age = int(time.time()) - payload["timestamp"]

        if age > max_age:
            return None

        return payload["data"]

    def delete(self, key):

        path = self._file(key)

        if os.path.exists(path):
            os.remove(path)

    def clear(self):

        for file in os.listdir(self.folder):

            if file.endswith(".json"):

                os.remove(
                    os.path.join(self.folder, file)
                )

    def cleanup(self, max_age=86400):

        now = int(time.time())

        for file in os.listdir(self.folder):

            if not file.endswith(".json"):
                continue

            path = os.path.join(self.folder, file)

            try:

                with open(path, "r", encoding="utf-8") as f:

                    payload = json.load(f)

                age = now - payload["timestamp"]

                if age > max_age:

                    os.remove(path)

            except Exception:

                pass


cache = Cache()
