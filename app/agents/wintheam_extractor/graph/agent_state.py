from typing import Any, Dict, List, Optional, TypedDict

class WintheamState(TypedDict):
    request_id: str
    company_id: str
    industry: str
    cpv_code: str

    response: Optional[Dict[str, Any]]
    raw_llm_response: Optional[str]

    validation_status: Optional[str]
    validation_feedback: Optional[List[str]]

    retry_count: int
    max_retries: int

    current_step: Optional[str]
    status: Optional[str]
    error: Optional[str]

    node_latencies: Dict[str, float]