import pytest

from section_planner.exceptions import InvalidSourceError
from section_planner.service import SectionPlannerService, extract_deduplicated_requirements


def live_shape(count=13):
    return {
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "Active",
        "JsonOutput": {
            "DeduplicationStatus": "COMPLETED",
            "CanonicalRequirements": [
                {
                    "CanonicalRequirementId": f"DEDUP-ACTUAL-{index:03d}",
                    "CanonicalRequirementText": f"Canonical requirement {index}",
                    "RequirementType": "Security",
                    "MandatoryFlag": True,
                    "SourceRequirements": [f"REQ-{index:03d}"],
                    "SourceDocuments": [f"DOC-{index:03d}"],
                    "DuplicateCount": 1,
                }
                for index in range(1, count + 1)
            ],
        },
    }


def test_actual_final_json_canonical_requirements_path_is_extracted():
    items = extract_deduplicated_requirements(live_shape())
    assert len(items) == 13
    assert items[0]["CanonicalRequirementId"] == "DEDUP-ACTUAL-001"


def test_direct_json_output_deduplicated_requirements_path_is_extracted():
    record = {
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "Active",
        "JsonOutput": {
            "DeduplicatedRequirements": [
                {
                    "CanonicalRequirementId": "CR-0001",
                    "CanonicalRequirement": "Describe the proposed service.",
                    "RequirementIds": ["REQ-0001"],
                    "RequirementType": "Technical",
                    "IntentResult": {
                        "CapabilityIntent": "Service delivery",
                        "EvidenceSections": ["Evidence"],
                    },
                }
            ]
        },
    }

    items = extract_deduplicated_requirements(record)
    normalized = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": record}
    )

    assert items[0]["CanonicalRequirementId"] == "CR-0001"
    assert normalized[0]["CanonicalRequirementId"] == "CR-0001"
    assert normalized[0]["CapabilityIntents"] == ["Service delivery"]
    assert normalized[0]["EvidenceSections"] == ["Evidence"]


def test_all_thirteen_live_shape_requirements_normalize_with_lineage():
    state = {"requirement_record": live_shape()}
    result = SectionPlannerService.normalize_canonical_requirements(state)
    assert len(result) == 13
    first = result[0]
    assert first["CanonicalRequirementId"] == "DEDUP-ACTUAL-001"
    assert first["CanonicalRequirement"] == "Canonical requirement 1"
    assert first["RequirementIds"] == ["REQ-001"]
    assert first["SourceDocuments"] == ["DOC-001"]
    assert first["SourceRequirements"][0]["RequirementId"] == "REQ-001"
    assert first["SourceRequirements"][0]["DocumentId"] == "DOC-001"
    assert first["RequirementTypes"] == ["Security"]
    assert first["MandatoryFlags"] == [True]


def test_canonical_field_migration_preserves_id_value_exactly():
    record = live_shape(count=1)
    record["JsonOutput"]["CanonicalRequirements"][0][
        "CanonicalRequirementId"
    ] = "DEDUP-GROUP-0001"

    result = SectionPlannerService.normalize_canonical_requirements(
        {"requirement_record": record}
    )

    assert result[0]["CanonicalRequirementId"] == "DEDUP-GROUP-0001"


def test_removed_deduplicated_requirement_id_field_is_not_accepted():
    record = live_shape(count=1)
    requirement = record["JsonOutput"]["CanonicalRequirements"][0]
    requirement["DeduplicatedRequirementId"] = requirement.pop(
        "CanonicalRequirementId"
    )

    with pytest.raises(InvalidSourceError, match="CanonicalRequirementId"):
        SectionPlannerService.normalize_canonical_requirements(
            {"requirement_record": record}
        )
