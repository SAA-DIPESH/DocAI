import pytest
from fastapi import HTTPException

import section_planner.api as api_module
from section_planner.api import app
from section_planner.exceptions import ConfigurationError
from section_planner.models import SectionPlannerRequest


def test_terminal_logging_uses_uvicorn_logger():
    assert api_module.terminal_logger.name == "uvicorn.error"


def test_swagger_uses_clean_public_proposal_plan_contract():
    schema = app.openapi()
    operation = schema["paths"]["/section-planner"]["post"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]

    assert response_schema["$ref"].endswith("/ProposalPlanResponse")
    public_fields = schema["components"]["schemas"]["ProposalPlanResponse"][
        "properties"
    ]
    validation_fields = schema["components"]["schemas"]["PublicValidationResult"][
        "properties"
    ]
    assert "LLMMetadata" not in public_fields
    assert "Warnings" not in validation_fields
    assert "Information" not in validation_fields
    assert "BlockingIssues" in validation_fields


@pytest.mark.asyncio
async def test_generation_failure_is_sent_to_enterprise_logger(monkeypatch):
    events = []

    class RecordingLogger:
        def start(self, **kwargs):
            events.append(("start", kwargs))
            return {"tracking": True}

        def end(self, **kwargs):
            events.append(("end", kwargs))

    class FailingService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def execute(self, _request):
            raise ConfigurationError("missing configuration")

    monkeypatch.setattr(api_module, "_request_logger", RecordingLogger)
    monkeypatch.setattr(api_module, "MongoPlannerRepository", object)
    monkeypatch.setattr(api_module, "SectionPlannerService", FailingService)

    request = SectionPlannerRequest.model_validate(
        {
            "CompanyId": "company-1",
            "TenderId": "tender-1",
            "ProjectId": "project-1",
            "UserId": "user-1",
            "UserName": "Test User",
            "IsRegenerate": False,
        }
    )

    with pytest.raises(HTTPException) as captured:
        await api_module.generate_section_plan(request)

    assert captured.value.status_code == 503
    assert events[0][1]["event_type"] == "TenderSectionPlanningStarted"
    assert events[1][1]["event_type"] == "TenderSectionPlanningFailed"
    assert events[1][1]["is_success"] is False
    assert events[1][1]["payload"]["company_id"] == "company-1"
