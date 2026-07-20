from datetime import datetime

import mongomock
from bson import ObjectId

from section_planner.assembly import ProposalPlanAssembler
from section_planner.disposition import classify_requirement
from section_planner.models import SectionPlannerLLMDecision
from section_planner.repository import MongoPlannerRepository
from section_planner.service import (
    SectionPlannerService,
    extract_deduplicated_requirements,
)
from section_planner.validation import PlanValidator
from .test_section_planner import settings


CURRENT_IDS = ["CR-0001", "CR-0002", "CR-0003"] + [
    f"DEDUP-UNIQUE-{index:04d}" for index in range(1, 23)
]


SPECIAL_REQUIREMENTS = {
    "CR-0003": (
        "The Supplier must perform the assignment with due skill, care and diligence.",
        "Technical Capability",
        ["Technical Capability", "Service Delivery"],
        ["Technical Solution", "Methodology"],
    ),
    "DEDUP-UNIQUE-0008": (
        "Please ensure all costs are included in the Total Cost of Delivery Worksheet.",
        "Pricing",
        ["Commercial"],
        ["Pricing", "Commercial Response"],
    ),
    "DEDUP-UNIQUE-0010": (
        "Please complete Solution Delivery costs for each part of the solution.",
        "Pricing",
        ["Commercial", "Service Delivery"],
        ["Pricing", "Implementation Plan"],
    ),
    "DEDUP-UNIQUE-0011": (
        "Please complete the Rate Card with roles, skills and experience.",
        "Staffing",
        ["Staffing", "Resource Management"],
        ["Resource Plan", "Team"],
    ),
    "DEDUP-UNIQUE-0013": (
        "Answers must be uploaded as a PDF file through the portal.",
        "Submission",
        ["Submission"],
        ["Appendices"],
    ),
    "DEDUP-UNIQUE-0018": (
        "Supplier Registration: how to complete the registration process.",
        "Submission",
        ["Submission"],
        ["Company Overview"],
    ),
    "DEDUP-UNIQUE-0020": (
        "Supplier staff must be properly briefed about their assignment.",
        "Staffing",
        ["Staffing", "Health & Safety"],
        ["Team", "Resource Plan"],
    ),
    "DEDUP-UNIQUE-0021": (
        "Supplier staff must perform with skill, care and diligence.",
        "Non-Functional Requirement",
        ["Functional Capability"],
        ["Standards", "Key Personnel"],
    ),
    "DEDUP-UNIQUE-0022": (
        "The Supplier must replace a removed worker with the required skills.",
        "Staffing",
        ["Staffing", "Service Delivery"],
        ["Team", "Key Personnel"],
    ),
}


def current_requirement_record() -> dict:
    items = []
    for index, requirement_id in enumerate(CURRENT_IDS, 1):
        text, requirement_type, intents, evidence = SPECIAL_REQUIREMENTS.get(
            requirement_id,
            (
                f"Background contractual requirement {requirement_id}.",
                "Contract",
                ["Legal"],
                ["Contract Response"],
            ),
        )
        items.append(
            {
                "CanonicalRequirementId": requirement_id,
                "CanonicalRequirement": text,
                "RequirementIds": [f"REQ-{index:04d}"],
                "RequirementType": requirement_type,
                "IntentResult": {
                    "CapabilityIntent": intents,
                    "EvidenceSections": evidence,
                    "SemanticAnchors": [requirement_id, requirement_type],
                },
            }
        )
    return {
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "Active",
        "JsonOutput": {"DeduplicatedRequirements": items},
        "Output": {
            "DeduplicatedRequirements": [
                {
                    "CanonicalRequirementId": "LEGACY-SHOULD-NOT-WIN",
                    "CanonicalRequirement": "Legacy requirement",
                }
            ]
        },
    }


def empty_evaluation() -> dict:
    return {
        "EvaluationModelDetected": False,
        "ExtractionStatus": "COMPLETED",
        "Criteria": [],
        "MandatoryConditions": [],
        "OverallScoring": {},
        "Conflicts": [],
        "MissingInformation": [],
        "ReviewFlags": [],
        "RequiresHumanReview": False,
        "SourceDocuments": [],
    }


def minimal_configuration() -> dict:
    return {
        "Sector": "Technology",
        "Groups": [
            {
                "GroupId": "group-1",
                "GroupName": "Response",
                "Order": 1,
                "Sections": [
                    {
                        "SectionId": "section-1",
                        "SectionName": "Technical response",
                        "SectionDescription": "Configured response section.",
                        "RequirementTypes": [],
                        "Dependencies": [],
                        "SubSections": [],
                    }
                ],
            }
        ],
    }


def test_current_json_output_shape_has_priority_and_all_25_ids_are_preserved():
    record = current_requirement_record()
    extracted = extract_deduplicated_requirements(record)
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": record}
    )

    assert len(extracted) == len(normalized) == 25
    assert [item["CanonicalRequirementId"] for item in normalized] == CURRENT_IDS
    assert "LEGACY-SHOULD-NOT-WIN" not in {
        item["CanonicalRequirementId"] for item in normalized
    }


def test_current_singular_fields_and_intent_values_are_preserved():
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": current_requirement_record()}
    )
    current = next(item for item in normalized if item["CanonicalRequirementId"] == "CR-0003")

    assert current["CanonicalRequirement"].startswith("The Supplier must perform")
    assert current["RequirementType"] == "Technical Capability"
    assert current["IntentResult"]["CapabilityIntent"] == [
        "Technical Capability",
        "Service Delivery",
    ]
    assert current["CapabilityIntents"] == [
        "Technical Capability",
        "Service Delivery",
    ]
    assert current["EvidenceSections"] == ["Technical Solution", "Methodology"]
    assert current["SemanticAnchors"] == ["CR-0003", "Technical Capability"]


def test_requirement_ids_create_complete_source_lineage_and_dispositions():
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": current_requirement_record()}
    )
    plan = ProposalPlanAssembler().assemble(
        SectionPlannerLLMDecision(Mappings=[], UnmappedCanonicalRequirementIds=[]),
        minimal_configuration(),
        normalized,
        empty_evaluation(),
        company_id="company-1",
        tender_id="tender-1",
        project_id="project-1",
    )

    assert all(item["SourceRequirements"] for item in normalized)
    assert all(
        source.get("RequirementId")
        for item in normalized
        for source in item["SourceRequirements"]
    )
    assert all(item.SourceRequirementIds for item in plan.RequirementDispositions)
    assert plan.RequirementDispositions[0].SourceRequirementIds == ["REQ-0001"]


def test_current_response_examples_are_not_review_or_submission_only():
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": current_requirement_record()}
    )
    by_id = {item["CanonicalRequirementId"]: item for item in normalized}

    for requirement_id in (
        "CR-0003",
        "DEDUP-UNIQUE-0008",
        "DEDUP-UNIQUE-0010",
        "DEDUP-UNIQUE-0011",
        "DEDUP-UNIQUE-0020",
        "DEDUP-UNIQUE-0021",
        "DEDUP-UNIQUE-0022",
    ):
        assert by_id[requirement_id]["ResponseApplicability"] is True
        assert by_id[requirement_id]["Disposition"] != "REVIEW_REQUIRED"
        assert by_id[requirement_id]["Disposition"] != "SUBMISSION_INSTRUCTION"


def test_genuine_portal_and_file_format_mechanics_remain_submission_instructions():
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": current_requirement_record()}
    )
    by_id = {item["CanonicalRequirementId"]: item for item in normalized}

    assert by_id["DEDUP-UNIQUE-0013"]["Disposition"] == "SUBMISSION_INSTRUCTION"
    assert by_id["DEDUP-UNIQUE-0018"]["Disposition"] == "SUBMISSION_INSTRUCTION"


def test_review_required_is_separate_and_makes_source_coverage_incomplete():
    requirement = {
        "CanonicalRequirementId": "REVIEW-1",
        "CanonicalRequirement": "An ambiguous statement with no actionable context.",
        "RequirementIds": ["SOURCE-1"],
        "RequirementType": "",
        "IntentResult": {},
        "RequirementTypes": [],
        "CapabilityIntents": [],
        "EvidenceSections": [],
        "SemanticAnchors": [],
        "SourceRequirements": [{"RequirementId": "SOURCE-1"}],
        "SourceDocuments": [],
    }
    requirement.update(classify_requirement(requirement))
    plan = ProposalPlanAssembler().assemble(
        SectionPlannerLLMDecision(Mappings=[], UnmappedCanonicalRequirementIds=[]),
        minimal_configuration(),
        [requirement],
        empty_evaluation(),
        company_id="company-1",
        tender_id="tender-1",
        project_id="project-1",
    )

    assert requirement["Disposition"] == "REVIEW_REQUIRED"
    assert plan.NonResponseRequirements == []
    assert [item.CanonicalRequirementId for item in plan.ReviewRequiredRequirements] == [
        "REVIEW-1"
    ]
    assert plan.UnmappedRequirementIds == ["REVIEW-1"]
    assert plan.Validation.SourceRequirementCoverageValid is False
    assert plan.PlanStatus == "ValidationRequired"


def test_declared_unmapped_response_is_persistable_but_remains_blocking():
    requirement = {
        "CanonicalRequirementId": "RESPONSE-1",
        "CanonicalRequirement": "Describe an unsupported specialist response.",
        "RequirementIds": ["SOURCE-1"],
        "RequirementType": "Unsupported Specialist Type",
        "IntentResult": {},
        "RequirementTypes": ["Unsupported Specialist Type"],
        "CapabilityIntents": [],
        "EvidenceSections": [],
        "SemanticAnchors": [],
        "SourceRequirements": [{"RequirementId": "SOURCE-1"}],
        "SourceDocuments": [],
    }
    requirement.update(classify_requirement(requirement))
    decision = SectionPlannerLLMDecision(
        Mappings=[], UnmappedCanonicalRequirementIds=["RESPONSE-1"]
    )
    source_evaluation = empty_evaluation()
    configuration = minimal_configuration()
    plan = ProposalPlanAssembler().assemble(
        decision,
        configuration,
        [requirement],
        source_evaluation,
        company_id="company-1",
        tender_id="tender-1",
        project_id="project-1",
    )

    assert requirement["ResponseApplicability"] is True
    assert plan.UnmappedRequirementIds == ["RESPONSE-1"]
    assert plan.Validation.ProposalRequirementCoverageValid is False
    assert plan.PlanStatus == "ValidationRequired"
    assert PlanValidator().validate(
        plan,
        configuration,
        [requirement],
        source_evaluation,
        "company-1",
        "tender-1",
    ) == []


def criterion(criterion_id: str, name: str, weight) -> dict:
    return {
        "CriterionId": criterion_id,
        "Name": name,
        "Description": name,
        "PrimaryCategory": name,
        "WeightPercent": weight,
    }


def test_latest_completed_evaluation_is_selected_with_six_exact_criteria():
    database = mongomock.MongoClient().DocAI
    scope = {"CompanyId": "company-1", "TenderId": "tender-1"}
    database.EvaluationCriteria.insert_many(
        [
            {
                "_id": ObjectId("6a574abbd6c837bf8e373eb1"),
                **scope,
                "Status": "Active",
                "ExtractionStatus": "COMPLETED",
                "UpdatedAt": datetime(2026, 7, 15, 11, 16, 44),
                "CreatedAt": datetime(2026, 7, 15, 8, 54, 19),
                "Criteria": [criterion(f"OLD-{index}", "Old", None) for index in range(4)],
            },
            {
                "_id": ObjectId("6a57766eedf50608f2a3cfa9"),
                **scope,
                "Status": "Regenerating",
                "ExtractionStatus": "completed",
                "CreatedAt": datetime(2026, 7, 15, 12, 0, 46),
                "Criteria": [
                    criterion("EC-001", "Quality", 75),
                    criterion("EC-002", "Price", 20),
                    criterion("EC-003", "Social Value", 5),
                    criterion("EC-004", "Key Participation Requirements", None),
                    criterion("EC-005", "Conflicts of Interest", None),
                    criterion("EC-006", "Minimum Quality Threshold", None),
                ],
            },
        ]
    )
    repository = MongoPlannerRepository(database, settings())

    selected = repository.load_evaluation("company-1", "tender-1", "Active")
    normalized = SectionPlannerService.normalize_evaluation_criteria(
        {"evaluation_record": selected}
    )

    assert str(selected["_id"]) == "6a57766eedf50608f2a3cfa9"
    assert len(normalized["Criteria"]) == 6
    weights = {item["CriterionId"]: item["WeightPercent"] for item in normalized["Criteria"]}
    assert weights == {
        "EC-001": 75,
        "EC-002": 20,
        "EC-003": 5,
        "EC-004": None,
        "EC-005": None,
        "EC-006": None,
    }

    plan = ProposalPlanAssembler().assemble(
        SectionPlannerLLMDecision(Mappings=[], UnmappedCanonicalRequirementIds=[]),
        minimal_configuration(),
        [],
        normalized,
        company_id="company-1",
        tender_id="tender-1",
        project_id="project-1",
    )
    persisted_weights = {
        item.CriterionId: item.WeightPercent for item in plan.EvaluationSummary.Criteria
    }
    assert persisted_weights["EC-001"] == 75
    assert persisted_weights["EC-002"] == 20
    assert persisted_weights["EC-003"] == 5


def test_latest_requirement_source_selects_confirmed_active_record():
    database = mongomock.MongoClient().DocAI
    scope = {"CompanyId": "company-1", "TenderId": "tender-1"}
    common = {
        **scope,
        "CompletedAt": datetime(2026, 7, 18, 13, 13, 32),
        "UpdatedAt": datetime(2026, 7, 18, 13, 13, 32),
        "CreatedAt": datetime(2026, 7, 18, 13, 13, 9),
        "JsonOutput": {"DeduplicatedRequirements": [{}]},
    }
    database.TenderRequirementDeduplications.insert_many(
        [
            {
                **common,
                "_id": ObjectId("6a5b7be5bba0217dcfa58a4a"),
                "Status": "Regenerating",
            },
            {
                **common,
                "_id": ObjectId("6a5b8b248154919e018ee966"),
                "Status": "Active",
            },
        ]
    )
    repository = MongoPlannerRepository(database, settings())

    selected = repository.load_requirements(
        "company-1", "tender-1", "Regenerating"
    )

    assert str(selected["_id"]) == "6a5b8b248154919e018ee966"
