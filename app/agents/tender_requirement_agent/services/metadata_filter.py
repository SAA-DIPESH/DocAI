from typing import Tuple

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementState,
)

# =====================================================
# Metadata Rules
# =====================================================

# Titles that rarely contain requirements
SKIP_TITLES = {
    "contents",
    "table of contents",
    "index",
    "revision history",
    "document control",
    "version history",
    "glossary",
    "abbreviations",
}

# Titles that are likely to contain requirements
POSITIVE_TITLES = {
    "scope",
    "scope of work",
    "technical requirements",
    "functional requirements",
    "eligibility criteria",
    "qualification criteria",
    "deliverables",
    "compliance",
    "evaluation criteria",
    "statement of requirements",
    "specifications",
    "technical specification",
}


def metadata_filter(
    state: TenderRequirementState,
) -> Tuple[int, str]:
    """
    Calculates metadata score.

    Returns:
        score
        reason
    """

    score = 0
    reasons = []

    title = (state.get("heading") or "").strip().lower()

    # ---------------------------------------
    # Negative Rules
    # ---------------------------------------

    if title in SKIP_TITLES:
        score -= 10
        reasons.append(f"Skip title='{title}'")

    # ---------------------------------------
    # Positive Rules
    # ---------------------------------------

    for keyword in POSITIVE_TITLES:
        if keyword in title:
            score += 5
            reasons.append(f"Heading='{title}'")
            break

    if not reasons:
        reasons.append("No metadata indicators")

    return score, " | ".join(reasons)