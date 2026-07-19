from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from typing import Any

from pydantic import BaseModel, Field




class WintheamExtractorResponse(BaseModel):
    company_id: str
    cpv_code: str

    status: str
    current_step: str | None = None

    response: dict[str, Any] | None = None

    validation_status: str | None = None
    validation_feedback: list[str] = Field(default_factory=list)

    retry_count: int = 0

    error: str | None = None

    node_latencies: dict[str, float] = Field(default_factory=dict)
