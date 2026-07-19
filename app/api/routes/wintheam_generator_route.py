import time
import uuid

from fastapi import APIRouter, HTTPException

from app.agents.wintheam_generator.graph.workflow import win_theme_graph
from app.agents.wintheam_generator.schemas.request import WinThemeRequest
from app.agents.wintheam_generator.schemas.response import WinThemeResponse
from app.infrastructure.logger import Logging


router = APIRouter(
    prefix="/api/v1/agents/wintheam",
    tags=["Win Theme Generator"],
)


logger = Logging(
    agent_name="wintheam_generator",
    source_module="api_route",
)


@router.post("/generate", response_model=WinThemeResponse)
def generate_win_theme(request: WinThemeRequest):

    request_id = str(uuid.uuid4())

    tracking_token = logger.start(
        message="Win theme generation started",
        event_type="WinThemeGenerationStarted",
        correlation_id=request_id,
    )

    initial_state = {
        "request_id": request_id,
        "company_id": request.company_id,
        "industry": request.industry,
        "cpv_code": request.cpv_code,

        "rules": {},

        "context": {},
        "anchor_groups": [],

        "current_anchor_index": 0,
        "current_anchor_group": None,
        "next_step": "continue",

        "current_evidence": [],
        "current_win_theme": None,
        "retrieval_status": None,

        "generated_themes": [],

        "validation_status": None,
        "warnings": [],
        "unsupported_claims_removed": [],

        "status": "pending",
        "current_step": None,
        "error": None,

        "node_latencies": {},
    }

    try:

        start = time.perf_counter()

        result = win_theme_graph.invoke(initial_state)

        execution_time = round(time.perf_counter() - start, 2)

        logger.end(
            tracking_token=tracking_token,
            is_success=result.get("status") != "failed",
            message="Win theme generation completed",
            event_type="WinThemeGenerationCompleted",
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

        return WinThemeResponse(
            status=result.get("status", "failed"),
            current_step=result.get("current_step"),
            validation_status=result.get("validation_status"),
            warnings=result.get("warnings", []),
            error=result.get("error"),
            generated_themes=result.get("generated_themes", []),
            node_latencies=result.get("node_latencies", {}),
        )

    except Exception as exc:

        logger.end(
            tracking_token=tracking_token,
            is_success=False,
            message="Win theme generation failed",
            event_type="WinThemeGenerationFailed",
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