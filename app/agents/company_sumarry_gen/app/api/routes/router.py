from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from app.agents.section_summary_agent.section_generation_agent import (
    SectionGenerationAgent
)

from app.agents.improve_section_summary.improve_section_summary import (
    SectionImprovementAgent
)
import traceback
router = APIRouter()


import time
import uuid
from fastapi import HTTPException

from app.utils.logger import AgentLogger

logger = AgentLogger()



class SectionGenerationRequest(BaseModel):

    company_id: str
    section_name: str
    purpose: str
  
  
@router.post("/generate-section-summery")
async def generate_section(
    request: SectionGenerationRequest
):
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        logger.log_event(
            agent_name="SectionGenerationAgent",
            message="Section generation request received",
            event_type="REQUEST_RECEIVED",
            source_module="generate_section_api",
            is_success=True,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name,
                "purpose": request.purpose
            },
            correlation_id=correlation_id
        )

        result = SectionGenerationAgent.generate_section(
            company_id=request.company_id,
            section_name=request.section_name,
            purpose=request.purpose
        )

        duration_ms = int((time.time() - start_time) * 1000)

        logger.log_event(
            agent_name="SectionGenerationAgent",
            message="Section generated successfully",
            event_type="REQUEST_COMPLETED",
            source_module="generate_section_api",
            is_success=True,
            duration_ms=duration_ms,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name
            },
            correlation_id=correlation_id
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as ex:
        duration_ms = int((time.time() - start_time) * 1000)

        logger.log_event(
            agent_name="SectionGenerationAgent",
            message=str(ex),
            event_type="REQUEST_FAILED",
            source_module="generate_section_api",
            is_success=False,
            duration_ms=duration_ms,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name,
                "error": str(ex)
            },
            correlation_id=correlation_id
        )

        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )

###################################################### IMprove summary agent ############################################################
class SectionImprovementRequest(BaseModel):

    company_id: str
    section_name: str
    section_summary: str
    
    purpose: str
    instruction: str

@router.post("/improve-section-summary")
async def improve_section(
    request: SectionImprovementRequest
):
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    try:

        logger.log_event(
            agent_name="SectionImprovementAgent",
            message="Section improvement request received",
            event_type="REQUEST_RECEIVED",
            source_module="improve_section_api",
            is_success=True,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name,
                "purpose": request.purpose,
                "instruction": request.instruction
            },
            correlation_id=correlation_id
        )

        result = SectionImprovementAgent.improve_section(
            company_id=request.company_id,
            section_name=request.section_name,
            section_summary=request.section_summary,
            purpose=request.purpose,
            instruction=request.instruction
        )

        duration_ms = int((time.time() - start_time) * 1000)

        logger.log_event(
            agent_name="SectionImprovementAgent",
            message="Section improved successfully",
            event_type="REQUEST_COMPLETED",
            source_module="improve_section_api",
            is_success=True,
            duration_ms=duration_ms,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name
            },
            correlation_id=correlation_id
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Section improved successfully",
                "data": result
            }
        )

    except Exception as error:

        duration_ms = int((time.time() - start_time) * 1000)

        logger.log_event(
            agent_name="SectionImprovementAgent",
            message=str(error),
            event_type="REQUEST_FAILED",
            source_module="improve_section_api",
            is_success=False,
            duration_ms=duration_ms,
            payload={
                "company_id": request.company_id,
                "section_name": request.section_name,
                "error": str(error)
            },
            correlation_id=correlation_id
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Failed to improve section",
                "error": str(error),
                "trace": traceback.format_exc()
            }
        )