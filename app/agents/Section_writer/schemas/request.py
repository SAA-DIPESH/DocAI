from typing import Optional

from pydantic import BaseModel


class ProposalGenerationRequest(BaseModel):
    company_id: str
    tender_id: str
    user_id: str
    isRegenerate: bool = False
    jwt_token: Optional[str] = None
