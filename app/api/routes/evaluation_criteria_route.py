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
from app.agents.EvaluationCriteriaAgent.services.output_service import (
    EvaluationCriteriaOutputService,
)
from app.infrastructure.logger import Logging


router = APIRouter(
    prefix="/api/v1/agents/evaluation-criteria",
    tags=["Evaluation Criteria Agent"],
)
_execution_lock = Lock()
terminal_logger = logging.getLogger("uvicorn.error")


def _run(request: EvaluationCriteriaRequest) -> dict:
    with _execution_lock:
        if not request.is_regenerated:
            terminal_logger.info(
                "Evaluation Criteria | mode=active-cache | company_id=%s | tender_id=%s",
                request.company_id,
                request.tender_id,
            )
            terminal_logger.info(
                "[AIUsageLogger] not applicable | reason=active Mongo response; no LLM call"
            )
            stored = EvaluationCriteriaOutputService.get_active(
                request.company_id,
                request.tender_id,
            )
            if stored is None:
                raise LookupError("Evaluation Criteria document could not be loaded.")
            terminal_logger.info("Evaluation Criteria | active Mongo document returned")
            return stored

        run_id = str(uuid.uuid4())
        terminal_logger.info(
            "Evaluation Criteria | mode=regenerate | run_id=%s | company_id=%s | tender_id=%s",
            run_id,
            request.company_id,
            request.tender_id,
        )
        output = EvaluationCriteriaAgent.execute(
            request.company_id,
            request.tender_id,
            usage_context={
                "run_id": run_id,
                "user_id": request.user_id,
                "project_id": request.project_id,
                "jwt_token": request.jwt_token,
            },
            persist=False,
        )
        _, stored = EvaluationCriteriaOutputService.insert_regenerated(
            output,
            created_by=request.user_name,
            run_id=run_id,
        )
        terminal_logger.info(
            "Evaluation Criteria | regenerated Mongo document inserted | run_id=%s | status=regenerating",
            run_id,
        )
        return stored


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
                "UserId": request.user_id,
                "ProjectId": request.project_id,
            },
        )
        return output
    except LookupError as exc:
        logger.end(
            tracking,
            is_success=False,
            message="Evaluation Criteria document not found",
            event_type="EvaluationCriteriaNotFound",
            payload={"CompanyId": request.company_id, "TenderId": request.tender_id},
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.end(
            tracking,
            is_success=False,
            message="Evaluation Criteria generation failed",
            event_type="EvaluationCriteriaGenerationFailed",
            payload={"CompanyId": request.company_id, "TenderId": request.tender_id, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {"agent": "EvaluationCriteriaAgent", "status": "healthy"}
