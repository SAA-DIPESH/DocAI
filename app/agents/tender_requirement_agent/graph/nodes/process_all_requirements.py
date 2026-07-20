import asyncio
import time
from copy import deepcopy
from typing import Any, Dict

from app.agents.tender_requirement_agent.chains.intent_chain import understand_intent
from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState
from app.agents.tender_requirement_agent.services.requirement_repository_mongo import (
    requirement_repository,
)
from app.agents.tender_requirement_agent.utils.helper import update_latency
from app.infrastructure.token_usage_logger import TokenUsageService


async def _process_requirement(
    requirement: Dict[str, Any],
    state: TenderRequirementState,
    index: int,
) -> Dict[str, Any]:
    """
    Process a single requirement by:
    1. Generating RequirementId
    2. Understanding business intent
    3. Preparing MongoDB document
    """

    result = deepcopy(requirement)

    result["RequirementId"] = (
        f"{state['document_id']}-"
        f"{state['chunk_id']}-"
        f"REQ-{index + 1:03d}"
    )

    # LLM Call
    raw_response, intent_result = await understand_intent(
        heading=state.get("heading"),
        requirement=result["RequirementText"],
        requirement_type=result["RequirementType"],
        requirement_strength=result["RequirementStrength"],
    )

    # Extract token usage only
    usage = TokenUsageService.extract_token_usage(raw_response)

    result["IntentResult"] = intent_result

    document = {
        # Metadata
        "CompanyId": state["company_id"],
        "DocumentId": state["document_id"],
        "TenderId": state["tender_id"],
        "ChunkId": state["chunk_id"],
        "RequirementId": result["RequirementId"],

        # User Information
        "UserId": state["user_id"],
        "UserName": state["user_name"],

        # Requirement Details
        "RequirementText": result["RequirementText"],
        "RequirementType": result["RequirementType"],
        "RequirementStrength": result["RequirementStrength"],
        "MandatoryFlag": result["MandatoryFlag"],
        "Priority": result["Priority"],
        "Confidence": result["Confidence"],

        # Intent Understanding
        "IntentResult": result["IntentResult"],

        # Source Information
        "Heading": state.get("heading"),
        "PageNumber": state.get("page_number"),

        # Business Status
        "Status": state["status"],
    }

    return {
        "document": document,
        "usage": usage,
    }


async def process_requirements_node(
    state: TenderRequirementState,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    try:

        requirements = state.get("requirements", [])

        if not requirements:
            return {
                "requirements": [],
                "processed_requirements": 0,
                "token_usage": state["token_usage"],
                "workflow_status": "completed",
                "current_step": "process_requirements",
                "error": None,
                "node_latencies": update_latency(
                    state,
                    "process_requirements",
                    start_time,
                ),
            }

        # Process all requirements in parallel
        results = await asyncio.gather(
            *[
                _process_requirement(
                    requirement=requirement,
                    state=state,
                    index=index,
                )
                for index, requirement in enumerate(requirements)
            ]
        )

        # Merge token usage after all tasks complete
        for result in results:
            TokenUsageService.merge_usage(
                state["token_usage"],
                result["usage"],
            )

        # Extract Mongo documents
        mongo_documents = [
            result["document"]
            for result in results
        ]

        # Bulk save to MongoDB
        await asyncio.to_thread(
            requirement_repository.bulk_upsert_requirements,
            mongo_documents,
        )

        # Remove Mongo-only fields from response
        response_requirements = [
            {
                key: value
                for key, value in document.items()
                if key not in {
                    "CompanyId",
                    "TenderId",
                    "DocumentId",
                    "ChunkId",
                }
            }
            for document in mongo_documents
        ]

        return {
            "requirements": response_requirements,
            "processed_requirements": len(response_requirements),
            "token_usage": state["token_usage"],
            "workflow_status": "completed",
            "current_step": "process_requirements",
            "error": None,
            "node_latencies": update_latency(
                state,
                "process_requirements",
                start_time,
            ),
        }

    except Exception as ex:

        return {
            "requirements": [],
            "processed_requirements": 0,
            "token_usage": state["token_usage"],
            "workflow_status": "failed",
            "current_step": "process_requirements",
            "error": str(ex),
            "node_latencies": update_latency(
                state,
                "process_requirements",
                start_time,
            ),
        }