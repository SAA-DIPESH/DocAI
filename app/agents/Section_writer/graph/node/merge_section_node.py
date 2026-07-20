from typing import Any, Dict

from app.agents.Section_writer.schemas.state import ProposalGenerationState,SectionState


def _total_token_usage(*usages: Dict[str, Any]) -> Dict[str, Any]:
    model = ""
    for usage in usages:
        if usage.get("model"):
            model = usage["model"]
            break

    return {
        "input_tokens": sum(
            int(usage.get("input_tokens", 0) or 0)
            for usage in usages
        ),
        "output_tokens": sum(
            int(usage.get("output_tokens", 0) or 0)
            for usage in usages
        ),
        "total_tokens": sum(
            int(usage.get("total_tokens", 0) or 0)
            for usage in usages
        ),
        "model": model,
    }


async def merge_section_node(
    state: SectionState,
) -> Dict[str, Any]:

    section = state["generation_context"]["Section"]

    validation_result = state["validation_result"]

    section_result = {
        "section_id": section.get("SectionId"),
        "section_name": section.get("SectionName"),
        "validation_result": validation_result,
    }

    # If validation failed, don't expect generated content
    if not validation_result["is_valid"]:
        return {
            "section_results": [section_result],
        }

    section_result["generated_content"] = state["generated_content"]

    section_result["compliance_result"] = state["compliance_result"]

    section_result["token_usage"] = {
        "section_writer": state["section_writer_token_usage"],
        "compliance_check": state["compliance_token_usage"],
        "total": _total_token_usage(
            state["section_writer_token_usage"],
            state["compliance_token_usage"],
        ),
    }

    workflow_metadata = {
        **state.get("workflow_metadata", {}),
        "current_node": "merge_section",
        "workflow_status": "Completed",
    }

    return {
        "section_results": [section_result],
        "workflow_metadata": workflow_metadata,
    }
