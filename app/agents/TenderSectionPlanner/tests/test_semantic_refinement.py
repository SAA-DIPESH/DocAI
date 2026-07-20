from copy import deepcopy

from section_planner.assembly import ProposalPlanAssembler
from section_planner.disposition import classify_requirement
from section_planner.models import SectionPlannerLLMDecision
from section_planner.repository import MongoPlannerRepository
from section_planner.validation import PlanValidator


def config() -> dict:
    return {
        "Sector": "Technology",
        "PlannerConfiguration": {
            "AllowDynamicSections": True,
            "StrictFrameworkOnly": False,
            "AutoCreateSubSections": True,
        },
        "Groups": [
            {
                "GroupId": "G1",
                "GroupName": "Technical Solution",
                "Order": 1,
                "Sections": [
                    {
                        "SectionId": "S1",
                        "SectionName": "Technical Approach",
                        "SectionDescription": "Configured technical response description.",
                        "Order": 1,
                        "PriorityWeight": 10,
                        "RequirementTypes": ["Technical", "Security"],
                        "Dependencies": [],
                        "SubSections": [
                            {
                                "SubSectionId": "SS1",
                                "SubSectionName": "Security Controls",
                                "SectionDescription": "Configured security response description.",
                                "Order": 1,
                                "RequirementTypes": ["Security"],
                                "Dependencies": [],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def requirement(
    requirement_id: str,
    text: str,
    requirement_type: str,
    *,
    sources: list[dict] | None = None,
    priorities: list[str] | None = None,
) -> dict:
    item = {
        "CanonicalRequirementId": requirement_id,
        "CanonicalRequirement": text,
        "RequirementIds": [],
        "RequirementTypes": [requirement_type],
        "MandatoryFlags": [],
        "Priorities": priorities or [],
        "RequirementStrengths": [],
        "Headings": [],
        "CapabilityIntents": [],
        "EvidenceSections": [],
        "SemanticAnchors": [],
        "SourceDocuments": [],
        "SourceRequirements": sources or [],
    }
    item.update(classify_requirement(item))
    return item


def criterion(criterion_id: str, name: str, description: str, weight=None) -> dict:
    return {
        "CriterionId": criterion_id,
        "Name": name,
        "Description": description,
        "PrimaryCategory": name,
        "SecondaryCategories": [],
        "ParentCriterionId": None,
        "QuestionReferences": [],
        "WeightPercent": weight,
        "MaximumScore": None,
        "MinimumScore": None,
        "MinimumPercent": None,
        "PassFail": None,
        "Mandatory": None,
        "PriceScoringFormula": None,
        "SourceEvidence": [],
    }


def evaluation(*criteria: dict, conflicts: list[dict] | None = None) -> dict:
    return {
        "EvaluationModelDetected": bool(criteria),
        "ExtractionStatus": "COMPLETED",
        "Criteria": list(criteria),
        "MandatoryConditions": [],
        "OverallScoring": {},
        "Conflicts": conflicts or [],
        "MissingInformation": [],
        "ReviewFlags": [],
        "RequiresHumanReview": False,
        "SourceDocuments": [],
    }


def decision(
    mappings: list[dict] | None = None,
    unmapped: list[str] | None = None,
) -> SectionPlannerLLMDecision:
    return SectionPlannerLLMDecision.model_validate(
        {
            "Mappings": mappings or [],
            "UnmappedCanonicalRequirementIds": unmapped or [],
        }
    )


def mapping(
    node_id: str,
    requirement_ids: list[str],
    criterion_ids: list[str] | None = None,
) -> dict:
    return {
        "NodeId": node_id,
        "CanonicalRequirementIds": requirement_ids,
        "EvaluationCriterionIds": criterion_ids or [],
    }


def assemble(
    llm_decision: SectionPlannerLLMDecision,
    requirements: list[dict],
    evaluation_output: dict,
    *,
    project_id: str = "project-1",
):
    return ProposalPlanAssembler().assemble(
        llm_decision,
        config(),
        requirements,
        evaluation_output,
        company_id="company-1",
        tender_id="tender-1",
        project_id=project_id,
    )


def test_tender_metadata_does_not_create_proposal_section_and_has_disposition():
    metadata = requirement(
        "R1", "The contract value is estimated at GBP 5 million.", "Commercial"
    )
    plan = assemble(decision(), [metadata], evaluation())

    assert plan.ProposalGroups == []
    assert plan.RequirementDispositions[0].Disposition == "TENDER_METADATA"
    assert plan.RequirementDispositions[0].ResponseApplicability is False
    assert plan.Validation.SourceRequirementCoverageValid is True


def test_submission_instruction_remains_traceable_outside_proposal_groups():
    submission = requirement(
        "R1",
        "Suppliers must apply via the e-tendering portal.",
        "Submission",
        sources=[{"RequirementId": "SRC-1", "DocumentId": "DOC-1"}],
    )
    plan = assemble(decision(), [submission], evaluation())

    assert not plan.Traceability.RequirementMappings
    assert plan.NonResponseRequirements[0].Disposition == "SUBMISSION_INSTRUCTION"
    assert plan.NonResponseRequirements[0].SourceRequirementIds == ["SRC-1"]
    assert plan.NonResponseRequirements[0].SourceDocumentIds == ["DOC-1"]


def test_criterion_only_mapping_is_rejected_and_cannot_create_a_node():
    quality = criterion("EC-1", "Quality", "Quality response", 20)
    llm_decision = decision([mapping("S1", [], ["EC-1"])])
    assembler = ProposalPlanAssembler()

    issues = assembler.validate_decisions(
        llm_decision, config(), [], evaluation(quality)
    )
    plan = assemble(llm_decision, [], evaluation(quality))

    assert "Mapping has no canonical requirement: S1" in issues
    assert plan.ProposalGroups == []
    assert plan.MappedEvaluationCriterionIds == []
    assert plan.UnmappedEvaluationCriterionIds == ["EC-1"]


def test_invented_or_dynamic_node_id_is_rejected_even_when_dynamic_flags_are_enabled():
    response = requirement("R1", "Describe the proposed technical solution.", "Technical")
    llm_decision = decision([mapping("dynamic-sub-invented", ["R1"])])

    issues = ProposalPlanAssembler().validate_decisions(
        llm_decision, config(), [response], evaluation()
    )

    assert issues == [
        "NodeId is not in ALLOWED NODE CATALOGUE: dynamic-sub-invented",
        "UnmappedCanonicalRequirementIds must exactly list response-applicable requirements without an owner",
    ]


def test_every_emitted_section_and_subsection_is_requirement_backed():
    response = requirement(
        "R1", "Describe the security controls in the proposed solution.", "Security"
    )
    plan = assemble(decision([mapping("SS1", ["R1"])]), [response], evaluation())

    section = plan.ProposalGroups[0].Sections[0]
    subsection = section.SubSections[0]
    assert section.RequirementIds == ["R1"]
    assert subsection.RequirementIds == ["R1"]
    assert all(
        node.RequirementIds
        for group in plan.ProposalGroups
        for parent in group.Sections
        for node in [parent, *parent.SubSections]
    )
    assert not section.AutoCreated and not subsection.AutoCreated


def test_final_business_values_are_hydrated_from_sources_not_llm():
    response = requirement(
        "R1",
        "Describe the security controls in the proposed solution.",
        "Security",
        priorities=["High"],
    )
    quality = criterion("EC-1", "Security quality", "Assess controls", 27.5)
    plan = assemble(
        decision([mapping("SS1", ["R1"], ["EC-1"])]),
        [response],
        evaluation(quality),
    )

    group = plan.ProposalGroups[0]
    section = group.Sections[0]
    subsection = section.SubSections[0]
    assert (group.GroupId, group.GroupName, group.Order) == (
        "G1",
        "Technical Solution",
        1,
    )
    assert subsection.SectionName == "Security Controls"
    assert subsection.SectionDescription == "Configured security response description."
    assert subsection.Priority == "High"
    assert subsection.EvaluationCriteria[0].WeightPercent == 27.5
    assert plan.Traceability.EvaluationCriterionMappings[0].SubSectionId == "SS1"


def test_all_non_response_sources_produce_no_nodes_and_leave_criteria_unmapped():
    requirements = [
        requirement("R1", "The contract starts on 1 June 2030.", "Timeline"),
        requirement("R2", "Submit through the e-tendering portal.", "Submission"),
    ]
    price = criterion("EC-4", "Price", "Completed price schedule", 30)
    plan = assemble(decision(), requirements, evaluation(price))

    assert plan.ProposalGroups == []
    assert plan.MappedRequirementIds == []
    assert plan.Traceability.RequirementMappings == []
    assert len(plan.NonResponseRequirements) == 2
    assert plan.MappedEvaluationCriterionIds == []
    assert plan.UnmappedEvaluationCriterionIds == ["EC-4"]
    assert plan.PlanStatus == "ValidationRequired"


def test_evidence_and_case_study_flags_are_deterministic_source_derivations():
    response = requirement(
        "R1",
        "Provide evidence, certification and a case study for the proposed solution.",
        "Technical",
    )
    plan = assemble(decision([mapping("S1", ["R1"])]), [response], evaluation())
    section = plan.ProposalGroups[0].Sections[0]

    assert section.EvidenceRequired is True
    assert section.CaseStudyRequired is True
    assert {item.SourceId for item in plan.Traceability.EvidenceRequirementTriggers} == {
        "R1"
    }
    assert {item.SourceId for item in plan.Traceability.CaseStudyTriggers} == {"R1"}


def test_duplicate_lineage_ids_are_normalized_in_first_seen_order():
    sources = [
        {"RequirementId": value, "DocumentId": f"D{index}", "ChunkId": f"C{index}"}
        for index, value in enumerate(["SRC1", "SRC2", "SRC3"], 1)
    ]
    response = requirement(
        "R1",
        "Describe the proposed technical solution.",
        "Technical",
        sources=sources + deepcopy(sources),
    )
    plan = assemble(decision([mapping("S1", ["R1"])]), [response], evaluation())
    trace = plan.Traceability.RequirementMappings[0]

    assert trace.SourceRequirementIds == ["SRC1", "SRC2", "SRC3"]
    assert trace.SourceDocumentIds == ["D1", "D2", "D3"]
    assert trace.SourceChunkIds == ["C1", "C2", "C3"]
    assert any("Duplicate lineage IDs normalized" in item for item in plan.Validation.Warnings)


def test_duplicate_criterion_evidence_is_normalized():
    response = requirement("R1", "Describe the proposed technical solution.", "Technical")
    quality = criterion("EC-1", "Technical quality", "Assess quality")
    quality["SourceEvidence"] = [
        {"DocumentId": "D1", "ChunkId": "C1"},
        {"DocumentId": "D1", "ChunkId": "C1"},
        {"DocumentId": "D1", "ChunkId": "C2"},
    ]
    plan = assemble(
        decision([mapping("S1", ["R1"], ["EC-1"])]),
        [response],
        evaluation(quality),
    )

    evidence = plan.Traceability.EvaluationCriterionMappings[0].SourceEvidence
    assert [(item.DocumentId, item.ChunkId) for item in evidence] == [
        ("D1", "C1"),
        ("D1", "C2"),
    ]


def test_evaluation_conflict_remains_blocking():
    plan = assemble(
        decision(),
        [],
        evaluation(conflicts=[{"ConflictId": "C1", "Description": "Weights conflict"}]),
    )

    assert plan.Validation.BlockingIssues
    assert plan.PlanStatus == "ValidationRequired"


def test_non_empty_project_id_is_preserved_in_plan_and_mongo_wrapper():
    plan = assemble(decision(), [], evaluation(), project_id="PROJECT-123")
    document = plan.model_dump()
    document.update({"Status": "Active", "UserId": "user-1"})

    class Collection:
        inserted = None

        def find_one(self, query, sort=None):
            return None

        def insert_one(self, value):
            self.inserted = value

    collection = Collection()
    MongoPlannerRepository({"TenderSectionPlans": collection}).save_plan(document, False)

    assert plan.ProjectId == "PROJECT-123"
    assert collection.inserted["ProjectId"] == "PROJECT-123"
    assert collection.inserted["JsonOutput"]["ProjectId"] == "PROJECT-123"


def test_validator_rejects_a_forged_requirement_empty_subsection():
    response = requirement(
        "R1", "Describe the security controls in the proposed solution.", "Security"
    )
    source_evaluation = evaluation()
    plan = assemble(decision([mapping("SS1", ["R1"])]), [response], source_evaluation)
    plan.ProposalGroups[0].Sections[0].SubSections[0].RequirementIds = []

    issues = PlanValidator().validate(
        plan,
        config(),
        [response],
        source_evaluation,
        "company-1",
        "tender-1",
    )

    assert "Requirement-empty subsection: SS1" in issues


def test_structural_validator_accepts_valid_source_only_plan():
    response = requirement(
        "R1", "Describe the security controls in the proposed solution.", "Security"
    )
    quality = criterion("EC-1", "Security quality", "Assess controls", 20)
    source_evaluation = evaluation(quality)
    plan = assemble(
        decision([mapping("SS1", ["R1"], ["EC-1"])]),
        [response],
        source_evaluation,
    )

    assert PlanValidator().validate(
        plan,
        config(),
        [response],
        source_evaluation,
        "company-1",
        "tender-1",
    ) == []
