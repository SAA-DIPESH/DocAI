from typing import Any, TypedDict


class SectionPlannerState(TypedDict, total=False):
    CompanyId: str
    TenderId: str
    IsRegenerate: bool
    UserId: str
    UserName: str
    ProjectId: str
    Status: str
    requirement_record: dict[str, Any]
    evaluation_record: dict[str, Any] | None
    canonical_requirements: list[dict[str, Any]]
    evaluation_criteria: list[dict[str, Any]]
    plan: dict[str, Any]
