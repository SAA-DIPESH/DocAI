from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from typing import Any

from pydantic import BaseModel, Field





class WinThemeResponse(BaseModel):
    status: str
    current_step: Optional[str] = None
    validation_status: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    generated_themes: List[Dict[str, Any]] = Field(default_factory=list)
    node_latencies: Dict[str, float] = Field(default_factory=dict)