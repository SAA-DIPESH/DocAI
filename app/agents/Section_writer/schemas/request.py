from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class ProposalGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    company_id: str = Field(
        min_length=1,
        alias="CompanyId",
        validation_alias=AliasChoices("CompanyId", "company_id", "companyId"),
    )
    tender_id: str = Field(
        min_length=1,
        alias="TenderId",
        validation_alias=AliasChoices("TenderId", "tender_id", "tenderId"),
    )
    is_regenerate: bool = Field(
        default=False,
        alias="IsRegenerate",
        validation_alias=AliasChoices("IsRegenerate", "isRegenerate", "is_regenerate"),
    )
    user_id: str = Field(
        min_length=1,
        alias="UserId",
        validation_alias=AliasChoices("UserId", "user_id", "userId"),
    )
    user_name: str = Field(
        min_length=1,
        alias="UserName",
        validation_alias=AliasChoices("UserName", "user_name", "userName"),
    )
    project_id: str = Field(
        alias="ProjectId",
        validation_alias=AliasChoices("ProjectId", "project_id", "projectId"),
    )
    jwt_token: str = Field(
        alias="JwtToken",
        validation_alias=AliasChoices("JwtToken", "jwt_token", "jwtToken"),
    )

    @property
    def isRegenerate(self) -> bool:
        return self.is_regenerate

    @field_validator("company_id", "tender_id", "user_id", "user_name")
    @classmethod
    def reject_blank_or_placeholder(cls, value: str) -> str:
        value = value.strip()
        if value.lower() == "string":
            raise ValueError("Replace the Swagger placeholder with a real value.")
        return value
