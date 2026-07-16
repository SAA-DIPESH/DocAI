import os
import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.infrastructure.token_usage import TokenUsageService

from ...infrastructure.agents.taxonomy_agent import taxonomy_agent
from ...services.mongo_services import TaxonomyRepository
from ...utils.logger import AgentLogger






router = APIRouter(
    prefix="/taxonomy",
    tags=["Document Taxonomy"]
)

logger = AgentLogger()


class AdditionalCPV(BaseModel):
    code: str
    label: Optional[str] = None


class CPV(BaseModel):
    code: str
    label: Optional[str] = None
    additionalCodes: List[AdditionalCPV] = Field(default_factory=list)


class Context(BaseModel):
    country: Optional[str] = None
    procedure: Optional[str] = None
    sectorHint: Optional[str] = None


class TaxonomyRequest(BaseModel):
    tenderId: Optional[str] = None
    companyId: Optional[str] = None
    userId: Optional[str] = None
    projectId: Optional[str] = None
    token: Optional[str] = None
    cpv: Optional[CPV] = None
    companyCpvCode: Optional[str] = None
    companyCpvLabel: Optional[str] = None
    context: Context = Field(default_factory=Context)

    @model_validator(mode="after")
    def validate_and_normalize_request(self):
        if not self.tenderId and not self.companyId:
            raise ValueError("Either tenderId or companyId is required")

        if self.cpv is None and self.companyCpvCode:
            self.cpv = CPV(
                code=self.companyCpvCode,
                label=self.companyCpvLabel,
                additionalCodes=[],
            )

        if self.cpv is None:
            raise ValueError("cpv.code or companyCpvCode is required")

        return self

    @property
    def cpv_set_for(self) -> str:
        return "Tender" if self.tenderId else "Company"





@router.post("/generate")
async def generate_taxonomy(
    request: TaxonomyRequest,
    http_request: Request
):
    start_time = time.perf_counter()
    correlation_id = str(uuid.uuid4())

    agent_name = "TenderDocumentTaxonomyAgent"
    source_module = "api.router.taxonomy_router"
    agent_input = request.model_dump(
        exclude={
            "token",
            "userId",
            "projectId",
            "companyCpvCode",
            "companyCpvLabel",
        }
    )
    agent_input["CPVsetfor"] = request.cpv_set_for

    try:
        logger.log_event(
            agent_name=agent_name,
            message="Taxonomy generation started",
            event_type="REQUEST_RECEIVED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id,
            payload=agent_input
        )

        # ==========================
        # RUN TAXONOMY AGENT
        # ==========================
        existing_taxonomy = TaxonomyRepository.find_by_scope(
            cpv_code=request.cpv.code,
            cpv_set_for=request.cpv_set_for,
            tender_id=request.tenderId,
            company_id=request.companyId,
        )

        if existing_taxonomy:
            duration_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            logger.log_event(
                agent_name=agent_name,
                message="Taxonomy returned from Mongo cache",
                event_type="CACHE_HIT",
                source_module=source_module,
                is_success=True,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                payload={
                    "cpv": request.cpv.code,
                    "tenderId": request.tenderId,
                    "companyId": request.companyId,
                    "CPVsetfor": request.cpv_set_for,
                    "projectId": request.projectId,
                }
            )

            return {
                "success": True,
                "data": existing_taxonomy,
                "cached": True,
                "token_usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "model": "",
                },
            }

        response = await taxonomy_agent(
            input_json=agent_input
        )
        token_usage = response["token_usage"]

        saved_taxonomy = TaxonomyRepository.save(
            {
                **response["data"],
                "cpv": agent_input["cpv"],
                "context": agent_input["context"],
                "tenderId": request.tenderId,
                "companyId": request.companyId,
                "projectId": request.projectId,
                "sourceRunId": (
                    correlation_id
                    if request.cpv_set_for == "Tender"
                    else None
                ),
                "CPVsetfor": request.cpv_set_for,
            }
        )

        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )
        
        # Build source IDs dynamically
        source_ids = []
        if request.tenderId:
            source_ids.append({
                "sourceIdType": "Tender",
                "id": request.tenderId,
            })

        if request.companyId:
            source_ids.append({
                "sourceIdType": "Company",
                "id": request.companyId,
            })

        access_token = (
            request.token
            or http_request.headers.get("Authorization", "")
            .removeprefix("Bearer ")
            .strip()
            or os.getenv("AI_USAGE_BEARER_TOKEN")
        )

        # Token usage logging with dynamic source_ids list
        token_usage_payload = {
    "applicationName": "TaxonomyAgent",
    "sourceIds": source_ids,
    "runId": correlation_id,
    "userId": request.userId or os.getenv("AI_USAGE_USER_ID", ""),
    "purpose": "Generate Taxonomy",
    "method": "LLM",
    "agentName": agent_name,
    "usageType": "Completion",
    "inputToken": token_usage["input_tokens"],
    "outputToken": token_usage["output_tokens"],
    "totalTokens": token_usage["total_tokens"],
    "model": token_usage["model"],
    "duration": duration_ms,
    "cost": {
        "currency": "USD",
        "value": 0
    },
    "companyId": request.companyId,
    "tenderId": request.tenderId,
    "projectId": request.projectId or os.getenv("AI_USAGE_PROJECT_ID"),
}

        # print("Token usage log payload:", token_usage_payload)

        token_usage_log_response = await TokenUsageService.log_usage(
            token_usage_payload,
            bearer_token=access_token
        )

        # print("Token usage log response:", token_usage_log_response)

        logger.log_event(
            agent_name=agent_name,
            message="Taxonomy generated successfully",
            event_type="AGENT_COMPLETED",
            source_module=source_module,
            is_success=True,
            correlation_id=correlation_id
        )

        logger.log_event(
            agent_name=agent_name,
            message="Taxonomy generation completed",
            event_type="OUTPUT_SAVED",
            source_module=source_module,
            is_success=True,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            payload={
                "tenderId": request.tenderId,
                "companyId": request.companyId,
                "cpv": request.cpv.code,
                "classification_count": len(
                    response["data"].get(
                        "classificationSet",
                        []
                    )
                ),
                "token_usage": response["token_usage"],
            }
        )

        return {
            "success": True,
            "data": saved_taxonomy,
            "cached": False,
            "token_usage": response["token_usage"],
        }

    except Exception as ex:
        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

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
