import time
import uuid

from fastapi import APIRouter, HTTPException

from app.agents.wintheam_extractor.graph.workflow import wintheam_extractor_graph
from app.agents.wintheam_extractor.schemas.request import WintheamExtractorRequest
from app.agents.wintheam_extractor.schemas.response import WintheamExtractorResponse
from app.infrastructure.logger import Logging


router = APIRouter(
    prefix="/api/v1/agents/wintheam",
    tags=["Win Theme Extractor"],
)


logger = Logging(
    agent_name="extract_wintheam",
    source_module="api_route",
)


@router.post("/extract", response_model=WintheamExtractorResponse)
def generate_wintheam_retrieval_plan(request: WintheamExtractorRequest):

    request_id = str(uuid.uuid4())

    tracking_token = logger.start(
        message="Win theme extraction started",
        event_type="WinThemeExtractionStarted",
        correlation_id=request_id,
    )

    initial_state = {
        "request_id": request_id,
        "company_id": request.company_id,
        "industry": request.industry,
        "cpv_code": request.cpv_code,

        "response": None,
        "raw_llm_response": None,

        "validation_status": None,
        "validation_feedback": [],

        "retry_count": 0,
        "max_retries": 1,

        "status": "pending",
        "current_step": None,
        "error": None,

        "node_latencies": {},
    }

    try:

        start = time.perf_counter()

        result = wintheam_extractor_graph.invoke(initial_state)

        execution_time = round(time.perf_counter() - start, 2)

        logger.end(
            tracking_token=tracking_token,
            is_success=result.get("status") != "failed",
            message="Win theme extraction completed",
            event_type="WinThemeExtractionCompleted",
            payload={
                "request_id": request_id,
                "company_id": request.company_id,
                "industry": request.industry,
                "cpv_code": request.cpv_code,
                "status": result.get("status"),
                "current_step": result.get("current_step"),
                "validation_status": result.get("validation_status"),
                "generated_themes_count": len(result.get("generated_themes", [])),
                "execution_time_seconds": execution_time,
                "node_latencies": result.get("node_latencies", {}),
            },
        )

        return WintheamExtractorResponse(
            company_id=request.company_id,
            cpv_code=request.cpv_code,
            status=result.get("status", "failed"),
            current_step=result.get("current_step"),
            response=result.get("response"),
            validation_status=result.get("validation_status"),
            validation_feedback=result.get("validation_feedback", []),
            retry_count=result.get("retry_count", 0),
            error=result.get("error"),
            node_latencies=result.get("node_latencies", {}),
        )

    except Exception as exc:

        logger.end(
            tracking_token=tracking_token,
            is_success=False,
            message="Win theme extraction failed",
            event_type="WinThemeExtractionFailed",
            payload={
                "request_id": request_id,
                "company_id": request.company_id,
                "industry": request.industry,
                "cpv_code": request.cpv_code,
                "error": str(exc),
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )