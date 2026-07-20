from typing import Dict, Any
from app.agents.Section_writer.schemas.state import ProposalGenerationState,SectionState






async def validate_context_node(
    state: SectionState,
) -> Dict[str, Any]:

    context = state.get("generation_context", {})

    section = context.get("Section")
    win_themes = context.get("WinThemes", [])

    warnings = []
    errors = []

    # -----------------------------
    # Mandatory validations
    # -----------------------------

    if section is None:
        errors.append("Section not found.")

    requirements = section.get("RequirementIds", [])
    if not requirements:
        errors.append("No requirements found.")

    evidence = section.get("EvidenceSummary", [])
    # if not evidence:
    #     errors.append("Evidence summary missing.")
    if not evidence:
        warnings.append(
        "Evidence summary missing. Proposal will be generated with limited confidence."
    )

    # -----------------------------
    # Optional validations
    # -----------------------------

    if not win_themes:
        warnings.append("No win themes available.")

    if section.get("CaseStudyRequired", False):

        case_studies = [
            item
            for item in evidence
            if item.get("EvidenceCategory") == "CaseStudy"
        ]

        if not case_studies:
            warnings.append(
                "Section requires case studies but none were found."
            )

    if section.get("SubSections") is None:
        warnings.append("SubSections missing. Using empty list.")
        section["SubSections"] = []

    if section.get("GroupName") is None:
        warnings.append("GroupName missing.")

    # -----------------------------
    # Validation Result
    # -----------------------------

    validation_result = {
        "is_valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors
    }

    workflow = state.get("workflow_metadata", {})

    workflow["current_node"] = "validate_context"

    workflow["workflow_status"] = "Completed"

    return {
        "validation_result": validation_result,
        "workflow_metadata": workflow
    }
