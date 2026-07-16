from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time
import uuid
import json
from app.agents.GrammerAI.app.infrastructure.agents.rephraser_agent import rephraser_agent
from  app.agents.GrammerAI.app.utils.logger import AgentLogger
# Import your async LLM task
from app.agents.GrammerAI.app.infrastructure.agents.grammer_agent import grammer_agent
from app.infrastructure.token_usage import TokenUsageService
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
import os
router = APIRouter(
    prefix="/grammar",
    tags=["Grammar Correction"]
)

logger = AgentLogger()


class RequestBody(BaseModel):
    content: str
    tenderId: Optional[str] = None
    companyId: Optional[str] = None
    userId: Optional[str] = None
    projectId: Optional[str] = None
    token: Optional[str] = None
    
@router.post("/grammer_correction")
async def grammar_correction_api(
    request: RequestBody,
    http_request: Request
    
):
    start_time = time.perf_counter()
    correlation_id = str(uuid.uuid4())
    agent_name = "GrammarCorrectionAgent"
    source_module = "api.router.router"
    print(f"Run ID: {correlation_id}")

    try:
        logger.log_event(
            agent_name=agent_name,
            message="Grammar correction process started",
            event_type="REQUEST_RECEIVED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id,
            payload=request.model_dump()
        )

        # ==========================
        # RUN LLM AGENT TASK
        # ==========================
        agent_response = await grammer_agent(content=request.content)
        # print(agent_response)
        # token_usage = TokenUsageService.extract_token_usage(agent_response)
        token_usage = agent_response["token_usage"]
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        access_token = (
            request.token
            or http_request.headers.get("Authorization", "")
            .removeprefix("Bearer ")
            .strip()
            or os.getenv("AI_USAGE_BEARER_TOKEN")
        )

        await TokenUsageService.log_agent_usage(
            request=request,
            token_usage=token_usage,
            bearer_token=access_token,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            application_name="Tender",
            agent_name=agent_name,
            purpose="Grammar Correction",
        )

        logger.log_event(
            agent_name=agent_name,
            message="Grammar corrected successfully via LLM",
            event_type="AGENT_COMPLETED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.log_event(
            agent_name=agent_name,
            message="Grammar correction completed successfully",
            event_type="OUTPUT_SAVED",
            source_module=source_module,
            is_success=True,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            payload={
                "content_length": len(request.content),
                # "token_usage": agent_response["token_usage"],
            }
        )

        return {
            "success": True,
            "data": agent_response["data"],
            # "token_usage": agent_response["token_usage"],
        }

    except Exception as ex:
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.log_event(
            agent_name=agent_name,
            message=str(ex),
            event_type="ERROR",
            source_module=source_module,
            is_success=False,      
            duration_ms=duration_ms,
            correlation_id=correlation_id
        )

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )





@router.post("/sentence_rephrase")
async def sentence_rephraser_api(
    request: RequestBody,
    http_request: Request
):
    start_time = time.perf_counter()
    correlation_id = str(uuid.uuid4())
    agent_name = "SentenceRephraserAgent"
    source_module = "api.router.router"
    print(f"Run ID: {correlation_id}")
    

    try:
        logger.log_event(
            agent_name=agent_name,
            message="Sentence rephrasing process started",
            event_type="REQUEST_RECEIVED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id,
            payload=request.model_dump()
        )

        # ==========================
        # RUN LLM AGENT TASK
        # ==========================
        agent_response = await rephraser_agent(
            content=request.content
        )
        # print(agent_response.model_dump())
        # print(agent_response)
        # print(agent_response.response_metadata)
        # print(agent_response.usage_metadata)
        token_usage = agent_response["token_usage"]
        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )
        access_token = (
            request.token
            or http_request.headers.get("Authorization", "")
            .removeprefix("Bearer ")
            .strip()
            or os.getenv("AI_USAGE_BEARER_TOKEN")
        )
        await TokenUsageService.log_agent_usage(
            request=request,
            token_usage=token_usage,
            bearer_token=access_token,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            application_name="Tender",
            agent_name=agent_name,
            purpose="Sentence Rephrase",
        )

        logger.log_event(
            agent_name=agent_name,
            message="Sentence rephrased successfully via LLM",
            event_type="AGENT_COMPLETED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.log_event(
            agent_name=agent_name,
            message="Sentence rephrasing completed successfully",
            event_type="OUTPUT_SAVED",
            source_module=source_module,
            is_success=True,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            payload={
                "content_length": len(request.content),
                # "token_usage": agent_response["token_usage"],
            }
        )

        return {
            "success": True,
            "data": agent_response["data"],
            # "token_usage": agent_response["token_usage"],
        }

    except Exception as ex:
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        logger.log_event(
            agent_name=agent_name,
            message=str(ex),
            event_type="ERROR",
            source_module=source_module,
            is_success=False,
            duration_ms=duration_ms,
            correlation_id=correlation_id
        )

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )
