from pydantic import BaseModel, Field, ConfigDict

class RequirementRequest(BaseModel):
    company_id: str = Field(alias="CompanyId")
    tender_id: str = Field(alias="TenderId")
    IsRegenerate: str = Field(alias="IsRegenerate")
    UserId: str
    UserName: str
    ProjectId: str
    JwtToken: str