import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, Request
from app.infrastructure.logger import Logging
from app.agents.Section_writer.schemas.request import ProposalGenerationRequest
from app.agents.Section_writer.schemas.state import ProposalGenerationState
from app.agents.Section_writer.graph.workflow.workflow import graph as proposal_generation_graph
from app.infrastructure.token_usage import TokenUsageService
import os
from app.agents.Section_writer.services.mongo_services.save_response import ProposalSummaryRepository
router = APIRouter(prefix="/proposal", tags=["Proposal Generation"])

logger = Logging(
    agent_name="ProposalGenerationAgent",
    source_module="app.api.routes.section_writer_router",
)


# ProposalRepository=ProposalSummaryRepository()



# @router.post("/generate")
# async def generate_proposal(
#     request: ProposalGenerationRequest,
#     http_request: Request,
# ):
#     start_time = time.perf_counter()

#     correlation_id = str(uuid.uuid4())

#     agent_name = "ProposalGenerationAgent"
#     source_module = "api.router.proposal_router"

#     print(f"Run ID: {correlation_id}")
#     try:
#         logger.log_event(
#             agent_name=agent_name,
#             message="Proposal generation started",
#             event_type="REQUEST_RECEIVED",
#             source_module=source_module,
#             is_success=True,
#             correlation_id=correlation_id,
#             payload=request.model_dump(),
#         )

    

#         initial_state: ProposalGenerationState = {
#             "company_id": request.company_id,
#             "tender_id": request.tender_id,
#             "proposal_plan_id": request.proposal_plan_id,
#             "user_id": request.user_id,
#             "workflow_metadata": {
#                 "workflow_status": "Started",
#                 "current_node": "context_builder",
#                 "retry_count": 0,
#                 "warnings": [],
#                 "errors": [],
#             },
#         }

#         result = await proposal_generation_graph.ainvoke(
#             initial_state
#         )
#          ####################################################
#         # Aggregate token usage
#         ####################################################

#         input_tokens = 0
#         output_tokens = 0
#         total_tokens = 0
#         model = ""

#         for section in result.get("section_results", []):

#             usage = section.get("token_usage", {}).get("total", {})

#             input_tokens += usage.get("input_tokens", 0)
#             output_tokens += usage.get("output_tokens", 0)
#             total_tokens += usage.get("total_tokens", 0)

#             if not model:
#                 model = usage.get("model", "")

#         duration_ms = int(
#             (time.perf_counter() - start_time) * 1000
#         )

#         access_token = (
#             request.token
#             or http_request.headers.get(
#                 "Authorization",
#                 "",
#             )
#             .removeprefix("Bearer ")
#             .strip()
#             or os.getenv("AI_USAGE_BEARER_TOKEN")
#         )

#         await TokenUsageService.log_agent_usage(
#             request=request,
#             token_usage={
#                 "input_tokens": input_tokens,
#                 "output_tokens": output_tokens,
#                 "total_tokens": total_tokens,
#                 "model": model,
#             },
#             bearer_token=access_token,
#             correlation_id=correlation_id,
#             duration_ms=duration_ms,
#             application_name="Tender",
#             agent_name=agent_name,
#             purpose="Proposal Generation",
#         )

#         logger.log_event(
#             agent_name=agent_name,
#             message="Proposal generated successfully",
#             event_type="AGENT_COMPLETED",
#             source_module=source_module,
#             is_success=True,
#             correlation_id=correlation_id,
#         )

#         logger.log_event(
#             agent_name=agent_name,
#             message="Proposal generation completed",
#             event_type="OUTPUT_SAVED",
#             source_module=source_module,
#             is_success=True,
#             duration_ms=duration_ms,
#             correlation_id=correlation_id,
#             payload={
#                 "sections_generated": len(
#                     result.get("section_results", [])
#                 ),
#                 "total_tokens": total_tokens,
#             },
#         )

#         return {
#             "status": "success",
#             "data": result,
#         }

#     except Exception as ex:

#         duration_ms = int(
#             (time.perf_counter() - start_time) * 1000
#         )

#         logger.log_event(
#             agent_name=agent_name,
#             message=str(ex),
#             event_type="ERROR",
#             source_module=source_module,
#             is_success=False,
#             duration_ms=duration_ms,
#             correlation_id=correlation_id,
#         )

#         raise HTTPException(
#             status_code=500,
#             detail=str(ex),
#         )

#     #     return {
#     #         "status": "success",
#     #         "data": result,
#     #     }

#     # except Exception as ex:
#     #     raise HTTPException(
#     #         status_code=500,
#     #         detail=str(ex),
#     #     )

token_usage_service = TokenUsageService()

@router.post("/generate")
async def generate_proposal(
    request: ProposalGenerationRequest,
    http_request: Request,
    
):
    start_time = time.perf_counter()

    correlation_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    print(f"Run ID : {correlation_id}")

    result = {}

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    model = ""

    try:
        logger.log(
            message="Proposal generation started",
            event_type="REQUEST_RECEIVED",
            is_success=True,
            correlation_id=correlation_id,
            payload=request.model_dump(),
        )

        initial_state: ProposalGenerationState = {
            "company_id": request.company_id,
            "tender_id": request.tender_id,
            "is_regenerate": request.is_regenerate,
            "user_id": request.user_id,
            "workflow_metadata": {
                "workflow_status": "Started",
                "current_node": "context_builder",
                "retry_count": 0,
                "warnings": [],
                "errors": [],
            },
        }

        result = await proposal_generation_graph.ainvoke(initial_state)
        generation_context = result.get("generation_context", {})
        proposal_plan_id = generation_context.get("ProposalPlanId")
        proposal_id = generation_context.get("ProposalId") or proposal_plan_id

        if not proposal_plan_id:
            source_status = generation_context.get("SourceStatus")
            expected_status = "Regenerating" if request.is_regenerate else "Active"
            status_detail = (
                f" Checked status: {source_status or expected_status}."
            )
            raise HTTPException(
                status_code=404,
                detail=(
                    "No proposal plan found for the supplied CompanyId and TenderId."
                    f"{status_detail}"
                ),
            )

        result.update(
            {
                "company_id": request.company_id,
                "tender_id": request.tender_id,
                "user_id": request.user_id,
                "user_name": request.user_name,
                "project_id": request.project_id,
                "proposal_plan_id": proposal_plan_id,
                "proposal_id": proposal_id,
                "version_id": version_id,
            }
        )
        
        # Save Proposal Summary (Fixed Indentation Here)
        proposal_repository = None
        try:
            proposal_repository = ProposalSummaryRepository()

            proposal_repository.save_proposal_summary(
                response=result,
                is_regenerate=request.is_regenerate,
            )
        except Exception as ex:
            print(f"Mongo Save Error: {ex}")
            logger.log(
                message=f"Failed to save proposal summary: {str(ex)}",
                event_type="DATABASE_ERROR",
                is_success=False,
                correlation_id=correlation_id,
            )
            raise
        finally:
            if proposal_repository:
                proposal_repository.close()

        logger.log(
            message="Proposal generated successfully",
            event_type="AGENT_COMPLETED",
            is_success=True,
            correlation_id=correlation_id,
        )

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise

    except Exception as ex:
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        try:
            logger.log(
                message=str(ex),
                event_type="ERROR",
                is_success=False,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
        except Exception as log_ex:
            print(f"Logger failed : {log_ex}")

        raise HTTPException(
            status_code=500,
            detail=str(ex),
        )

    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        if isinstance(result, dict):
            for section in result.get("section_results", []):
                usage = section.get("token_usage", {}).get("total", {})

                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)
                total_tokens += usage.get("total_tokens", 0)

                if not model:
                    model = usage.get("model", "")

        access_token = (
            request.jwt_token
            or http_request.headers.get("Authorization", "")
            or os.getenv("AI_USAGE_BEARER_TOKEN")
            or ""
        ).removeprefix("Bearer ").strip()

        if total_tokens > 0:
            token_usage_payload = {
                "sections_generated": len(result.get("section_results", [])),
                "total_tokens": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": model,
            }

            try:
                token_usage_response = await token_usage_service.log_agent_usage(
                    request=request,
                    token_usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "model": model,
                    },
                    bearer_token=access_token,
                    correlation_id=correlation_id,
                    duration_ms=duration_ms,
                    application_name="Tender",
                    agent_name="ProposalGenerationAgent",
                    purpose="Proposal Generation",
                )

                usage_saved = token_usage_response is not None
                if isinstance(token_usage_response, dict):
                    usage_saved = token_usage_response.get("success", True) is not False

                token_usage_payload["token_usage_response"] = token_usage_response

                logger.log(
                    message=(
                        "Token usage logged"
                        if usage_saved
                        else "Token usage logging failed or skipped"
                    ),
                    event_type=(
                        "OUTPUT_SAVED"
                        if usage_saved
                        else "TOKEN_USAGE_LOG_FAILED"
                    ),
                    is_success=usage_saved,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id,
                    payload=token_usage_payload,
                )

            except Exception as ex:
                logger.log(
                    message=f"Token usage logging failed: {str(ex)}",
                    event_type="TOKEN_USAGE_LOG_FAILED",
                    is_success=False,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id,
                    payload=token_usage_payload,
                )
        else:
            logger.log(
                message="Token usage logging skipped: no token usage found",
                event_type="TOKEN_USAGE_LOG_SKIPPED",
                is_success=False,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
                payload={
                    "sections_generated": (
                        len(result.get("section_results", []))
                        if isinstance(result, dict)
                        else 0
                    ),
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model": model,
                },
            )
####################################################
@router.post("/generate/stream")
async def generate_proposal_stream(
    request: ProposalGenerationRequest,
):

    initial_state = {
        "company_id": request.company_id,
        "tender_id": request.tender_id,
        "is_regenerate": request.is_regenerate,
        "user_id": request.user_id,
        "workflow_metadata": {
            "workflow_status": "Started",
            "current_node": "context_builder",
            "retry_count": 0,
            "warnings": [],
            "errors": [],
        },
    }

    async for event in proposal_generation_graph.astream(initial_state):
        print(event)
