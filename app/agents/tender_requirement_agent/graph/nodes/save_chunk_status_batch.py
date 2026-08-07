import asyncio
import time
from typing import Any, Dict

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.services.requirement_repository_mongo import (
    requirement_repository,
)


async def save_chunk_status_batch_node(
    state: TenderRequirementBatchState,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    try:

        tasks = []

        for chunk in state["chunks"]:

            chunk_data = {
                "CompanyId": state["company_id"],
                "TenderId": state["tender_id"],
                "DocumentId": chunk["document_id"],
                "ChunkId": chunk["chunk_id"],
                "UserId": state["user_id"],
                "UserName": state["user_name"],
                "SourceDocument": chunk["source_document"],
                "PageNumber": chunk.get("page_number"),
                "Heading": chunk.get("heading"),
                "Status": state["status"],
                "RequirementCount": len(
                    chunk.get("requirements", [])
                ),
                "Error": chunk.get("error"),
            }

            tasks.append(
                asyncio.to_thread(
                    requirement_repository.upsert_chunk_status,
                    chunk_data,
                )
            )

        await asyncio.gather(*tasks)

        return {
            "workflow_status": "completed",
            "current_step": "save_chunk_status",
            "total_processing_time": round(
                time.perf_counter() - start_time,
                3,
            ),
            "error": None,
        }

    except Exception as ex:

        return {
            "workflow_status": "failed",
            "current_step": "save_chunk_status",
            "error": str(ex),
        }