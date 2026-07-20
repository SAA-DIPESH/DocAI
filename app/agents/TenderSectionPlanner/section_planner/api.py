import logging
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.infrastructure.logger import Logging

from .exceptions import (
    ConfigurationError,
    InvalidSourceError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    PersistenceError,
    PlanValidationError,
    SourceNotFoundError,
    StructuredOutputError,
)
from .models import ProposalPlanResponse, SectionPlannerRequest
from .repository import MongoPlannerRepository
from .service import SectionPlannerService
from .settings import Settings

terminal_logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/section-planner", tags=["Section Planner"])


def _request_logger() -> Logging:
    return Logging(
        agent_name=os.getenv("SECTION_PLANNER_AGENT_NAME", "Tender Section Planner"),
        source_module="tender_section_planner_api",
    )


def _request_payload(request: SectionPlannerRequest) -> dict[str, object]:
    return {
        "company_id": request.company_id,
        "tender_id": request.tender_id,
        "project_id": request.project_id,
        "is_regenerate": request.is_regenerate,
        "user_id": request.user_id,
    }


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ConfigurationError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (SourceNotFoundError, InvalidSourceError)):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, PlanValidationError):
        return HTTPException(
            status_code=422,
            detail={"message": str(exc), "issues": exc.issues},
        )
    if isinstance(exc, LLMTimeoutError):
        return HTTPException(status_code=504, detail=str(exc))
    if isinstance(exc, LLMRateLimitError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (StructuredOutputError, LLMServiceError)):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, PersistenceError):
        return HTTPException(status_code=500, detail=str(exc))
    return HTTPException(status_code=500, detail="Section planning failed")


@router.post("", response_model=ProposalPlanResponse)
async def generate_section_plan(request: SectionPlannerRequest) -> ProposalPlanResponse:
    event_logger = _request_logger()
    tracking_token = event_logger.start(
        message="Tender section planning started",
        event_type="TenderSectionPlanningStarted",
    )
    terminal_logger.info(
        "Section planning started | company_id=%s tender_id=%s project_id=%s regenerate=%s",
        request.company_id,
        request.tender_id,
        request.project_id,
        request.is_regenerate,
    )
    try:
        persisted = await SectionPlannerService(MongoPlannerRepository()).execute(request)
        response = ProposalPlanResponse.model_validate(persisted)
        event_logger.end(
            tracking_token=tracking_token,
            is_success=True,
            message="Tender section planning completed",
            event_type="TenderSectionPlanningCompleted",
            payload={
                **_request_payload(request),
                "proposal_plan_id": response.ProposalPlanId,
                "plan_status": response.PlanStatus,
                "proposal_group_count": len(response.ProposalGroups),
            },
        )
        terminal_logger.info(
            "Section planning completed | company_id=%s tender_id=%s project_id=%s "
            "proposal_plan_id=%s status=%s groups=%s",
            request.company_id,
            request.tender_id,
            request.project_id,
            response.ProposalPlanId,
            response.PlanStatus,
            len(response.ProposalGroups),
        )
        return response
    except Exception as exc:
        http_error = _http_error(exc)
        event_logger.end(
            tracking_token=tracking_token,
            is_success=False,
            message="Tender section planning failed",
            event_type="TenderSectionPlanningFailed",
            payload={
                **_request_payload(request),
                "status_code": http_error.status_code,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        if http_error.status_code == 500:
            terminal_logger.exception("Section planning failed")
        else:
            terminal_logger.warning(
                "Section planning rejected | status_code=%s error_type=%s",
                http_error.status_code,
                type(exc).__name__,
            )
        raise http_error from exc


@router.get(
    "/latest",
    summary="Get the latest persisted Proposal Section Plan",
    response_model=ProposalPlanResponse,
)
async def get_latest_section_plan(
    company_id: str = Query(alias="CompanyId"),
    tender_id: str = Query(alias="TenderId"),
    project_id: str | None = Query(default=None, alias="ProjectId"),
) -> ProposalPlanResponse:
    event_logger = _request_logger()
    tracking_token = event_logger.start(
        message="Tender section plan retrieval started",
        event_type="TenderSectionPlanRetrievalStarted",
    )
    payload = {
        "company_id": company_id,
        "tender_id": tender_id,
        "project_id": project_id,
    }
    terminal_logger.info(
        "Section plan retrieval started | company_id=%s tender_id=%s project_id=%s",
        company_id,
        tender_id,
        project_id,
    )
    try:
        plan = MongoPlannerRepository().load_latest_plan(company_id, tender_id, project_id)
        if plan is None:
            event_logger.end(
                tracking_token=tracking_token,
                is_success=False,
                message="Tender section plan was not found",
                event_type="TenderSectionPlanNotFound",
                payload=payload,
            )
            terminal_logger.warning(
                "Section plan not found | company_id=%s tender_id=%s project_id=%s",
                company_id,
                tender_id,
                project_id,
            )
            raise HTTPException(status_code=404, detail="Persisted Section Plan was not found")

        response = ProposalPlanResponse.model_validate(plan)
        event_logger.end(
            tracking_token=tracking_token,
            is_success=True,
            message="Tender section plan retrieval completed",
            event_type="TenderSectionPlanRetrievalCompleted",
            payload={**payload, "proposal_plan_id": response.ProposalPlanId},
        )
        terminal_logger.info(
            "Section plan retrieval completed | company_id=%s tender_id=%s project_id=%s "
            "proposal_plan_id=%s",
            company_id,
            tender_id,
            project_id,
            response.ProposalPlanId,
        )
        return response
    except HTTPException:
        raise
    except Exception as exc:
        event_logger.end(
            tracking_token=tracking_token,
            is_success=False,
            message="Tender section plan retrieval failed",
            event_type="TenderSectionPlanRetrievalFailed",
            payload={**payload, "error_type": type(exc).__name__, "error": str(exc)},
        )
        terminal_logger.exception("Section plan retrieval failed")
        raise HTTPException(status_code=500, detail="Section plan retrieval failed") from exc


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail startup clearly rather than serving a deterministic or promptless agent.
    settings = Settings.from_env()
    settings.validate()
    MongoPlannerRepository(settings=settings).log_collection_selection()
    yield


app = FastAPI(title="Tender Section Planner", lifespan=lifespan)
app.include_router(router)


@app.get("/", include_in_schema=False)
async def open_api_docs() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
