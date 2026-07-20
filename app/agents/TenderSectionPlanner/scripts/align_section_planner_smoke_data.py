from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson.json_util import dumps
from pymongo import MongoClient

from section_planner.service import extract_deduplicated_requirements
from section_planner.settings import Settings

TARGET_COMPANY_ID = "6a45059ff419103201431533"
TARGET_TENDER_ID = "6a4506d2f4191032014315fd"
SOURCE_COMPANY_ID = "6a202607915f3a8b0831fec6"
SOURCE_TENDER_ID = "6a3116bdd84ecafff02388c7"
TEST_REASON = "Section Planner real OpenAI end-to-end smoke test"
TEST_CREATOR = "Codex integration utility"


class AlignmentError(RuntimeError):
    pass


def _status_valid(value: Any) -> bool:
    return str(value or "").lower() in {"active", "completed"}


def _set_existing_dates(document: dict[str, Any], now: datetime) -> None:
    for field in ("CreatedAt", "UpdatedAt", "CreatedDate", "ModifiedDate"):
        if field in document:
            document[field] = now


class SmokeDataAligner:
    def __init__(self, database: Any, settings: Settings, backup_dir: Path) -> None:
        self.database = database
        self.settings = settings
        self.backup_dir = backup_dir

    @property
    def target(self) -> dict[str, str]:
        return {"CompanyId": TARGET_COMPANY_ID, "TenderId": TARGET_TENDER_ID}

    @property
    def source(self) -> dict[str, str]:
        return {"CompanyId": SOURCE_COMPANY_ID, "TenderId": SOURCE_TENDER_ID}

    def run(self) -> dict[str, Any]:
        before = self._counts()
        evaluation = self._select_evaluation()
        requirement_source = self._select_requirement_source()
        requirement, requirement_action = self._align_requirement(requirement_source)
        backup_path = self._backup(
            {
                "RequirementSource": requirement_source,
                "RequirementSelected": requirement,
                "EvaluationSelected": evaluation,
            }
        )
        canonical = extract_deduplicated_requirements(requirement)
        canonical_ids = [
            str(item.get("CanonicalRequirementId") or "")
            for item in canonical
        ]
        if not canonical_ids or len(set(canonical_ids)) != len(canonical_ids):
            raise AlignmentError("Canonical requirement IDs must be non-empty and unique")
        after = self._counts()
        return {
            "Database": self.settings.mongo_db_name,
            "Collections": {
                "Requirements": self.settings.requirement_deduplication_collection,
                "Evaluation": self.settings.evaluation_criteria_collection,
                "Plans": self.settings.tender_section_plan_collection,
            },
            "BackupPath": str(backup_path.resolve()),
            "RequirementSourceId": str(requirement_source["_id"]),
            "RequirementSelectedId": str(requirement["_id"]),
            "RequirementAction": requirement_action,
            "EvaluationSelectedId": str(evaluation["_id"]),
            "CanonicalRequirementCount": len(canonical),
            "UniqueCanonicalIdCount": len(set(canonical_ids)),
            "EvaluationCriterionCount": len(evaluation.get("Criteria") or []),
            "CountsBefore": before,
            "CountsAfter": after,
            "PlanCollectionUntouched": before["Plans"] == after["Plans"],
        }

    def _counts(self) -> dict[str, int]:
        return {
            "Requirements": self.database[
                self.settings.requirement_deduplication_collection
            ].count_documents(self.target),
            "Evaluation": self.database[
                self.settings.evaluation_criteria_collection
            ].count_documents(self.target),
            "Plans": self.database[self.settings.tender_section_plan_collection].count_documents(
                self.target
            ),
        }

    def _select_evaluation(self) -> dict[str, Any]:
        collection = self.database[self.settings.evaluation_criteria_collection]
        candidates = collection.find(self.target).sort([("UpdatedAt", -1), ("_id", -1)])
        for document in candidates:
            completed = str(document.get("ExtractionStatus", "")).lower() == "completed"
            if completed and _status_valid(document.get("Status")) and document.get("Criteria"):
                return document
        raise AlignmentError("Target scope has no active completed Evaluation Criteria record")

    def _select_requirement_source(self) -> dict[str, Any]:
        collection = self.database[self.settings.requirement_deduplication_collection]
        document = collection.find_one(self.source, sort=[("ModifiedDate", -1), ("_id", -1)])
        if not document or len(extract_deduplicated_requirements(document)) != 13:
            raise AlignmentError("The configured 13-requirement source record was not found")
        return document

    def _align_requirement(
        self, source: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        collection = self.database[self.settings.requirement_deduplication_collection]
        genuine = collection.find_one(
            {**self.target, "IsTestData": {"$ne": True}, "Status": {"$regex": "^(active|completed)$", "$options": "i"}},
            sort=[("ModifiedDate", -1), ("_id", -1)],
        )
        if genuine:
            extract_deduplicated_requirements(genuine)
            return genuine, "reused-genuine"
        identity = {
            **self.target,
            "IsTestData": True,
            "OriginalCompanyId": SOURCE_COMPANY_ID,
            "OriginalTenderId": SOURCE_TENDER_ID,
        }
        existing = collection.find_one(identity)
        if existing:
            extract_deduplicated_requirements(existing)
            return existing, "reused-test-copy"
        clone = self._clone(source, include_final_json=True)
        clone.update(identity)
        result = collection.insert_one(clone)
        clone["_id"] = result.inserted_id
        return clone, "cloned-test-copy"

    @staticmethod
    def _clone(source: dict[str, Any], include_final_json: bool) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        clone = deepcopy(source)
        clone.pop("_id", None)
        clone["CompanyId"] = TARGET_COMPANY_ID
        clone["TenderId"] = TARGET_TENDER_ID
        clone["IsTestData"] = True
        clone["TestDataReason"] = TEST_REASON
        clone["OriginalCompanyId"] = str(source.get("CompanyId"))
        clone["OriginalTenderId"] = str(source.get("TenderId"))
        clone["TestDataCreatedAt"] = now
        clone["TestDataCreatedBy"] = TEST_CREATOR
        _set_existing_dates(clone, now)
        wrappers = ["JsonOutput"] if include_final_json else []
        for name in wrappers:
            wrapper = clone.get(name)
            if isinstance(wrapper, dict):
                if "CompanyId" in wrapper:
                    wrapper["CompanyId"] = TARGET_COMPANY_ID
                if "TenderId" in wrapper:
                    wrapper["TenderId"] = TARGET_TENDER_ID
                _set_existing_dates(wrapper, now)
        return clone

    def _backup(self, documents: dict[str, Any]) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.backup_dir / f"section_planner_smoke_sources_{stamp}.json"
        path.write_text(dumps(documents, indent=2), encoding="utf-8")
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Align Section Planner OpenAI smoke-test sources")
    parser.add_argument("--backup-dir", default="backups/section_planner_smoke")
    args = parser.parse_args()
    settings = Settings.from_env()
    settings.validate()
    client = MongoClient(settings.mongo_uri)
    database = client[settings.mongo_db_name]
    result = SmokeDataAligner(database, settings, Path(args.backup_dir)).run()
    print(dumps(result, indent=2))


if __name__ == "__main__":
    main()
