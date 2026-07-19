"""Shared MongoDB persistence helpers."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient


class MongoDocumentStore:
    """Persist agent output using the shared DocAI Mongo configuration."""

    def __init__(self, collection_name: str) -> None:
        mongo_uri = os.getenv("MONGO_URI")
        database_name = os.getenv("MONGO_DB_NAME")
        if not mongo_uri:
            raise ValueError("MONGO_URI is required for MongoDB persistence.")
        if not database_name:
            raise ValueError("MONGO_DB_NAME is required for MongoDB persistence.")
        self.client = MongoClient(mongo_uri)
        self.collection = self.client[database_name][collection_name]

    def upsert(self, identity: dict[str, Any], document: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        update = dict(document)
        update["UpdatedAt"] = now
        result = self.collection.update_one(
            identity,
            {
                "$set": update,
                "$setOnInsert": {"CreatedAt": now},
            },
            upsert=True,
        )
        stored = self.collection.find_one(identity, {"_id": 1})
        if not stored:
            raise RuntimeError("MongoDB upsert completed without a retrievable document.")
        return str(stored["_id"])

    def insert(self, document: dict[str, Any]) -> str:
        result = self.collection.insert_one(dict(document))
        return str(result.inserted_id)

    def set_status(self, identity: dict[str, Any], status: str, upsert: bool = False) -> bool:
        result = self.collection.update_one(
            identity,
            {
                "$set": {
                    "Status": status,
                    "UpdatedAt": datetime.now(timezone.utc),
                }
            },
            upsert=upsert,
        )
        return bool(result.matched_count or result.upserted_id)

    def find_one(self, identity: dict[str, Any]) -> dict[str, Any] | None:
        document = self.collection.find_one(identity)
        if document and "_id" in document:
            document["_id"] = str(document["_id"])
        return document

    def find_latest(self, identity: dict[str, Any]) -> dict[str, Any] | None:
        document = self.collection.find_one(identity, sort=[("CreatedAt", -1), ("_id", -1)])
        if document and "_id" in document:
            document["_id"] = str(document["_id"])
        return document

    def close(self) -> None:
        self.client.close()