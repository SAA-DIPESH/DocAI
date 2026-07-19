import pytest

from section_planner.models import DynamicSectionPlannerLLMDecision, SectionPlannerLLMDecision
from section_planner.service import SectionPlannerService
from .test_section_planner import MockLLM, execute, valid_dynamic_decision


def requirement(requirement_id: str, response: bool = True) -> dict:
    return {
        "CanonicalRequirementId": requirement_id,
        "ResponseApplicability": response,
    }


def normalize(payload: dict, requirements: list[dict]) -> SectionPlannerLLMDecision:
    return SectionPlannerService._normalize_llm_decision(
        SectionPlannerLLMDecision.model_validate(payload), requirements
    )


def test_duplicate_node_mappings_are_merged_in_first_seen_order():
    result = normalize(
        {
            "Mappings": [
                {
                    "NodeId": "sec-004",
                    "CanonicalRequirementIds": ["R1"],
                    "EvaluationCriterionIds": ["EC-1"],
                },
                {
                    "NodeId": "sec-004",
                    "CanonicalRequirementIds": ["R2"],
                    "EvaluationCriterionIds": ["EC-2"],
                },
            ],
            "UnmappedCanonicalRequirementIds": [],
        },
        [requirement("R1"), requirement("R2")],
    )

    assert [item.NodeId for item in result.Mappings] == ["sec-004"]
    assert result.Mappings[0].CanonicalRequirementIds == ["R1", "R2"]
    assert result.Mappings[0].EvaluationCriterionIds == ["EC-1", "EC-2"]


def test_duplicate_requirement_and_criterion_ids_are_deduplicated():
    result = normalize(
        {
            "Mappings": [
                {
                    "NodeId": "sec-004",
                    "CanonicalRequirementIds": ["R2", "R1", "R2"],
                    "EvaluationCriterionIds": ["EC-2", "EC-1", "EC-2"],
                }
            ],
            "UnmappedCanonicalRequirementIds": [],
        },
        [requirement("R1"), requirement("R2")],
    )

    assert result.Mappings[0].CanonicalRequirementIds == ["R2", "R1"]
    assert result.Mappings[0].EvaluationCriterionIds == ["EC-2", "EC-1"]


def test_unmapped_ids_are_reconciled_in_source_order():
    result = normalize(
        {
            "Mappings": [
                {
                    "NodeId": "sec-004",
                    "CanonicalRequirementIds": ["R2"],
                    "EvaluationCriterionIds": [],
                }
            ],
            "UnmappedCanonicalRequirementIds": ["R2"],
        },
        [requirement("R1"), requirement("R2"), requirement("R3")],
    )

    assert result.UnmappedCanonicalRequirementIds == ["R1", "R3"]


def test_unknown_unmapped_id_is_preserved_for_validator_rejection():
    result = normalize(
        {"Mappings": [], "UnmappedCanonicalRequirementIds": ["INVENTED"]},
        [requirement("R1")],
    )

    assert result.UnmappedCanonicalRequirementIds == ["R1", "INVENTED"]


def test_different_nodes_are_not_merged():
    result = normalize(
        {
            "Mappings": [
                {
                    "NodeId": "sec-004",
                    "CanonicalRequirementIds": ["R1"],
                    "EvaluationCriterionIds": [],
                },
                {
                    "NodeId": "sec-005",
                    "CanonicalRequirementIds": ["R2"],
                    "EvaluationCriterionIds": [],
                },
            ],
            "UnmappedCanonicalRequirementIds": [],
        },
        [requirement("R1"), requirement("R2")],
    )

    assert [item.NodeId for item in result.Mappings] == ["sec-004", "sec-005"]


def test_dynamic_known_criterion_is_kept_only_on_first_seen_subsection():
    payload = valid_dynamic_decision().model_dump()
    second = dict(payload["ProposalGroups"][0]["Sections"][0]["SubSections"][0])
    second["SubSectionName"] = "Second Owner"
    second["CanonicalRequirementIds"] = ["R2"]
    payload["ProposalGroups"][0]["Sections"][0]["SubSections"].append(second)

    result = SectionPlannerService._normalize_dynamic_decision(
        DynamicSectionPlannerLLMDecision.model_validate(payload),
        [requirement("DEDUP-001"), requirement("R2")],
        {"Criteria": [{"CriterionId": "EC-1"}]},
    )

    subsections = result.ProposalGroups[0].Sections[0].SubSections
    assert subsections[0].EvaluationCriterionIds == ["EC-1"]
    assert subsections[1].EvaluationCriterionIds == []


def test_dynamic_unknown_criterion_is_preserved_for_validator_rejection():
    decision = valid_dynamic_decision().model_copy(deep=True)
    decision.ProposalGroups[0].Sections[0].SubSections[0].EvaluationCriterionIds = [
        "UNKNOWN-EC"
    ]

    result = SectionPlannerService._normalize_dynamic_decision(
        decision,
        [requirement("DEDUP-001")],
        {"Criteria": [{"CriterionId": "EC-1"}]},
    )

    assert (
        result.ProposalGroups[0].Sections[0].SubSections[0].EvaluationCriterionIds
        == ["UNKNOWN-EC"]
    )


def test_social_value_criterion_selects_explicitly_related_owner():
    payload = valid_dynamic_decision().model_dump()
    first = payload["ProposalGroups"][0]["Sections"][0]["SubSections"][0]
    first["SubSectionName"] = "Commercial Terms"
    first["CanonicalRequirementIds"] = ["R1"]
    first["EvaluationCriterionIds"] = ["EC-SV"]
    second = dict(first)
    second["SubSectionName"] = "Social Value Delivery"
    second["SubSectionDescription"] = "Describe measurable social value delivery."
    second["CanonicalRequirementIds"] = ["R2"]
    payload["ProposalGroups"][0]["Sections"][0]["SubSections"].append(second)

    result = SectionPlannerService._normalize_dynamic_decision(
        DynamicSectionPlannerLLMDecision.model_validate(payload),
        [requirement("R1"), requirement("R2")],
        {
            "Criteria": [
                {
                    "CriterionId": "EC-SV",
                    "Name": "Social Value",
                    "Description": "Social value commitments",
                }
            ]
        },
    )

    subsections = result.ProposalGroups[0].Sections[0].SubSections
    assert subsections[0].EvaluationCriterionIds == []
    assert subsections[1].EvaluationCriterionIds == ["EC-SV"]


@pytest.mark.asyncio
async def test_initial_llm_result_is_normalized_before_validation():
    decision = valid_dynamic_decision().model_copy(deep=True)
    decision.UnmappedCanonicalRequirementIds = ["DEDUP-001"]

    output, _ = await execute(MockLLM(decision))

    assert output["MappedRequirementIds"] == ["DEDUP-001"]
    assert output["LLMMetadata"]["RepairAttempts"] == 0


@pytest.mark.asyncio
async def test_repair_llm_result_is_also_normalized():
    invalid = valid_dynamic_decision().model_copy(deep=True)
    invalid.ProposalGroups[0].Sections[0].SubSections[0].CanonicalRequirementIds = [
        "INVENTED"
    ]
    repaired = valid_dynamic_decision().model_copy(deep=True)
    repaired.UnmappedCanonicalRequirementIds = ["DEDUP-001"]

    output, _ = await execute(MockLLM(invalid, repaired))

    assert output["MappedRequirementIds"] == ["DEDUP-001"]
    assert output["LLMMetadata"]["RepairAttempts"] == 1
