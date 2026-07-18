from pydantic import BaseModel, Field, ConfigDict


class RequirementRequest(BaseModel):
    CompanyId: str
    TenderId: str 
    IsRegenerate : bool
    UserId : str
    UserName : str
    ProjectId : str
    JwtToken : str
