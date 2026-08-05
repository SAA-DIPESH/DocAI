import time
import uuid
from fastapi import APIRouter, HTTPException
from app.agents.wintheam_extractor.graph.workflow import wintheam_extractor_graph
from app.agents.wintheam_extractor.schemas.request import WinThemeExtractorRequest
from app.agents.wintheam_extractor.schemas.response import WinThemeExtractorResponse
from app.infrastructure.logger import Logging


router = APIRouter(prefix="/api/v1/agents/wintheam",tags=["Win Theme Extractor"])

logger = Logging(agent_name="extract_wintheam",source_module="api_route")

MAX_RETRIES = 2


@router.post("/extract",response_model=WinThemeExtractorResponse,)
def generate_wintheam_retrieval_plan(request: WinThemeExtractorRequest):

    request_id = str(uuid.uuid4())

    tracking_token = logger.start(
        message="Win theme extraction started",
        event_type="WinThemeExtractionStarted",
        correlation_id=request_id,
    )

    initial_state = {
        # Request
        "request_id": request_id,
        "company_id": request.company_id,
        "industry": request.industry,
        "cpv_codes": request.cpv_codes,

        # Generation
        "retrieval_blueprint": None,
        "raw_llm_response": None,

        # Validation
        "validation_status": None,
        "validation_feedback": [],

        # Retry
        "retry_count": 0,
        "max_retries": MAX_RETRIES,

        # Execution
        "status": "pending",
        "current_step": None,
        "error": None,

        # Metrics
        "node_latencies": {},
    }

    try:

        start = time.perf_counter()

        result = wintheam_extractor_graph.invoke(initial_state)

        execution_time = round(
            time.perf_counter() - start,
            2,
        )

        anchor_group_count = len(
            result.get(
                "retrieval_blueprint",
                {},
            ).get(
                "anchor_groups",
                [],
            )
        )

        logger.end(
            tracking_token=tracking_token,
            is_success=result.get("status") != "failed",
            message="Win theme extraction completed",
            event_type="WinThemeExtractionCompleted",
            payload={
                "request_id": request_id,
                "company_id": request.company_id,
                "industry": request.industry,
                "cpv_codes": request.cpv_codes,
                "status": result.get("status"),
                "current_step": result.get("current_step"),
                "validation_status": result.get("validation_status"),
                "anchor_group_count": anchor_group_count,
                "execution_time_seconds": execution_time,
                "node_latencies": result.get(
                    "node_latencies",
                    {},
                ),
            },
        )

        return WinThemeExtractorResponse(
            request_id=request_id,
            company_id=request.company_id,
            industry=request.industry,
            cpv_codes=request.cpv_codes,

            status=result.get("status", "failed"),
            current_step=result.get("current_step"),

            retrieval_blueprint=result.get(
                "retrieval_blueprint"
            ),

            validation_status=result.get(
                "validation_status"
            ),
            validation_feedback=result.get(
                "validation_feedback",
                [],
            ),

            retry_count=result.get(
                "retry_count",
                0,
            ),

            error=result.get("error"),

            node_latencies=result.get(
                "node_latencies",
                {},
            ),
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
                "cpv_codes": request.cpv_codes,
                "error": str(exc),
            },
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )