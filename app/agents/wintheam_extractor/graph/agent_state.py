from typing import Any, Dict, List, Optional, Literal
from typing_extensions import TypedDict


class WinThemeExtractorState(TypedDict):
    # Request
    request_id: str
    company_id: str
    industry: str
    cpv_codes: List[str]

    # Output
    retrieval_blueprint: Optional[Dict[str, Any]]
    raw_llm_response: Optional[str]

    # Validation
    validation_errors: List[str]
    validation_warnings: List[str]

    # Retry
    retry_count: int
    max_retries: int

    # Execution
    current_step: Optional[str]
    status: Literal[
        "pending",
        "processing",
        "completed",
        "failed",
        "invalid_input"
    ]

    errors: List[str]

    # Metrics
    node_latencies: Dict[str, float]