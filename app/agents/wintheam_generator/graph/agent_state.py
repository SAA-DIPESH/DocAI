from typing import Any, Dict, List, Literal, Optional, TypedDict


# ======================================================
# Models
# ======================================================

class AnchorGroup(TypedDict, total=False):
    anchor: str
    description: str
    requirements: List[Dict[str, Any]]
    priority: int


class Evidence(TypedDict, total=False):
    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str
    page_number: int
    metadata: Dict[str, Any]


class WinTheme(TypedDict, total=False):
    anchor: str
    title: str
    description: str
    supporting_evidence: List[Evidence]
    confidence: float
    reasoning: Optional[str]


# ======================================================
# State
# ======================================================

class WinThemeState(TypedDict, total=False):
    # ======================================================
    # Request
    # ======================================================

    request_id: str
    company_id: str
    industry: str
    cpv_codes: List[str]

    # ======================================================
    # Validation Rules
    # ======================================================

    rules: Dict[str, Any]

    # ======================================================
    # Retrieval Blueprint
    # ======================================================

    context: Dict[str, Any]
    anchor_groups: List[AnchorGroup]

    # ======================================================
    # Anchor Processing
    # ======================================================

    current_anchor_index: int
    current_anchor_group: Optional[AnchorGroup]

    next_step: Literal[
        "continue",
        "end",
    ]

    # ======================================================
    # Evidence Retrieval
    # ======================================================

    current_evidence: List[Evidence]

    retrieval_status: Optional[
        Literal[
            "success",
            "no_evidence",
            "failed",
        ]
    ]

    retrieved_chunks_count: int
    reranked_chunks_count: int

    # ======================================================
    # Win Theme Generation
    # ======================================================

    current_win_theme: Optional[WinTheme]

    # ======================================================
    # Final Output
    # ======================================================

    generated_themes: List[WinTheme]

    # ======================================================
    # Validation
    # ======================================================

    validation_status: Optional[
        Literal[
            "passed",
            "warning",
            "failed",
        ]
    ]

    warnings: List[str]
    unsupported_claims_removed: List[str]

    # ======================================================
    # Execution
    # ======================================================

    status: Literal[
        "pending",
        "running",
        "success",
        "failed",
        "insufficient_evidence",
    ]

    current_step: Optional[str]
    error: Optional[str]

    node_latencies: Dict[str, float]