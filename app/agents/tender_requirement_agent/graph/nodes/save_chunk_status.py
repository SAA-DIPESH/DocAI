import asyncio
import time
from typing import Any, Dict

from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState
from app.agents.tender_requirement_agent.services.requirement_repository_mongo import requirement_repository


async def save_chunk_status_node(state: TenderRequirementState) -> Dict[str, Any]:
    start_time = time.perf_counter()

    try:
        chunk_data = {
            "CompanyId": state["company_id"],
            "TenderId": state["tender_id"],
            "DocumentId": state["document_id"],
            "ChunkId": state["chunk_id"],
            "UserId": state["user_id"],
            "UserName": state["user_name"],
            "SourceDocument": state["source_document"],
            "PageNumber": state.get("page_number"),
            "Heading": state.get("heading"),
            "Status": state["status"],
            "RequirementCount": len(state.get("requirements", [])),
            "Error": state.get("error"),
        }
        await asyncio.to_thread(
            requirement_repository.upsert_chunk_status,
            chunk_data,
        )

        return {
            "current_step": "save_chunk_status",
            "total_processing_time": round(
                time.perf_counter() - start_time,
                3,
            ),
        }

    except Exception as ex:
        return {
            "workflow_status": "failed",
            "error": str(ex),
        }