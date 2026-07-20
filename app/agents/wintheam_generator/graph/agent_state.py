from typing import TypedDict, Dict, Any, List, Optional, Literal


from typing import TypedDict, Dict, Any, List, Optional, Literal


class WinThemeState(TypedDict, total=False):
    # Initial input
    company_id: str
    industry: str
    cpv_code: str

    # Validation rules
    rules: Dict[str, Any]

    # From extract_win_theme_node
    context: Dict[str, Any]
    anchor_groups: List[Dict[str, Any]]

    # Loop control
    current_anchor_index: int
    current_anchor_group: Optional[Dict[str, Any]]
    next_step: Literal["continue", "end"]

    # From retrieve_evidence_node
    current_evidence: List[Dict[str, Any]]
    retrieval_status: Optional[
        Literal[
            "success",
            "no_evidence",
            "failed",
        ]
    ]

    # From win_theme_generator_node
    current_win_theme: Optional[Dict[str, Any]]

    # Final output
    generated_themes: List[Dict[str, Any]]

    # Validation / warnings
    validation_status: Optional[str]
    warnings: List[str]
    unsupported_claims_removed: List[str]

    # Status / tracking
    status: Literal[
        "pending",
        "success",
        "failed",
        "candidate",
        "insufficient_evidence",
    ]
    current_step: Optional[str]
    error: Optional[str]
    node_latencies: Dict[str, float]
