import os
import json
import time
from fastapi import APIRouter, HTTPException, status,Request
from pydantic import BaseModel,Optional
from app.infrastructure.token_usage import TokenUsageService
from app.infrastructure.agent.add_section_agent import add_section_agent
from app.utils.logger import AgentLogger

router = APIRouter(
    prefix="/section",
    tags=["Add proposal section Agent"]
)

agent_logger = AgentLogger()


class AddSectionRequest(BaseModel):
    tender_id: str
    company_id: str
    section_name: str
    section_purpose: str = ""
    userId: Optional[str] = None
    projectId: Optional[str] = None
    token: Optional[str] = None
    


@router.post("/generate")
async def generate_section(request: AddSectionRequest,http_request: Request):
    start_time = time.perf_counter()
    agent_name = "AddSectionAgent"
    source_module = "app.routes.sections"
    correlation_id = f"tender-{request.tender_id}" 

    try:
        # 1. Run the agent
        response = add_section_agent(
            tender_id=request.tender_id,
            company_id=request.company_id,
            section_name=request.section_name,
            section_purpose=request.section_purpose
            
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
            purpose="Grammar Correction",
        )
        

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 2. Intercept internal JSONDecodeError strings if agent fell back
        if isinstance(response, dict) and response.get("success") is False:
            inner_data = response.get("data", {})
            raw_response_str = inner_data.get("raw_response", "")

            if isinstance(raw_response_str, str) and raw_response_str.strip():
                try:
                    clean_content = raw_response_str.strip()
                    if clean_content.startswith("```"):
                        clean_content = clean_content.split("```")[1]
                        if clean_content.startswith("json"):
                            clean_content = clean_content[4:]
                        clean_content = clean_content.strip()

                    response = json.loads(clean_content, strict=False)
                except Exception as parse_err:
                    # ✅ FIX 1: If parsing completely fails, log as failure and raise an HTTPException
                    agent_logger.log_event(
                        agent_name=agent_name,
                        message=f"Critical: Unrecoverable JSON format from LLM: {str(parse_err)}",
                        event_type="SECTION_GENERATION_PARSING_FAILED",
                        source_module=source_module,
                        is_success=False,
                        duration_ms=duration_ms,
                        payload={"request": request.model_dump(), "error": str(parse_err)},
                        correlation_id=correlation_id
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"LLM generated invalid structural JSON. Raw backup description: {response.get('message')}"
                    )

        # -----------------------------------------------------------------
        # 🔥 DEEP SANITIZATION BLOCK (Bulletproof Cleanup)
        # -----------------------------------------------------------------
        if isinstance(response, dict):
            # Clean Top Level
            response["SectionId"] = request.section_name
            response["SectionName"] = request.section_name
            
            # Clean data wrapper if nested
            if "data" in response and isinstance(response["data"], dict):
                response["data"]["SectionId"] = request.section_name
                response["data"]["SectionName"] = request.section_name
                
                if "GeneratedSubSections" in response["data"] and isinstance(response["data"]["GeneratedSubSections"], list):
                    for idx, sub in enumerate(response["data"]["GeneratedSubSections"]):
                        if isinstance(sub, dict):
                            response["data"]["GeneratedSubSections"][idx]["SectionId"] = f"{request.section_name}-0{idx+1}"
                            # ✅ FIX 2: Dynamic subsection titles prevent database values from leaking
                            if "SectionName" in sub:
                                response["data"]["GeneratedSubSections"][idx]["SectionName"] = f"{request.section_name} - Part {idx+1}"

            # Clean subsections in main schema body
            if "GeneratedSubSections" in response and isinstance(response["GeneratedSubSections"], list):
                for idx, sub in enumerate(response["GeneratedSubSections"]):
                    if isinstance(sub, dict):
                        response["GeneratedSubSections"][idx]["SectionId"] = f"{request.section_name}-0{idx+1}"
                        # ✅ FIX 2: Clean main schema body subsections as well
                        response["GeneratedSubSections"][idx]["SectionName"] = f"{request.section_name} - Part {idx+1}"

        # 3. Log and return final output matching your exact schema
        agent_logger.log_event(
            agent_name=agent_name,
            message=f"Successfully generated section: '{request.section_name}'",
            event_type="SECTION_GENERATION_SUCCESS",
            source_module=source_module,
            is_success=True,
            duration_ms=duration_ms,
            payload={
                "request": request.model_dump(),
                "response_summary": {"success": True, "section_id": request.section_name}
            },
            correlation_id=correlation_id
        )

        return {
            "success": True,
            "message": "Section generated successfully",
            "data": response
        }

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions directly so they bypass the global catch block
        raise
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        error_message = str(e)

        agent_logger.log_event(
            agent_name=agent_name,
            message=f"Failed to generate section '{request.section_name}': {error_message}",
            event_type="SECTION_GENERATION_FAILED",
            source_module=source_module,
            is_success=False,
            duration_ms=duration_ms,
            payload={"request": request.model_dump(), "error": error_message},
            correlation_id=correlation_id
        )

        raise HTTPException(status_code=500, detail=error_message)