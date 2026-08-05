from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from typing import Any

from pydantic import BaseModel, Field




class WinThemeExtractorResponse(BaseModel):
    request_id: str
    status: str

    retrieval_blueprint: Optional[Dict[str, Any]] = None

    validation_status: Optional[str] = None
    validation_feedback: List[str] = Field(default_factory=list)

    retry_count: int

    error: Optional[str] = None

    node_latencies: Dict[str, float] = Field(default_factory=dict)