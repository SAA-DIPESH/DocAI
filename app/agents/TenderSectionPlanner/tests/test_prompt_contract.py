import json
import re
from pathlib import Path

from section_planner.models import (
    DynamicProposalGroupDecision,
    DynamicSectionDecision,
    DynamicSectionPlannerLLMDecision,
    DynamicSubSectionDecision,
)


ROOT = Path(__file__).parents[1]
CONSTITUTION = (ROOT / "Section_Planner_Constitution.md").read_text(encoding="utf-8")
SPECIFICATION = (ROOT / "Section_Planner_Specification.md").read_text(encoding="utf-8")
USER_PROMPT = (ROOT / "Section_Planner_User_Prompt.md").read_text(encoding="utf-8")
ALL_PROMPTS = "\n".join((CONSTITUTION, SPECIFICATION, USER_PROMPT))


def specification_example() -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", SPECIFICATION, re.DOTALL)
    assert match, "Specification must contain its JSON contract"
    return json.loads(match.group(1))


def test_prompts_use_only_requirements_and_evaluation_sources():
    assert "CanonicalRequirementId" in CONSTITUTION
    assert "CriterionId" in CONSTITUTION
    assert "Tender Section Configuration is not an input" in CONSTITUTION
    assert "supplied requirements" in USER_PROMPT
    assert "criterion" in USER_PROMPT


def test_specification_matches_dynamic_structured_output_model():
    example = specification_example()
    assert set(example) == set(DynamicSectionPlannerLLMDecision.model_fields)
    assert set(example["ProposalGroups"][0]) == set(DynamicProposalGroupDecision.model_fields)
    section = example["ProposalGroups"][0]["Sections"][0]
    assert set(section) == set(DynamicSectionDecision.model_fields)
    assert set(section["SubSections"][0]) == set(DynamicSubSectionDecision.model_fields)
    DynamicSectionPlannerLLMDecision.model_validate(example)


def test_llm_contract_contains_dynamic_content_but_no_final_structural_ids():
    serialized = json.dumps(specification_example())
    for required in (
        "GroupName",
        "SectionName",
        "SectionDescription",
        "SubSectionName",
        "SubSectionDescription",
        "CanonicalRequirementIds",
        "EvaluationCriterionIds",
    ):
        assert required in serialized
    for forbidden in (
        "GroupId",
        "SectionId",
        "SubSectionId",
        "Priority",
        "WeightPercent",
        "Dependencies",
        "SourceEvidence",
    ):
        assert forbidden not in serialized


def test_prompts_require_requirement_backed_sections_and_subsections():
    assert "every subsection owns at least one supplied canonical" in CONSTITUTION
    assert "Criteria cannot create hierarchy" in CONSTITUTION
    assert "Assign every requirement once" in USER_PROMPT


def test_prompts_require_exact_source_ids_without_legacy_ids():
    assert "CanonicalRequirementId" in ALL_PROMPTS
    assert "CriterionId" in ALL_PROMPTS
    assert "DeduplicatedRequirementId" not in ALL_PROMPTS
    assert "CR1" not in ALL_PROMPTS


def test_python_owns_ids_validation_hydration_and_persistence():
    assert "Python owns stable final IDs" in CONSTITUTION
    assert "weights/evidence" in CONSTITUTION
    assert "traceability" in CONSTITUTION
