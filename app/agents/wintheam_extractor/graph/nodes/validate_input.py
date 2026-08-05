# app/agents/wintheam_extractor/graph/nodes/validate_input.py

from typing import Dict, Any

from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


def validate_input_node(state: WinThemeExtractorState) -> Dict[str, Any]:
    """
    Validate incoming request before invoking the LLM.

    Checks:
    - company_id is present
    - industry is present
    - at least one CPV code is provided
    """

    errors = []

    company_id = state.get("company_id", "").strip()
    industry = state.get("industry", "").strip()
    cpv_codes = state.get("cpv_codes", [])

    if not company_id:
        errors.append("Missing company_id.")

    if not industry:
        errors.append("Missing industry.")

    if not cpv_codes:
        errors.append("At least one CPV code is required.")

    elif not all(isinstance(code, str) and code.strip() for code in cpv_codes):
        errors.append("All CPV codes must be non-empty strings.")

    if errors:
        return {
            "status": "invalid_input",
            "current_step": "validate_input",
            "errors": errors,
        }

    return {
        "status": "processing",
        "current_step": "validate_input",
        "errors": [],
    }