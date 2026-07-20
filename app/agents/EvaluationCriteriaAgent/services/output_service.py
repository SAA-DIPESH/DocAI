"""MongoDB output persistence for the Evaluation Criteria Agent."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from app.infrastructure.database import MongoDocumentStore


class EvaluationCriteriaOutputService:
    collection_name = "EvaluationCriteria"

    @classmethod
    def save(
        cls,
        output: dict[str, Any],
        is_regenerated: bool,
        created_by: str,
        run_id: str,
    ) -> str:
        if not output.get("CompanyId") or not output.get("TenderId"):
            raise ValueError(
                "CompanyId and TenderId are required for MongoDB persistence."
            )
    
        document = dict(output)
    
        if is_regenerated:
            document["Status"] = "Regenerating"
        else:
            document["Status"] = "Active"
    
        document["IsRegenerated"] = is_regenerated
        document["CreatedBy"] = created_by
        document["CreatedAt"] = datetime.now(timezone.utc)
        document["RunId"] = run_id
    
        store = MongoDocumentStore(cls.collection_name)
    
        try:
            # Always creates a new MongoDB document.
            return store.insert(document)
        finally:
            store.close()
            
    @classmethod
    def insert_regenerated(
        cls,
        output: dict[str, Any],
        created_by: str,
        run_id: str,
    ) -> tuple[str, dict[str, Any]]:
        document = dict(output)
        document["Status"] = "Regenerating"
        document["CreatedBy"] = created_by
        document["CreatedAt"] = datetime.now(timezone.utc)
        document["RunId"] = run_id
        store = MongoDocumentStore(cls.collection_name)
        try:
            document_id = store.insert(document)
        finally:
            store.close()
        response = dict(document)
        response["_id"] = document_id
        return document_id, response

    @classmethod
    def set_status(
        cls,
        company_id: str,
        tender_id: str,
        status: str,
        upsert: bool = False,
    ) -> bool:
        store = MongoDocumentStore(cls.collection_name)
        try:
            return store.set_status(
                {"CompanyId": company_id, "TenderId": tender_id},
                status,
                upsert=upsert,
            )
        finally:
            store.close()

    @classmethod
    def get(cls, company_id: str, tender_id: str) -> dict[str, Any] | None:
        store = MongoDocumentStore(cls.collection_name)
        try:
            return store.find_one({"CompanyId": company_id, "TenderId": tender_id})
        finally:
            store.close()

    @classmethod
    def get_active(cls, company_id: str, tender_id: str) -> dict[str, Any] | None:
        store = MongoDocumentStore(cls.collection_name)
        try:
            return store.find_latest(
                {
                    "CompanyId": company_id,
                    "TenderId": tender_id,
                    "Status": "Active",
                }
            )
        finally:
            store.close()


__all__ = ["EvaluationCriteriaOutputService"]
