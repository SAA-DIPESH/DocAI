from typing import Optional

from pydantic import BaseModel, Field

class SourceId(BaseModel):
    sourceIdType: str
    id: str


class Cost(BaseModel):
    currency: str
    value: float


class TokenUsageRequest(BaseModel):
    applicationName: str
    sourceIds: list[SourceId] = Field(default_factory=list)
    runId: str
    userId: str
    purpose: str
    method: str
    agentName: str
    usageType: str
    inputToken: int
    outputToken: int
    totalTokens: int
    model: str
    duration: int
    cost: Cost
    companyId: Optional[str] = None
    tenderId: Optional[str] = None
    projectId: Optional[str] = None
