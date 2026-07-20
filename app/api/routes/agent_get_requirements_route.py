from fastapi import APIRouter, HTTPException

from app.agents.tender_requirement_agent.schemas.request import RequirementRequest
from app.agents.tender_requirement_agent.services.requirement_service import RequirementService
from app.infrastructure.logger import Logging


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

    status = "Regenerating" if request.IsRegenerate else "Active"

    try:

        result = await service.process_tender(
            company_id=request.CompanyId,
            tender_id=request.TenderId,
            user_id=request.UserId,
            user_name=request.UserName,
            status=status,
        )

        logger.end(
            tracking_token=tracking_token,
            is_success=True,
            message="Requirement processing completed",
            event_type="RequirementProcessingCompleted",
            payload={
                "company_id": request.CompanyId,
                "tender_id": request.TenderId,
                "status": result.get("status"),
                "total_chunks": result.get("total_chunks"),
                "processed_chunks": result.get("processed_chunks"),
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