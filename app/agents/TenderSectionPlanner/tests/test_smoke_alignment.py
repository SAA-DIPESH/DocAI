from copy import deepcopy
from pathlib import Path

import mongomock

from scripts.align_section_planner_smoke_data import (
    SOURCE_COMPANY_ID,
    SOURCE_TENDER_ID,
    TARGET_COMPANY_ID,
    TARGET_TENDER_ID,
    SmokeDataAligner,
)
from .test_section_planner import settings


def canonical_requirements(count):
    return [
        {
            "CanonicalRequirementId": f"CR{index}",
            "CanonicalRequirementText": f"Requirement {index}",
            "RequirementType": "Security",
            "MandatoryFlag": True,
            "SourceRequirements": [f"REQ-{index}"],
            "SourceDocuments": [f"DOC-{index}"],
        }
        for index in range(1, count + 1)
    ]


def source_requirement():
    return {
        "CompanyId": SOURCE_COMPANY_ID,
        "TenderId": SOURCE_TENDER_ID,
        "Status": "Active",
        "CreatedDate": "original-created",
        "ModifiedDate": "original-modified",
        "JsonOutput": {
            "CompanyId": SOURCE_COMPANY_ID,
            "TenderId": SOURCE_TENDER_ID,
            "CanonicalRequirements": canonical_requirements(13),
        },
    }


def evaluation():
    return {
        "CompanyId": TARGET_COMPANY_ID,
        "TenderId": TARGET_TENDER_ID,
        "Status": "active",
        "ExtractionStatus": "COMPLETED",
        "Criteria": [{"CriterionId": "EC-1", "WeightPercent": None}],
    }


def database():
    db = mongomock.MongoClient().DocAI
    app_settings = settings()
    db[app_settings.requirement_deduplication_collection].insert_one(source_requirement())
    db[app_settings.evaluation_criteria_collection].insert_one(evaluation())
    return db


def test_alignment_clones_sources_preserves_lineage_and_never_creates_plan(tmp_path):
    db = database()
    app_settings = settings()
    original = deepcopy(
        db[app_settings.requirement_deduplication_collection].find_one(
            {"CompanyId": SOURCE_COMPANY_ID, "TenderId": SOURCE_TENDER_ID}
        )
    )
    result = SmokeDataAligner(db, app_settings, tmp_path).run()
    clone = db[app_settings.requirement_deduplication_collection].find_one(
        {"CompanyId": TARGET_COMPANY_ID, "TenderId": TARGET_TENDER_ID}
    )

    assert result["RequirementAction"] == "cloned-test-copy"
    assert result["CanonicalRequirementCount"] == 13
    assert result["UniqueCanonicalIdCount"] == 13
    assert result["PlanCollectionUntouched"] is True
    assert Path(result["BackupPath"]).is_file()
    assert [x["CanonicalRequirementId"] for x in clone["JsonOutput"]["CanonicalRequirements"]] == [
        f"CR{index}" for index in range(1, 14)
    ]
    assert clone["JsonOutput"]["CanonicalRequirements"][0]["SourceRequirements"] == ["REQ-1"]
    assert clone["JsonOutput"]["CanonicalRequirements"][0]["SourceDocuments"] == ["DOC-1"]
    assert (
        db[app_settings.requirement_deduplication_collection].find_one({"_id": original["_id"]})
        == original
    )
    assert db[app_settings.tender_section_plan_collection].count_documents({}) == 0


def test_alignment_is_idempotent_and_does_not_modify_evaluation(tmp_path):
    db = database()
    app_settings = settings()
    evaluation_before = deepcopy(db[app_settings.evaluation_criteria_collection].find_one({}))
    aligner = SmokeDataAligner(db, app_settings, tmp_path)
    first = aligner.run()
    second = aligner.run()

    assert first["CountsAfter"] == second["CountsAfter"]
    assert second["RequirementAction"] == "reused-test-copy"
    assert db[app_settings.evaluation_criteria_collection].find_one({}) == evaluation_before


def test_genuine_target_requirement_is_preferred_and_not_overwritten(tmp_path):
    db = database()
    app_settings = settings()
    genuine = source_requirement()
    genuine["CompanyId"] = TARGET_COMPANY_ID
    genuine["TenderId"] = TARGET_TENDER_ID
    genuine["JsonOutput"]["CompanyId"] = TARGET_COMPANY_ID
    genuine["JsonOutput"]["TenderId"] = TARGET_TENDER_ID
    genuine["JsonOutput"]["CanonicalRequirements"] = canonical_requirements(15)
    inserted = db[app_settings.requirement_deduplication_collection].insert_one(genuine)
    before = deepcopy(
        db[app_settings.requirement_deduplication_collection].find_one({"_id": inserted.inserted_id})
    )

    result = SmokeDataAligner(db, app_settings, tmp_path).run()

    assert result["RequirementAction"] == "reused-genuine"
    assert result["CanonicalRequirementCount"] == 15
    assert (
        db[app_settings.requirement_deduplication_collection].find_one({"_id": inserted.inserted_id})
        == before
    )
    assert db[app_settings.requirement_deduplication_collection].count_documents(
        {"CompanyId": TARGET_COMPANY_ID, "TenderId": TARGET_TENDER_ID}
    ) == 1
