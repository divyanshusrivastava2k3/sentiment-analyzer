"""MongoDB storage layer with automatic file-based fallback.

If MongoDB is unreachable (service stopped / not installed), every write
falls back to a local JSON file so the app keeps working for demos.
"""
import json
import os
import threading
from datetime import datetime, timezone

from pymongo import MongoClient, errors

from config import BASE_DIR, Config

FALLBACK_PATH = os.path.join(BASE_DIR, "data", "analyses.json")
_lock = threading.Lock()


class Store:
    def __init__(self):
        self._client = None
        self._db = None
        self.mongo_ok = False
        self._connect()

    def _connect(self):
        try:
            client = MongoClient(
                Config.MONGO_URI, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500
            )
            client.admin.command("ping")
            self._client = client
            self._db = client[Config.MONGO_DB]
            self.mongo_ok = True
        except errors.PyMongoError:
            os.makedirs(os.path.dirname(FALLBACK_PATH), exist_ok=True)
            if not os.path.exists(FALLBACK_PATH):
                with open(FALLBACK_PATH, "w", encoding="utf-8") as f:
                    json.dump([], f)

    @property
    def collection(self):
        return self._db.analyses if self.mongo_ok else None

    # -- public API -------------------------------------------------------
    def save_analysis(self, source: str, summary: dict, rows: list) -> dict:
        doc = {
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "rows": rows,
        }
        if self.mongo_ok:
            result = self.collection.insert_one(doc)
            doc["_id"] = str(result.inserted_id)
        else:
            with _lock:
                docs = self._read_fallback()
                doc["_id"] = f"local-{len(docs) + 1}"
                docs.append(doc)
                with open(FALLBACK_PATH, "w", encoding="utf-8") as f:
                    json.dump(docs, f, ensure_ascii=False, indent=2)
        return doc

    def recent_analyses(self, limit: int = 20) -> list:
        if self.mongo_ok:
            cursor = (
                self.collection.find({}, {"rows": 0})
                .sort("$natural", -1)
                .limit(limit)
            )
            out = []
            for d in cursor:
                d["_id"] = str(d["_id"])
                out.append(d)
            return out
        with _lock:
            docs = self._read_fallback()
        return [{**d, "rows": None} for d in reversed(docs[-limit:])]

    def get_analysis(self, analysis_id: str):
        if self.mongo_ok:
            from bson.errors import InvalidId
            from bson.objectid import ObjectId

            try:
                d = self.collection.find_one({"_id": ObjectId(analysis_id)})
            except (InvalidId, TypeError):
                return None
            if d:
                d["_id"] = str(d["_id"])
            return d
        with _lock:
            docs = self._read_fallback()
        return next((d for d in docs if d.get("_id") == analysis_id), None)

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _read_fallback() -> list:
        try:
            with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []


store = Store()
