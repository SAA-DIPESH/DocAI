from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import mongomock
import pytest

from section_planner.exceptions import (
    ConfigurationError,
    InvalidSourceError,
    LLMTimeoutError,
    PlanValidationError,
)
from section_planner.llm import LLMResult
from section_planner.models import (
    DynamicSectionPlannerLLMDecision,
    ProposalPlan,
    ProposalPlanResponse,
    SectionPlannerLLMDecision,
    SectionPlannerRequest,
)
from section_planner.service import SectionPlannerService
from section_planner.repository import MongoPlannerRepository
from section_planner.settings import Settings


ROOT = Path(__file__).parents[1]


def settings(**overrides) -> Settings:
    values = {
        "mongo_uri": "mongodb://localhost:27017",
        "mongo_db_name": "DocAI",
        "requirement_deduplication_collection": "TenderRequirementDeduplications",
        "evaluation_criteria_collection": "EvaluationCriteria",
        "tender_section_plan_collection": "TenderSectionPlans",
        "llm_provider": "openai",
        "openai_api_key": "test-openai-key",
        "openai_model": "gpt-test",
        "openai_timeout_seconds": 10,
        "openai_max_retries": 0,
        "openai_reasoning_effort": "medium",
        "nvidia_api_key": "test-nvidia-key",
        "nvidia_model": "meta/llama-3.3-70b-instruct",
        "nvidia_base_url": "https://integrate.api.nvidia.com/v1",
        "nvidia_timeout_seconds": 10,
        "nvidia_max_retries": 0,
        "nvidia_max_tokens": 8192,
        "nvidia_temperature": 1.0,
        "nvidia_top_p": 1.0,
        "nvidia_enable_thinking": True,
        "nvidia_clear_thinking": False,
        "mistral_api_key": "test-mistral-key",
        "mistral_model": "mistral-large-latest",
        "mistral_base_url": "https://api.mistral.ai/v1",
        "mistral_timeout_seconds": 10,
        "mistral_max_retries": 0,
        "mistral_temperature": 0.2,
        "constitution_path": ROOT / "Section_Planner_Constitution.md",
        "specification_path": ROOT / "Section_Planner_Specification.md",
        "user_prompt_path": ROOT / "Section_Planner_User_Prompt.md",
        "llm_max_input_tokens": 12000,
        "llm_max_output_tokens": 3000,
        "llm_repair_attempts": 1,
    }
    values.update(overrides)
    return Settings(**values)


def request(regenerate: bool = False) -> SectionPlannerRequest:
    return SectionPlannerRequest.model_validate(
        {
            "CompanyId": "company-1",
            "TenderId": "tender-1",
            "IsRegenerate": regenerate,
            "UserId": "user-1",
            "UserName": "Test User",
            "ProjectId": "project-1",
            "JwtToken": "jwt-super-secret",
        }
    )


def test_request_accepts_is_regenerated_and_empty_project_id():
    payload = {
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "IsRegenerated": True,
        "UserId": "user-1",
        "UserName": "Test User",
        "ProjectId": "",
        "JwtToken": "secret",
    }

    parsed = SectionPlannerRequest.model_validate(payload)

    assert parsed.is_regenerate is True
    assert parsed.project_id == ""
    assert "JwtToken" not in parsed.model_dump(by_alias=True)


def configuration() -> dict:
    return {
        "_id": "config-1",
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Sector": "Technology",
        "PlannerConfiguration": {
            "StrictFrameworkOnly": True,
            "AllowDynamicSections": False,
            "UseEvaluationPriority": True,
        },
        "Groups": [
            {
                "GroupId": "G1",
                "GroupName": "Response",
                "Order": 1,
                "Sections": [
                    {
                        "SectionId": "S1",
                        "SectionName": "Technical Solution",
                        "RequirementTypes": ["Technical"],
                        "Dependencies": [],
                        "SubSections": [
                            {
                                "SubSectionId": "SS1",
                                "SubSectionName": "Security Controls",
                                "RequirementTypes": ["Security"],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def requirements() -> dict:
    return {
        "_id": "dedup-1",
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "Completed",
        "Output": {
            "DeduplicatedRequirements": [
                {
                    "CanonicalRequirementId": "DEDUP-001",
                    "CanonicalRequirement": "Describe security controls and certification evidence",
                    "RequirementIds": ["REQ-7", "REQ-9"],
                    "SourceRequirements": [
                        {
                            "RequirementId": "REQ-7",
                            "DocumentId": "DOC-1",
                            "ChunkId": "CHUNK-2",
                            "SourceMongoId": "mongo-7",
                            "RequirementText": "Provide security controls",
                            "RequirementType": "Security",
                            "MandatoryFlag": True,
                            "Priority": "High",
                            "RequirementStrength": "Shall",
                            "Heading": "Security Controls",
                            "PageNumber": 7,
                            "Confidence": 0.98,
                            "IntentResult": {
                                "CapabilityIntent": "Security assurance",
                                "EvidenceSections": ["Certification"],
                                "SemanticAnchors": ["security", "certification"],
                            },
                        }
                    ],
                }
            ]
        },
    }


def evaluation(weight=25) -> dict:
    return {
        "_id": "eval-1",
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "active",
        "ExtractionStatus": "COMPLETED",
        "EvaluationModelDetected": True,
        "Criteria": [
            {
                "CriterionId": "EC-1",
                "Name": "Security controls",
                "Description": "Pass/fail security evidence",
                "PrimaryCategory": "Security",
                "SecondaryCategories": [],
                "ParentCriterionId": None,
                "QuestionReferences": ["Q1"],
                "WeightPercent": weight,
                "MaximumScore": 100,
                "MinimumScore": 50,
                "MinimumPercent": None,
                "PassFail": True,
                "Mandatory": True,
                "PriceScoringFormula": None,
                "SourceEvidence": [{"DocumentId": "DOC-1", "ChunkId": "CHUNK-8"}],
            }
        ],
        "MandatoryConditions": [],
        "OverallScoring": {},
        "Conflicts": [],
        "MissingInformation": [],
        "ReviewFlags": [],
        "RequiresHumanReview": False,
        "Validation": {},
        "SourceDocuments": [{"DocumentId": "DOC-1"}],
    }


def valid_plan(weight=25, plan_status="Generated") -> ProposalPlan:
    criterion = deepcopy(evaluation(weight)["Criteria"][0])
    return ProposalPlan.model_validate(
        {
            "ProposalPlanId": "plan-1",
            "CompanyId": "company-1",
            "TenderId": "tender-1",
            "ProjectId": "project-1",
            "Sector": "Technology",
            "PlanStatus": plan_status,
            "ProposalGroups": [
                {
                    "GroupId": "G1",
                    "GroupName": "Response",
                    "Order": 1,
                    "Sections": [
                        {
                            "SectionId": "S1",
                            "SectionName": "Technical Solution",
                            "SectionDescription": "Plan a source-backed security response.",
                            "Required": True,
                            "Priority": "High",
                            "RequirementIds": ["DEDUP-001"],
                            "EvaluationCriteria": [],
                            "SubSections": [
                                {
                                    "SectionId": "SS1",
                                    "SectionName": "Security Controls",
                                    "SectionDescription": "Plan the security controls and evidence response.",
                                    "Required": True,
                                    "Priority": "High",
                                    "RequirementIds": ["DEDUP-001"],
                                    "EvaluationCriteria": [criterion],
                                    "SubSections": [],
                                    "EvidenceRequired": True,
                                    "CaseStudyRequired": False,
                                    "Dependencies": [],
                                    "AutoCreated": False,
                                    "AutoCreatedReason": None,
                                }
                            ],
                            "EvidenceRequired": True,
                            "CaseStudyRequired": False,
                            "Dependencies": [],
                            "AutoCreated": False,
                            "AutoCreatedReason": None,
                        }
                    ],
                }
            ],
            "MappedRequirementIds": ["DEDUP-001"],
            "UnmappedRequirementIds": [],
            "MappedEvaluationCriterionIds": ["EC-1"],
            "UnmappedEvaluationCriterionIds": [],
            "EvaluationSummary": {
                "EvaluationModelDetected": True,
                "ExtractionStatus": "COMPLETED",
                "OverallScoring": {},
                "MandatoryConditions": [],
                "Conflicts": [],
                "MissingInformation": [],
                "ReviewFlags": [],
                "RequiresHumanReview": False,
                "SourceDocuments": [{"DocumentId": "DOC-1"}],
            },
            "Traceability": {
                "RequirementMappings": [
                    {
                        "CanonicalRequirementId": "DEDUP-001",
                        "CanonicalRequirement": "Describe security controls and certification evidence",
                        "SourceRequirementIds": ["REQ-7", "REQ-9"],
                        "SourceDocumentIds": ["DOC-1"],
                        "SourceChunkIds": ["CHUNK-2"],
                        "SectionId": "S1",
                        "SubSectionId": "SS1",
                    }
                ],
                "EvaluationCriterionMappings": [
                    {
                        "CriterionId": "EC-1",
                        "SectionId": "S1",
                        "SubSectionId": "SS1",
                        "SourceEvidence": criterion["SourceEvidence"],
                    }
                ],
            },
            "Validation": {
                "RequirementCoverageValid": True,
                "EvaluationCriteriaCoverageValid": True,
                "HierarchyValid": True,
                "DependencyValid": True,
                "NoEmptySections": True,
                "NoUnsupportedWeights": True,
                "Issues": [],
            },
        }
    )


def valid_decision() -> SectionPlannerLLMDecision:
    return SectionPlannerLLMDecision.model_validate(
        {
            "Mappings": [
                {
                    "NodeId": "SS1",
                    "CanonicalRequirementIds": ["DEDUP-001"],
                    "EvaluationCriterionIds": ["EC-1"],
                },
            ],
            "UnmappedCanonicalRequirementIds": [],
        }
    )


def valid_dynamic_decision() -> DynamicSectionPlannerLLMDecision:
    return DynamicSectionPlannerLLMDecision.model_validate(
        {
            "ProposalGroups": [
                {
                    "GroupName": "Technical Response",
                    "Sections": [
                        {
                            "SectionName": "Technical Solution",
                            "SectionDescription": "Describe the proposed technical solution.",
                            "SubSections": [
                                {
                                    "SubSectionName": "Security Controls",
                                    "SubSectionDescription": (
                                        "Describe security controls and certification evidence."
                                    ),
                                    "CanonicalRequirementIds": ["DEDUP-001"],
                                    "EvaluationCriterionIds": ["EC-1"],
                                }
                            ],
                        }
                    ],
                }
            ],
            "UnmappedCanonicalRequirementIds": [],
        }
    )


class FakeRepository:
    def __init__(self, *, eval_record=None):
        self.reqs = requirements()
        self.eval_record = evaluation() if eval_record is None else eval_record
        self.saved = None
        self.calls = []

    def load_requirements(self, company_id, tender_id, operational_status):
        self.calls.append(("requirements", company_id, tender_id, operational_status))
        return deepcopy(self.reqs)

    def load_evaluation(self, company_id, tender_id, operational_status):
        self.calls.append(("evaluation", company_id, tender_id, operational_status))
        return deepcopy(self.eval_record)

    def save_plan(self, document, regenerate):
        self.saved = deepcopy(document)
        return deepcopy(document)


class MockLLM:
    def __init__(self, *plans):
        self.plans = list(plans)
        self.calls = []

    async def generate_plan(self, *, instructions, runtime_prompt, output_model):
        self.calls.append((instructions, runtime_prompt))
        result = self.plans.pop(0)
        if isinstance(result, Exception):
            raise result
        return LLMResult(
            plan=result,
            response_id=f"resp-{len(self.calls)}",
            usage={"InputTokens": 100, "OutputTokens": 50, "TotalTokens": 150},
            provider="OpenAI",
            model="gpt-test",
        )

    async def repair_plan(
        self,
        *,
        instructions,
        runtime_prompt,
        previous_output,
        validation_errors,
        output_model,
    ):
        repair_prompt = (
            runtime_prompt
            + "\n[PREVIOUS GENERATED PLAN]\n"
            + str(previous_output)
            + "\n[DETERMINISTIC VALIDATION ERRORS]\n"
            + str(validation_errors)
        )
        return await self.generate_plan(
            instructions=instructions,
            runtime_prompt=repair_prompt,
            output_model=output_model,
        )


async def execute(llm, *, repo=None, app_settings=None, regenerate=False):
    repository = repo or FakeRepository()
    service = SectionPlannerService(
        repository,
        settings=app_settings or settings(),
        llm=llm,
    )
    return await service.execute(request(regenerate)), repository


@pytest.mark.asyncio
async def test_every_success_calls_openai_and_sends_complete_instruction_context():
    llm = MockLLM(valid_dynamic_decision())
    output, repository = await execute(llm)
    assert len(llm.calls) == 1
    instructions, prompt = llm.calls[0]
    assert (ROOT / "Section_Planner_Constitution.md").read_text(encoding="utf-8") in instructions
    assert (ROOT / "Section_Planner_Specification.md").read_text(encoding="utf-8") in instructions
    assert (ROOT / "Section_Planner_User_Prompt.md").read_text(encoding="utf-8") in prompt
    assert "DEDUP-001" in prompt and "EC-1" in prompt
    assert "project-1" not in prompt
    assert "company-1" not in prompt and "tender-1" not in prompt
    assert "TENDER SECTION CONFIGURATION" not in prompt
    assert "ALLOWED NODE CATALOGUE" not in prompt
    assert "jwt-super-secret" not in instructions + prompt
    assert "test-openai-key" not in instructions + prompt
    assert repository.saved is not None
    assert output["LLMMetadata"]["ResponseId"] == "resp-1"
    assert output["ProjectId"] == "project-1"


@pytest.mark.asyncio
async def test_dynamic_hierarchy_never_loads_configuration_and_always_emits_subsections():
    output, repository = await execute(MockLLM(valid_dynamic_decision()))

    assert all(call[0] != "configuration" for call in repository.calls)
    assert "TenderSectionConfigurationId" not in output
    group = output["ProposalGroups"][0]
    section = group["Sections"][0]
    subsection = section["SubSections"][0]
    assert group["GroupId"].startswith("grp-dyn-")
    assert section["SectionId"].startswith("sec-dyn-")
    assert subsection["SectionId"].startswith("sub-dyn-")
    assert subsection["RequirementIds"] == ["DEDUP-001"]


@pytest.mark.asyncio
async def test_public_response_hides_internal_audit_but_mongo_retains_safe_metadata():
    output, _ = await execute(MockLLM(valid_dynamic_decision()))
    database = mongomock.MongoClient().DocAI
    repository = MongoPlannerRepository(database, settings())
    repository.save_plan(output, False)

    persisted = database.TenderSectionPlans.find_one({"ProposalPlanId": output["ProposalPlanId"]})
    assert persisted["JsonOutput"]["LLMMetadata"]["Usage"]["InputTokens"] == 100
    assert "JwtToken" not in repr(persisted)
    assert "test-openai-key" not in repr(persisted)

    public = ProposalPlanResponse.model_validate(persisted["JsonOutput"]).model_dump()
    serialized = repr(public)
    assert "LLMMetadata" not in public
    assert "Usage" not in serialized
    assert "PromptHashes" not in serialized
    assert "ResponseId" not in serialized
    assert "Warnings" not in public["Validation"]
    assert "Information" not in public["Validation"]
    assert "BlockingIssues" in public["Validation"]


@pytest.mark.asyncio
async def test_duplicate_dynamic_requirement_owner_is_repaired_before_persistence():
    invalid = valid_dynamic_decision().model_copy(deep=True)
    duplicate = invalid.ProposalGroups[0].Sections[0].SubSections[0].model_copy(deep=True)
    duplicate.SubSectionName = "Duplicate Security Owner"
    invalid.ProposalGroups[0].Sections[0].SubSections.append(duplicate)

    output, repository = await execute(
        MockLLM(invalid, valid_dynamic_decision())
    )

    assert output["LLMMetadata"]["RepairAttempts"] == 1
    assert repository.saved is not None
    assert len(output["ProposalGroups"][0]["Sections"][0]["SubSections"]) == 1


@pytest.mark.asyncio
async def test_normalized_context_uses_actual_deduplicated_id_and_complete_lineage():
    llm = MockLLM(valid_dynamic_decision())
    await execute(llm)
    prompt = llm.calls[0][1]
    assert '"CanonicalRequirementId":"DEDUP-001"' in prompt
    assert '"EvidenceSections":["Certification"]' in prompt
    assert "SourceMongoId" not in prompt
    assert "SourceRequirements" not in prompt
    assert "RequirementIds" not in prompt
    assert "SourceDocuments" not in prompt
    assert "SourceEvidence" not in prompt
    assert "ChunkId" not in prompt
    assert "CR1" not in prompt


def test_compact_context_sends_only_response_requirements_and_compact_json():
    response = {
        "CanonicalRequirementId": "R1",
        "CanonicalRequirement": "Describe   the\nsolution",
        "RequirementType": "Technical",
        "CapabilityIntents": ["Delivery", "Delivery"],
        "EvidenceSections": ["Method", "Method"],
        "SemanticAnchors": ["API", "API"],
        "MandatoryFlags": [True],
        "Priorities": ["High"],
        "ResponseApplicability": True,
        "SourceRequirements": [{"ChunkId": "secret-lineage"}],
        "RequirementIds": ["REQ-1"],
    }
    non_response = {**response, "CanonicalRequirementId": "R2", "ResponseApplicability": False}

    compact = SectionPlannerService._compact_requirements([response, non_response])
    encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))

    assert [item["CanonicalRequirementId"] for item in compact] == ["R1"]
    assert compact[0]["CanonicalRequirement"] == "Describe the solution"
    assert compact[0]["CapabilityIntent"] == ["Delivery"]
    assert "SourceRequirements" not in encoded and "RequirementIds" not in encoded
    assert "\n" not in encoded and ": " not in encoded

    compact_criteria = SectionPlannerService._compact_evaluation(
        {
            "Criteria": [
                {
                    "CriterionId": "EC-1",
                    "Name": "Quality",
                    "Description": "Technical quality",
                    "PrimaryCategory": "Quality",
                    "WeightPercent": 75,
                    "Mandatory": True,
                    "SourceEvidence": [{"ChunkId": "CHUNK-1"}],
                }
            ],
            "SourceDocuments": [{"DocumentId": "DOC-1"}],
        }
    )
    assert compact_criteria == [
        {
            "CriterionId": "EC-1",
            "Name": "Quality",
            "Description": "Technical quality",
            "PrimaryCategory": "Quality",
            "WeightPercent": 75,
            "Mandatory": True,
        }
    ]


@pytest.mark.asyncio
async def test_identical_dynamic_decision_produces_stable_structural_ids():
    first, _ = await execute(MockLLM(valid_dynamic_decision()))
    second, _ = await execute(MockLLM(valid_dynamic_decision()))

    def ids(plan):
        return [
            (group["GroupId"], section["SectionId"], subsection["SectionId"])
            for group in plan["ProposalGroups"]
            for section in group["Sections"]
            for subsection in section["SubSections"]
        ]

    assert ids(first) == ids(second)


@pytest.mark.asyncio
async def test_token_budget_guard_stops_before_llm_and_persistence():
    repository = FakeRepository()
    llm = MockLLM(valid_dynamic_decision())
    with pytest.raises(InvalidSourceError, match="token budget"):
        await execute(
            llm,
            repo=repository,
            app_settings=settings(llm_max_input_tokens=50),
        )
    assert llm.calls == []
    assert repository.saved is None


@pytest.mark.asyncio
async def test_runtime_never_exceeds_one_repair_attempt():
    invalid = valid_dynamic_decision().model_copy(deep=True)
    invalid.ProposalGroups[0].Sections[0].SubSections[0].CanonicalRequirementIds = [
        "INVENTED"
    ]
    llm = MockLLM(invalid, invalid, invalid)
    with pytest.raises(PlanValidationError):
        await execute(llm, app_settings=settings(llm_repair_attempts=5))
    assert len(llm.calls) == 2


@pytest.mark.asyncio
async def test_missing_source_weight_stays_null_in_context_and_result():
    repo = FakeRepository(eval_record=evaluation(weight=None))
    llm = MockLLM(valid_dynamic_decision())
    output, _ = await execute(llm, repo=repo)
    assert '"WeightPercent":null' in llm.calls[0][1]
    criterion = output["ProposalGroups"][0]["Sections"][0]["SubSections"][0][
        "EvaluationCriteria"
    ][0]
    assert criterion["WeightPercent"] is None


@pytest.mark.asyncio
async def test_invalid_first_result_invokes_repair_and_persists_valid_repair():
    invalid = valid_dynamic_decision().model_copy(deep=True)
    invalid.ProposalGroups[0].Sections[0].SubSections[0].CanonicalRequirementIds = [
        "INVENTED-REQUIREMENT"
    ]
    llm = MockLLM(invalid, valid_dynamic_decision())
    output, repository = await execute(llm)
    assert len(llm.calls) == 2
    assert "[DETERMINISTIC VALIDATION ERRORS]" in llm.calls[1][1]
    assert "Invented CanonicalRequirementIds" in llm.calls[1][1]
    assert repository.saved is not None
    assert output["LLMMetadata"]["RepairAttempts"] == 1
    assert output["LLMMetadata"]["ResponseId"] == "resp-2"


@pytest.mark.asyncio
async def test_second_invalid_result_is_rejected_and_never_persisted():
    invalid = valid_dynamic_decision().model_copy(deep=True)
    invalid.ProposalGroups[0].Sections[0].SubSections[0].CanonicalRequirementIds = [
        "INVENTED-REQUIREMENT"
    ]
    llm = MockLLM(invalid, invalid)
    repository = FakeRepository()
    with pytest.raises(PlanValidationError):
        await execute(llm, repo=repository)
    assert len(llm.calls) == 2
    assert repository.saved is None


@pytest.mark.asyncio
async def test_missing_api_key_is_controlled_and_openai_is_not_bypassed():
    llm = MockLLM(valid_dynamic_decision())
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        await execute(llm, app_settings=settings(openai_api_key=""))
    assert llm.calls == []


def test_missing_mistral_key_is_controlled():
    with pytest.raises(ConfigurationError, match="MISTRAL_API_KEY"):
        settings(llm_provider="mistral", mistral_api_key="").validate()


@pytest.mark.asyncio
async def test_openai_timeout_is_propagated_without_deterministic_fallback():
    llm = MockLLM(LLMTimeoutError("OpenAI request timed out"))
    repository = FakeRepository()
    with pytest.raises(LLMTimeoutError):
        await execute(llm, repo=repository)
    assert len(llm.calls) == 1
    assert repository.saved is None


@pytest.mark.asyncio
async def test_mismatched_tenant_source_is_rejected_before_openai():
    repository = FakeRepository()
    repository.eval_record["CompanyId"] = "company-2"
    llm = MockLLM(valid_dynamic_decision())
    with pytest.raises(InvalidSourceError, match="does not match"):
        await execute(llm, repo=repository)
    assert llm.calls == []


@pytest.mark.asyncio
async def test_missing_evaluation_stops_before_openai_and_persistence():
    repository = FakeRepository(eval_record={})
    llm = MockLLM(valid_dynamic_decision())
    from section_planner.exceptions import SourceNotFoundError

    with pytest.raises(SourceNotFoundError, match="Evaluation Criteria"):
        await execute(llm, repo=repository)
    assert llm.calls == []
    assert repository.saved is None


@pytest.mark.asyncio
@pytest.mark.parametrize("regenerate,status", [(False, "Active"), (True, "Regenerating")])
async def test_operational_status_is_separate_from_gpt_plan_status(regenerate, status):
    repository = FakeRepository()
    output, _ = await execute(
        MockLLM(valid_dynamic_decision()), regenerate=regenerate, repo=repository
    )
    assert output["Status"] == status
    assert output["PlanStatus"] == "Generated"
    assert ("requirements", "company-1", "tender-1", status) in repository.calls
    assert ("evaluation", "company-1", "tender-1", status) in repository.calls


@pytest.mark.asyncio
async def test_prompt_hashes_usage_and_safe_ai_metadata_are_persisted():
    output, _ = await execute(MockLLM(valid_dynamic_decision()))
    metadata = output["LLMMetadata"]
    assert metadata["Provider"] == "OpenAI"
    assert metadata["Model"] == "gpt-test"
    assert metadata["PromptHashes"]["Constitution"]
    assert metadata["PromptHashes"]["Specification"]
    assert metadata["PromptHashes"]["UserPrompt"]
    assert metadata["Usage"] == {"InputTokens": 100, "OutputTokens": 50, "TotalTokens": 150}
    assert "JwtToken" not in repr(output)
