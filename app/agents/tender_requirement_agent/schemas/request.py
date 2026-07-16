from pydantic import BaseModel, Field, ConfigDict

class RequirementRequest(BaseModel):
    company_id: str = Field(alias="CompanyId")
    tender_id: str = Field(alias="TenderId")
    IsRegenerate: bool 
    UserId: str
    UserName: str
    ProjectId: str
    JwtToken: str