import mongomock
import pytest

from section_planner.repository import MongoPlannerRepository
from section_planner.settings import Settings
from .test_section_planner import settings


class Collection:
    def __init__(self):
        self.query = None
        self.sort = None

    def find_one(self, query, sort=None):
        self.query = query
        self.sort = sort
        return {"Status": "active", "ExtractionStatus": "COMPLETED"}


class Database(dict):
    def __missing__(self, key):
        value = Collection()
        self[key] = value
        return value

    def list_collection_names(self):
        return list(self)


def test_evaluation_loader_uses_confirmed_collection_shape_and_active_completed_filter():
    database = Database()
    repository = MongoPlannerRepository(database)

    result = repository.load_evaluation("company-1", "tender-1")

    collection = database["EvaluationCriteria"]
    assert result["ExtractionStatus"] == "COMPLETED"
    assert collection.query["CompanyId"] == "company-1"
    assert collection.query["TenderId"] == "tender-1"
    status_query, extraction_query = collection.query["$and"]
    assert (
        status_query["$or"][0]["Status"]["$regex"]
        == "^(active|regenerating)$"
    )
    assert extraction_query["$or"][0]["ExtractionStatus"]["$regex"] == "^completed$"
    assert collection.sort[0] == ("CompletedAt", -1)


def test_default_requirement_collection_is_actual_agent_collection():
    repository = MongoPlannerRepository(Database(), settings())
    assert repository.requirement_collection == "TenderRequirementDeduplications"


def test_settings_default_requirement_collection(monkeypatch):
    monkeypatch.delenv("REQUIREMENT_DEDUPLICATION_COLLECTION", raising=False)
    assert (
        Settings.from_env().requirement_deduplication_collection
        == "TenderRequirementDeduplications"
    )


def test_requirement_query_accepts_real_active_status_without_merging_collections():
    database = Database()
    repository = MongoPlannerRepository(database, settings())
    repository.load_requirements("company-1", "tender-1")
    collection = database["TenderRequirementDeduplications"]
    assert collection.query["CompanyId"] == "company-1"
    assert collection.query["TenderId"] == "tender-1"
    assert (
        collection.query["$or"][0]["Status"]["$regex"]
        == "^(active|regenerating)$"
    )
    assert "RequirementDeduplication" not in database


def test_source_queries_allow_active_and_regenerating_case_insensitively():
    database = Database()
    repository = MongoPlannerRepository(database, settings())

    repository.load_requirements("company-1", "tender-1", "Regenerating")
    requirement_query = database["TenderRequirementDeduplications"].query
    repository.load_evaluation("company-1", "tender-1", "Regenerating")
    evaluation_query = database["EvaluationCriteria"].query

    assert (
        requirement_query["$or"][0]["Status"]["$regex"]
        == "^(active|regenerating)$"
    )
    assert requirement_query["$or"][0]["Status"]["$options"] == "i"
    evaluation_status = evaluation_query["$and"][0]["$or"][0]["Status"]
    assert evaluation_status["$regex"] == "^(active|regenerating)$"
    assert evaluation_status["$options"] == "i"


@pytest.mark.parametrize("stored_status", ["Regenerating", "regenerating"])
def test_evaluation_loader_matches_both_regenerating_case_variants(stored_status):
    database = mongomock.MongoClient().DocAI
    database.EvaluationCriteria.insert_one(
        {
            "CompanyId": "company-1",
            "TenderId": "tender-1",
            "Status": stored_status,
            "ExtractionStatus": "COMPLETED",
        }
    )
    repository = MongoPlannerRepository(database, settings())

    result = repository.load_evaluation(
        "company-1", "tender-1", "Regenerating"
    )

    assert result is not None
    assert result["Status"] == stored_status


@pytest.mark.parametrize("stored_status", ["Active", "active", "ACTIVE"])
def test_evaluation_loader_matches_all_active_case_variants(stored_status):
    database = mongomock.MongoClient().DocAI
    database.EvaluationCriteria.insert_one(
        {
            "CompanyId": "company-1",
            "TenderId": "tender-1",
            "Status": stored_status,
            "ExtractionStatus": "COMPLETED",
        }
    )
    repository = MongoPlannerRepository(database, settings())

    result = repository.load_evaluation("company-1", "tender-1", "Active")

    assert result is not None
    assert result["Status"] == stored_status


def test_latest_plan_returns_final_json_and_supports_project_filter():
    database = Database()
    collection = database["TenderSectionPlans"]
    collection.find_one = lambda query, sort=None: {"JsonOutput": {"ProposalPlanId": "plan-1"}}
    repository = MongoPlannerRepository(database, settings())

    result = repository.load_latest_plan("company-1", "tender-1", "project-1")

    assert result == {"ProposalPlanId": "plan-1"}


def test_latest_plan_reads_legacy_final_json_during_migration():
    database = Database()
    collection = database["TenderSectionPlans"]
    collection.find_one = lambda query, sort=None: {
        "FinalJson": {"ProposalPlanId": "legacy-plan"}
    }
    repository = MongoPlannerRepository(database, settings())

    result = repository.load_latest_plan("company-1", "tender-1")

    assert result == {"ProposalPlanId": "legacy-plan"}


def test_duplicate_requirement_collections_warn_and_use_only_configured(caplog):
    database = Database()
    database["RequirementDeduplication"] = Collection()
    database["TenderRequirementDeduplications"] = Collection()
    repository = MongoPlannerRepository(database, settings())
    repository.log_collection_selection()
    assert "without merging" in caplog.text
    assert "TenderRequirementDeduplications" in caplog.text


def test_example_env_has_one_unambiguous_requirement_collection_key():
    lines = (settings().constitution_path.parent / ".env.example").read_text(
        encoding="utf-8"
    ).splitlines()
    values = [
        line for line in lines if line.startswith("REQUIREMENT_DEDUPLICATION_COLLECTION=")
    ]
    assert values == [
        "REQUIREMENT_DEDUPLICATION_COLLECTION=TenderRequirementDeduplications"
    ]
