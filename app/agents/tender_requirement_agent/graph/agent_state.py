from typing import Any, Dict, List, Literal, Optional, TypedDict


class Requirement(TypedDict, total=False):
    requirement_id: str
    requirement_text: str
    intent: str
    intent_reason: str
    evidence_section: Optional[str]
    status: Literal["pending", "completed", "failed"]
    error: Optional[str]


class TenderRequirementState(TypedDict, total=False):
    # =========================================================
    # Tender Metadata
    # =========================================================
    tender_id: str
    company_id: str
    user_id: str
    user_name: str
    status: str
    document_id: str
    chunk_id: str
    source_document: str
    page_number: Optional[int]
    heading: Optional[str]

    # =========================================================
    # Chunk Data
    # =========================================================
    chunk_text: str

    # =========================================================
    # Master Data
    # =========================================================
    capability_intent_taxonomy: List[Dict[str, Any]]
    company_evidence_sections: List[Dict[str, Any]]

    # =========================================================
    # Requirement Detection
    # =========================================================
    detection_result: int
    requirements: List[Requirement]

    # =========================================================
    # Processing Result
    # =========================================================
    saved_requirement_ids: List[str]
    failed_requirement_ids: List[str]

    # =========================================================
    # Workflow Status
    # =========================================================
    workflow_status: Literal[
        "pending",
        "processing",
        "completed",
        "failed",
    ]

    current_step: str
    next_step: str

    # =========================================================
    # Error Handling
    # =========================================================
    error: Optional[str]

    # =========================================================
    # Performance
    # =========================================================
    node_latencies: Dict[str, float]
    total_processing_time: float