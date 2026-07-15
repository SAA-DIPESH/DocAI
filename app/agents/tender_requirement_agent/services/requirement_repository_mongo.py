import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import MongoClient, UpdateOne


class TenderRequirementRepository:

    def __init__(self,mongo_uri: Optional[str] = None,database_name: Optional[str] = None) -> None:
        self.client = MongoClient(mongo_uri or os.getenv("MONGODB_URI","mongodb://localhost:27017/"),serverSelectionTimeoutMS=5000)
        database = self.client[database_name or os.getenv("MONGODB_DATABASE","DocAI")]
        self.requirements_collection = database[os.getenv("REQUIREMENTS_COLLECTION","tender_requirements")]
        self.chunks_collection = database[os.getenv("CHUNKS_COLLECTION","tender_chunks")]

    def ping(self) -> None:
        self.client.admin.command("ping")

    # ==========================================================
    # Single Upsert
    # ==========================================================

    def upsert_requirement(self,requirement: Dict[str, Any]) -> None:

        now = datetime.now(timezone.utc)
        payload = deepcopy(requirement)
        payload["UpdatedAt"] = now

        self.requirements_collection.update_one(
            {
                "DocumentId": payload["DocumentId"],
                "RequirementId": payload["RequirementId"],
            },
            {
                "$set": payload,
                "$setOnInsert": {
                    "CreatedAt": now,
                },
            },
            upsert=True,
        )

    # ==========================================================
    # Bulk Upsert
    # ==========================================================

    def bulk_upsert_requirements(self, requirements: List[Dict[str, Any]]) -> None:

        if not requirements:
            return

        now = datetime.now(timezone.utc)

        operations = []

        for requirement in requirements:

            payload = deepcopy(requirement)
            payload["UpdatedAt"] = now

            operations.append(
                UpdateOne(
                    {
                        "DocumentId": payload["DocumentId"],
                        "RequirementId": payload["RequirementId"],
                    },
                    {
                        "$set": payload,
                        "$setOnInsert": {
                            "CreatedAt": now,
                        },
                    },
                    upsert=True,
                )
            )

        if operations:
            self.requirements_collection.bulk_write(
                operations,
                ordered=False,
            )

    # ==========================================================
    # Chunk Status
    # ==========================================================

    def upsert_chunk_status(self,chunk_data: Dict[str, Any]) -> None:

        now = datetime.now(timezone.utc)
        payload = deepcopy(chunk_data)
        payload["UpdatedAt"] = now

        self.chunks_collection.update_one(
            {
                "DocumentId": payload["DocumentId"],
                "ChunkId": payload["ChunkId"],
            },
            {
                "$set": payload,
                "$setOnInsert": {
                    "CreatedAt": now,
                },
            },
            upsert=True,
        )


# Create Object TenderRequirementRepository Class
requirement_repository = TenderRequirementRepository()