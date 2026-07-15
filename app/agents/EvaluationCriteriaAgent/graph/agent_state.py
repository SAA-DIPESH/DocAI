"""State contract for the Evaluation Criteria workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class EvaluationCriteriaAgentState(TypedDict, total=False):
    company_id: str
    tender_id: str
    evidence_pack: dict[str, Any]
    llm_input: dict[str, Any]
    final_output: dict[str, Any]
