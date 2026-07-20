from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from .settings import Settings

logger = logging.getLogger("uvicorn.error")


class PlannerRepository(Protocol):
    def load_requirements(
        self, company_id: str, tender_id: str, operational_status: str
    ) -> dict[str, Any] | None: ...
    def load_evaluation(
        self, company_id: str, tender_id: str, operational_status: str
    ) -> dict[str, Any] | None: ...
    def save_plan(self, document: dict[str, Any], regenerate: bool) -> dict[str, Any]: ...
    def load_latest_plan(
        self, company_id: str, tender_id: str, project_id: str | None = None
    ) -> dict[str, Any] | None: ...


class MongoPlannerRepository:
    """Mongo adapter following the Proposal Agent's document-store conventions."""

    def __init__(self, database: Any | None = None, settings: Settings | None = None) -> None:
        settings = settings or Settings.from_env()
        if database is None:
            from pymongo import MongoClient

            client = MongoClient(settings.mongo_uri)
            database = client[settings.mongo_db_name]
        self.database = database
        self.requirement_collection = settings.requirement_deduplication_collection
        self.evaluation_collection = settings.evaluation_criteria_collection
        self.plan_collection = settings.tender_section_plan_collection

    @staticmethod
    def _scope(company_id: str, tender_id: str) -> dict[str, Any]:
        return {"CompanyId": company_id, "TenderId": tender_id}

    def _latest(self, collection: str, query: dict[str, Any]) -> dict[str, Any] | None:
        return self.database[collection].find_one(
            query,
            sort=[
                ("CompletedAt", -1),
                ("UpdatedAt", -1),
                ("ModifiedDate", -1),
                ("CreatedAt", -1),
                ("CreatedDate", -1),
                ("_id", -1),
            ],
        )

    @staticmethod
    def _timestamp(value: Any) -> float:
        if isinstance(value, datetime):
            return value.replace(tzinfo=value.tzinfo or timezone.utc).timestamp()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return float("-inf")
        return float("-inf")

    @classmethod
    def _source_recency_key(cls, document: dict[str, Any]) -> tuple[Any, ...]:
        timestamps = tuple(
            cls._timestamp(document.get(field))
            for field in (
                "CompletedAt",
                "UpdatedAt",
                "ModifiedDate",
                "CreatedAt",
                "CreatedDate",
            )
        )
        return (max(timestamps), *timestamps, str(document.get("_id") or ""))

    def _newest_eligible(
        self, collection: str, query: dict[str, Any]
    ) -> dict[str, Any] | None:
        source = self.database[collection]
        try:
            documents = list(source.find(query))
        except AttributeError:
            return self._latest(collection, query)
        return max(documents, key=self._source_recency_key) if documents else None

    def load_requirements(
        self, company_id: str, tender_id: str, operational_status: str = "Active"
    ) -> dict[str, Any] | None:
        query = self._scope(company_id, tender_id)
        valid_status = {"$regex": "^(active|regenerating)$", "$options": "i"}
        query["$or"] = [
            {"Status": valid_status},
            {"Output.Status": valid_status},
            {"JsonOutput.Status": valid_status},
            {"FinalJson.Status": valid_status},
        ]
        return self._newest_eligible(self.requirement_collection, query)

    def load_evaluation(
        self, company_id: str, tender_id: str, operational_status: str = "Active"
    ) -> dict[str, Any] | None:
        query = self._scope(company_id, tender_id)
        valid_status = {"$regex": "^(active|regenerating)$", "$options": "i"}
        completed = {"$regex": "^completed$", "$options": "i"}
        query["$and"] = [
            {
                "$or": [
                    {"Status": valid_status},
                    {"Output.Status": valid_status},
                    {"JsonOutput.Status": valid_status},
                    {"FinalJson.Status": valid_status},
                ]
            },
            {
                "$or": [
                    {"ExtractionStatus": completed},
                    {"Output.ExtractionStatus": completed},
                    {"JsonOutput.ExtractionStatus": completed},
                    {"FinalJson.ExtractionStatus": completed},
                ]
            },
        ]
        return self._newest_eligible(self.evaluation_collection, query)

    def log_collection_selection(self) -> None:
        logger.info("Requirement Deduplication collection: %s", self.requirement_collection)
        logger.info("Evaluation Criteria collection: %s", self.evaluation_collection)
        logger.info("Tender Section Plan collection: %s", self.plan_collection)
        try:
            names = set(self.database.list_collection_names())
        except Exception as exc:
            logger.warning("Unable to inspect MongoDB collection names at startup: %s", type(exc).__name__)
            return
        legacy = "RequirementDeduplication"
        current = "TenderRequirementDeduplications"
        if legacy in names and current in names:
            logger.warning(
                "Both requirement collections exist; using configured collection %s without merging %s and %s",
                self.requirement_collection,
                legacy,
                current,
            )

    def save_plan(self, document: dict[str, Any], regenerate: bool) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        identity = {
            "CompanyId": document["CompanyId"],
            "TenderId": document["TenderId"],
            "ProjectId": document["ProjectId"],
        }
        section_count = sum(
            len(group.get("Sections", [])) for group in document.get("ProposalGroups", [])
        )
        wrapper = {
            "ProposalPlanId": document["ProposalPlanId"],
            "CompanyId": document["CompanyId"],
            "TenderId": document["TenderId"],
            "ProjectId": document["ProjectId"],
            "Sector": document.get("Sector", ""),
            "RequirementDeduplicationId": document.get("RequirementDeduplicationId"),
            "PlanStatus": document["PlanStatus"],
            "TotalGroups": len(document.get("ProposalGroups", [])),
            "TotalSections": section_count,
            "RequiredSectionCount": section_count,
            "TotalMappedRequirements": len(document.get("MappedRequirementIds", [])),
            "JsonOutput": document,
            "Status": document["Status"],
            "CreatedBy": document.get("UserId"),
            "ModifiedDate": now,
        }
        existing = self.database[self.plan_collection].find_one(identity)
        if existing:
            wrapper["CreatedDate"] = existing.get("CreatedDate", now)
            self.database[self.plan_collection].replace_one({"_id": existing["_id"]}, wrapper)
        else:
            wrapper["CreatedDate"] = now
            self.database[self.plan_collection].insert_one(dict(wrapper))
        return document

    def load_latest_plan(
        self, company_id: str, tender_id: str, project_id: str | None = None
    ) -> dict[str, Any] | None:
        query = self._scope(company_id, tender_id)
        if project_id:
            query["ProjectId"] = project_id
        record = self._latest(self.plan_collection, query)
        if not record:
            return None
        json_output = record.get("JsonOutput")
        if isinstance(json_output, dict):
            return json_output
        final_json = record.get("FinalJson")
        return final_json if isinstance(final_json, dict) else record
