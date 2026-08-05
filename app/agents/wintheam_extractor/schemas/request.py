# app/agents/wintheam_extractor/schemas.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class WinThemeExtractorRequest(BaseModel):
    company_id: str = Field(..., description="Company identifier")
    industry: str = Field(..., description="Industry name")
    cpv_codes: List[str] = Field(
        ...,
        min_length=1,
        description="One or more CPV codes",
    )

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("company_id cannot be empty.")
        return value

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("industry cannot be empty.")
        return value

    @field_validator("cpv_codes")
    @classmethod
    def validate_cpv_codes(cls, value: List[str]) -> List[str]:
        cleaned = []

        for cpv in value:
            cpv = cpv.strip()

            if not cpv:
                raise ValueError("CPV code cannot be empty.")

            cleaned.append(cpv)

        return cleaned
