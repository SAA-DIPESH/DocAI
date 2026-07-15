from pydantic import BaseModel


class RequirementRequest(BaseModel):
    company_id: str
    tender_id: str
    IsRegenerate : str
    UserId : str
    UserName : str
    ProjectId : str
    JwtToken : str
