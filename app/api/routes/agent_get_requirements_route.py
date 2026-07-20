import time

from fastapi import APIRouter, HTTPException

from app.agents.tender_requirement_agent.schemas.request import RequirementRequest
from app.agents.tender_requirement_agent.services.requirement_service import RequirementService
from app.infrastructure.logger import Logging
from app.infrastructure.token_usage_logger import TokenUsageService


logger = Logging(
    agent_name="Requirements_Detection_And_Intent_Agent",
    source_module="agent_requirement_route",
)

router = APIRouter(
    prefix="/api/v1/agents",
    tags=["Requirement Agent"],
)

service = RequirementService()


@router.post("/get_requirements")
async def process_requirement(
    request: RequirementRequest,
):

    tracking_token = logger.start(
        message="Requirement processing started",
        event_type="RequirementProcessingStarted",
    )

    start_time = time.perf_counter()

    status = "Regenerating" if request.IsRegenerate else "Active"

    try:

        result = await service.process_tender(
            company_id=request.CompanyId,
            tender_id=request.TenderId,
            user_id=request.UserId,
            user_name=request.UserName,
            status=status,
        )

        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        token_usage = result.get("TokenUsage", {})

        # Log token usage (do not fail the API if logging fails)
        try:
            await TokenUsageService.log_agent_usage(
                request=request,
                token_usage=token_usage,
                duration_ms=duration_ms,
                correlation_id=request.ProjectId,
                application_name="Tender",
                source_ids=[request.TenderId],
                purpose="Requirement Extraction",
                method="POST",
                agent_name="Requirements_Detection_And_Intent_Agent",
                usage_type="LLM",
            )
        except Exception as log_ex:
            logger.warning(
                tracking_token=tracking_token,
                message="Failed to log token usage",
                payload={
                    "company_id": request.CompanyId,
                    "tender_id": request.TenderId,
                    "error": str(log_ex),
                },
            )

        logger.end(
            tracking_token=tracking_token,
            is_success=True,
            message="Requirement processing completed",
            event_type="RequirementProcessingCompleted",
            payload={
                "company_id": request.CompanyId,
                "tender_id": request.TenderId,
                "status": result.get("Status"),
                "total_chunks": result.get("TotalChunks"),
                "processed_chunks": result.get("ProcessedChunks"),
            },
        )

        return result

    except Exception as ex:

        logger.end(
            tracking_token=tracking_token,
            is_success=False,
            message="Requirement processing failed",
            event_type="RequirementProcessingFailed",
            payload={
                "company_id": request.CompanyId,
                "tender_id": request.TenderId,
                "error": str(ex),
            },
        )

        raise HTTPException(
            status_code=500,
            detail=str(ex),
        )