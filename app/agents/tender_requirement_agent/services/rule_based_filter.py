from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementState,
)

from app.agents.tender_requirement_agent.services.metadata_filter import (
    metadata_filter,
)

from app.agents.tender_requirement_agent.services.content_filter import (
    content_filter,
)

# =====================================================
# Thresholds
# =====================================================

HIGH_CONFIDENCE_THRESHOLD = 12
MEDIUM_CONFIDENCE_THRESHOLD = 6


def rule_based_filter(
    state: TenderRequirementState,
):
    """
    Combines metadata and content scores to determine whether
    the chunk should be processed by the LLM.

    Returns:
        {
            should_process,
            filter_score,
            filter_confidence,
            filter_reason
        }
    """

    # =====================================================
    # Metadata Score
    # =====================================================

    metadata_score, metadata_reason = metadata_filter(state)

    # =====================================================
    # Content Score
    # =====================================================

    content_score, content_reason = content_filter(
        state.get("chunk_text", "")
    )

    # =====================================================
    # Total Score
    # =====================================================

    total_score = metadata_score + content_score

    # =====================================================
    # Confidence
    # =====================================================

    if total_score >= HIGH_CONFIDENCE_THRESHOLD:
        confidence = "HIGH"
        should_process = True

    elif total_score >= MEDIUM_CONFIDENCE_THRESHOLD:
        confidence = "MEDIUM"
        should_process = True

    else:
        confidence = "LOW"
        should_process = False

    # =====================================================
    # Build Reason
    # =====================================================

    reasons = []

    if metadata_reason:
        reasons.append(f"Metadata: {metadata_reason}")

    if content_reason:
        reasons.append(f"Content: {content_reason}")

    # =====================================================
    # Return State Updates
    # =====================================================

    return {
        "filter_score": total_score,
        "filter_confidence": confidence,
        "should_process": should_process,
        "filter_reason": " | ".join(reasons),
    }