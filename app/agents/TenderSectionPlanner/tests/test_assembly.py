from section_planner.assembly import ProposalPlanAssembler, build_allowed_node_catalogue
from section_planner.models import RequirementNodeMapping, SectionPlannerLLMDecision
from .test_section_planner import configuration, evaluation, requirements, valid_decision


def inputs():
    from section_planner.service import SectionPlannerService

    state = {"requirement_record": requirements(), "evaluation_record": evaluation()}
    return (
        configuration(),
        SectionPlannerService.normalize_canonical_requirements(state),
        SectionPlannerService.normalize_evaluation_criteria(state),
    )


def test_python_assembles_all_structural_fields_and_exact_weight():
    config, requirement_items, evaluation_output = inputs()
    assembler = ProposalPlanAssembler()
    decision = valid_decision()

    plan = assembler.assemble(
        decision,
        config,
        requirement_items,
        evaluation_output,
        company_id="company-1",
        tender_id="tender-1",
        project_id="project-1",
    )

    group = plan.ProposalGroups[0]
    section = group.Sections[0]
    subsection = section.SubSections[0]
    assert (group.GroupId, group.GroupName, group.Order) == ("G1", "Response", 1)
    assert (section.SectionId, section.SectionName, section.Dependencies) == (
        "S1",
        "Technical Solution",
        [],
    )
    assert (subsection.SectionId, subsection.SectionName) == (
        "SS1",
        "Security Controls",
    )
    assert subsection.EvaluationCriteria[0].WeightPercent == 25
    assert section.RequirementIds == ["DEDUP-001"]
    assert plan.Traceability.RequirementMappings[0].SubSectionId == "SS1"


def test_invented_node_id_is_rejected_before_assembly():
    config, requirement_items, evaluation_output = inputs()
    decision = valid_decision().model_copy(deep=True)
    decision.Mappings[0].NodeId = "invented-id"

    issues = ProposalPlanAssembler().validate_decisions(
        decision, config, requirement_items, evaluation_output
    )

    assert "NodeId is not in ALLOWED NODE CATALOGUE: invented-id" in issues


def test_decision_schema_has_no_structural_name_order_or_dependency_fields():
    node_fields = set(SectionPlannerLLMDecision.model_fields)
    nested_fields = set(RequirementNodeMapping.model_fields)
    forbidden = {
        "GroupId",
        "GroupName",
        "Order",
        "SectionId",
        "SectionName",
        "SubSectionId",
        "SubSectionName",
        "Dependencies",
        "ParentSectionId",
    }
    assert not node_fields.intersection(forbidden)
    assert not nested_fields.intersection(forbidden)
    assert nested_fields == {
        "NodeId",
        "CanonicalRequirementIds",
        "EvaluationCriterionIds",
    }


def test_allowed_catalogue_is_derived_from_configuration():
    catalogue = build_allowed_node_catalogue(configuration())
    assert [item["NodeId"] for item in catalogue] == ["S1", "SS1"]
    assert catalogue[1]["ParentSectionId"] == "S1"
