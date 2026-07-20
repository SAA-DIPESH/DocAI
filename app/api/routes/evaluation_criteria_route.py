"""Evaluation Criteria Agent API endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from threading import Lock

from fastapi import APIRouter, HTTPException

from app.agents.EvaluationCriteriaAgent.graph.nodes import EvaluationCriteriaAgent
from app.agents.EvaluationCriteriaAgent.schemas.request import EvaluationCriteriaRequest
from app.infrastructure.logger import Logging


router = APIRouter(
    prefix="/api/v1/agents/evaluation-criteria",
    tags=["Evaluation Criteria Agent"],
)

_execution_lock = Lock()
terminal_logger = logging.getLogger("uvicorn.error")


def _run(request: EvaluationCriteriaRequest) -> dict:
    """
    Always generate fresh Evaluation Criteria output.

    IsRegenerated = False -> generate fresh output and save as Active.
    IsRegenerated = True  -> generate fresh output and save as Regenerating.
    """
    with _execution_lock:
        run_id = str(uuid.uuid4())
        status = "Regenerating" if request.is_regenerated else "Active"
        mode = "regenerate" if request.is_regenerated else "generate"

        terminal_logger.info(
            "Evaluation Criteria | mode=%s | run_id=%s | company_id=%s | "
            "tender_id=%s | status=%s",
            mode,
            run_id,
            request.company_id,
            request.tender_id,
            status,
        )

        # Always executes Qdrant retrieval, OpenAI extraction and validation.
        # persist=True makes the agent insert a new MongoDB document.
        output = EvaluationCriteriaAgent.execute(
            company_id=request.company_id,
            tender_id=request.tender_id,
            is_regenerated=request.is_regenerated,
            created_by=request.user_name,
            run_id=run_id,
            usage_context={
                "run_id": run_id,
                "user_id": request.user_id,
                "project_id": request.project_id,
                "jwt_token": request.jwt_token,
            },
            persist=True,
        )

        terminal_logger.info(
            "Evaluation Criteria | MongoDB document inserted | "
            "run_id=%s | status=%s",
            run_id,
            status,
        )

        # Add operational persistence information to the API response.
        response = dict(output)
        response["Status"] = status
        response["IsRegenerated"] = request.is_regenerated
        response["CreatedBy"] = request.user_name
        response["RunId"] = run_id

        return response


@router.post("/evaluate")
async def evaluate(request: EvaluationCriteriaRequest) -> dict:
    logger = Logging(
        agent_name=os.getenv("EC_AGENT_NAME", "Evaluation Criteria Agent"),
        source_module="evaluation_criteria_route",
    )

    tracking = logger.start(
        message="Evaluation Criteria generation started",
        event_type="EvaluationCriteriaGenerationStarted",
    )

    try:
        output = await asyncio.to_thread(_run, request)

        logger.end(
            tracking,
            is_success=True,
            message="Evaluation Criteria generation completed",
            event_type="EvaluationCriteriaGenerationCompleted",
            payload={
                "CompanyId": request.company_id,
                "TenderId": request.tender_id,
                "IsRegenerated": request.is_regenerated,
                "Status": (
                    "Regenerating"
                    if request.is_regenerated
                    else "Active"
                ),
                "UserId": request.user_id,
                "ProjectId": request.project_id,
                "RunId": output.get("RunId"),
            },
        )

        return output

    except Exception as exc:
        logger.end(
            tracking,
            is_success=False,
            message="Evaluation Criteria generation failed",
            event_type="EvaluationCriteriaGenerationFailed",
            payload={
                "CompanyId": request.company_id,
                "TenderId": request.tender_id,
                "IsRegenerated": request.is_regenerated,
                "UserId": request.user_id,
                "ProjectId": request.project_id,
                "error": str(exc),
            },
        )

        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "agent": "EvaluationCriteriaAgent",
        "status": "healthy",
    }