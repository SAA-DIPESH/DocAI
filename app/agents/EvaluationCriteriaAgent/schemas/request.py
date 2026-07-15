"""Public request schema."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationCriteriaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    company_id: str = Field(
        min_length=1,
        alias="CompanyId",
        examples=["6a45059ff419103201431533"],
    )
    tender_id: str = Field(
        min_length=1,
        alias="TenderId",
        examples=["6a4506d2f4191032014315fd"],
    )
    is_regenerated: bool = Field(alias="IsRegenerated", examples=[False])
    user_name: str = Field(min_length=1, alias="UserName", examples=["Jane Doe"])
    user_id: str = Field(min_length=1, alias="UserId", examples=["user-id"])
    project_id: str = Field(alias="ProjectId", examples=[""])
    jwt_token: str = Field(alias="JwtToken", examples=[""])

    @field_validator("company_id", "tender_id")
    @classmethod
    def reject_swagger_placeholder(cls, value: str) -> str:
        value = value.strip()
        if value.lower() == "string":
            raise ValueError("Replace the Swagger placeholder with a real ID.")
        return value
