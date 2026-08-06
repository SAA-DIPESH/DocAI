import asyncio
import time
from typing import Any, Dict, List

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.services.requirement_repository_mongo import (
    requirement_repository,
)

from app.agents.tender_requirement_agent.utils.helper import (
    update_latency,
)


def build_requirement_document(
    state: TenderRequirementBatchState,
    chunk: Dict[str, Any],
    requirement: Dict[str, Any],
    index: int,
) -> Dict[str, Any]:

    requirement_id = (
        f"{chunk['document_id']}-"
        f"{chunk['chunk_id']}-"
        f"REQ-{index + 1:03d}"
    )

    return {

        "CompanyId": state["company_id"],
        "TenderId": state["tender_id"],
        "DocumentId": chunk["document_id"],
        "ChunkId": chunk["chunk_id"],
        "RequirementId": requirement_id,

        "UserId": state["user_id"],
        "UserName": state["user_name"],

        "RequirementText": requirement["RequirementText"],
        "RequirementType": requirement["RequirementType"],
        "RequirementStrength": requirement["RequirementStrength"],
        "MandatoryFlag": requirement["MandatoryFlag"],
        "Priority": requirement["Priority"],
        "Confidence": requirement["Confidence"],

        "CapabilityIntent": requirement.get(
            "CapabilityIntent",
            [],
        ),

        "EvidenceSections": requirement.get(
            "EvidenceSections",
            [],
        ),

        "SemanticAnchors": requirement.get(
            "SemanticAnchors",
            [],
        ),

        "IntentConfidence": requirement.get(
            "IntentConfidence",
            0.0,
        ),

        "Heading": chunk.get("heading"),
        "PageNumber": chunk.get("page_number"),

        "Status": state["status"],
    }


async def process_requirements_batch_node(
    state: TenderRequirementBatchState,
):

    start_time = time.perf_counter()

    try:

        mongo_documents = []

        updated_chunks = []

        for chunk in state["chunks"]:

            requirements = chunk.get(
                "requirements",
                [],
            )

            saved_ids = []

            for index, requirement in enumerate(
                requirements
            ):

                document = build_requirement_document(
                    state,
                    chunk,
                    requirement,
                    index,
                )

                mongo_documents.append(
                    document
                )

                saved_ids.append(
                    document["RequirementId"]
                )

            updated_chunks.append(
                {
                    **chunk,
                    "saved_requirement_ids": saved_ids,
                    "processed_requirements": len(
                        saved_ids
                    ),
                }
            )

        if mongo_documents:

            await asyncio.to_thread(
                requirement_repository.bulk_upsert_requirements,
                mongo_documents,
            )

        return {

            "chunks": updated_chunks,

            "workflow_status": "processing",

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

            "chunks": state["chunks"],

            "workflow_status": "failed",

            "current_step": "process_requirements",

            "error": str(ex),

            "node_latencies": update_latency(
                state,
                "process_requirements",
                start_time,
            ),
        }