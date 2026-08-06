from typing import Dict, List, Literal, Optional, TypedDict


# =========================================================
# Requirement
# =========================================================

class Requirement(TypedDict, total=False):
    # Requirement Identification
    RequirementId: str

    # Requirement Extraction
    RequirementText: str
    RequirementType: str

    RequirementStrength: Literal[
        "Mandatory",
        "Conditional",
        "Optional",
        "Informational",
    ]

    MandatoryFlag: bool

    Priority: Literal[
        "High",
        "Medium",
        "Low",
    ]

    Confidence: float

    # Intent Mapping
    CapabilityIntent: List[str]
    EvidenceSections: List[str]
    SemanticAnchors: List[str]
    IntentConfidence: float


# =========================================================
# Token Usage
# =========================================================

class ModelTokenUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class TokenUsage(TypedDict):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    models: Dict[str, ModelTokenUsage]


# =========================================================
# Batch Input (NEW)
# =========================================================

class ChunkState(TypedDict, total=False):
    document_id: str
    chunk_id: str
    source_document: str
    page_number: Optional[int]
    heading: Optional[str]

    chunk_text: str

    should_process: bool
    filter_score: int
    filter_reason: str
    filter_confidence: Literal["HIGH", "MEDIUM", "LOW"]

    detection_result: bool
    requirements: List[Requirement]

    saved_requirement_ids: List[str]
    failed_requirement_ids: List[str]

    error: Optional[str]


# =========================================================
# Agent State
# =========================================================

class TenderRequirementBatchState(TypedDict, total=False):

    tender_id: str
    company_id: str
    user_id: str
    user_name: str
    status: str

    chunks: List[ChunkState]

    workflow_status: Literal[
        "pending",
        "processing",
        "completed",
        "failed",
    ]

    current_step: str

    token_usage: TokenUsage

    node_latencies: Dict[str, float]

    total_processing_time: float

    error: Optional[str]