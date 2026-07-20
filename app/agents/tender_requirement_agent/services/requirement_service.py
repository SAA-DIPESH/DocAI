import asyncio
from typing import Any, Dict

from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState
from app.agents.tender_requirement_agent.graph.workflow import tender_requirement_graph
from app.agents.tender_requirement_agent.services.tender_retriever_qdrant import tender_retriever
from app.agents.tender_requirement_agent.utils.helper import create_batches
from app.infrastructure.logger import Logging


logger = Logging(
    agent_name="Requirements_Detection_And_Intent_Agent",
    source_module="requirement_service",
)


class RequirementService:

    def __init__(
        self,
        processing_batch_size: int = 25,
        max_concurrency: int = 20,
        batch_parallelism: int = 4,
    ) -> None:

        self.processing_batch_size = processing_batch_size
        self.max_concurrency = max_concurrency

        # Number of batches that can run simultaneously
        self.batch_semaphore = asyncio.Semaphore(
            batch_parallelism
        )

    @staticmethod
    def create_initial_state(
        chunk: Dict[str, Any],
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> TenderRequirementState:

        return {
            "company_id": company_id,
            "tender_id": chunk["tender_id"],
            "user_id": user_id,
            "user_name": user_name,
            "status": status,
            "document_id": chunk["document_id"],
            "chunk_id": chunk["chunk_id"],
            "source_document": chunk["document_name"],
            "page_number": chunk.get("page_number"),
            "heading": chunk.get("related_section"),
            "chunk_text": chunk["text"],
            "requirements": [],
            "workflow_status": "pending",
            "error": None,
            "node_latencies": {},
        }

    async def process_batch(
        self,
        batch,
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ):
        """
        Process a single batch.

        Semaphore ensures only a limited number of
        of batches execute simultaneously.
        """

        async with self.batch_semaphore:

            states = [
                self.create_initial_state(
                    chunk=chunk,
                    company_id=company_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=status,
                )
                for chunk in batch
            ]

            return await tender_requirement_graph.abatch(
                states,
                config={
                    "max_concurrency": self.max_concurrency,
                },
            )

    async def process_tender(
        self,
        company_id: str,
        tender_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> Dict[str, Any]:

        tracking_token = logger.start(
            message="Tender processing started",
            event_type="TenderProcessingStarted",
        )

        try:

            retrieval_result = tender_retriever.retrieve_chunks(
                tender_id=tender_id,
            )

            chunks = retrieval_result["chunks"]

            # ----------------------------------------------------
            # Create Tasks
            # ----------------------------------------------------

            tasks = [
                self.process_batch(
                    batch=batch,
                    company_id=company_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=status,
                )
                for batch in create_batches(
                    chunks,
                    self.processing_batch_size,
                )
            ]

            # ----------------------------------------------------
            # Execute batches in parallel
            # ----------------------------------------------------

            batch_results = await asyncio.gather(*tasks)

            # ----------------------------------------------------
            # Flatten results
            # ----------------------------------------------------

            all_results = [
                result
                for batch in batch_results
                for result in batch
            ]

            business_status = (
                "Completed"
                if len(all_results) == len(chunks)
                else "PartiallyCompleted"
            )

            response = {
                "CompanyId": company_id,
                "TenderId": tender_id,
                "TotalChunks": len(chunks),
                "ProcessedChunks": len(all_results),
                "Status": business_status,
                "Chunks": all_results,
            }

            logger.end(
                tracking_token=tracking_token,
                is_success=True,
                message="Tender processing completed",
                event_type="TenderProcessingCompleted",
                payload={
                    "company_id": company_id,
                    "tender_id": tender_id,
                    "total_chunks": len(chunks),
                    "processed_chunks": len(all_results),
                    "status": business_status,
                },
            )

            return response

        except Exception as ex:

            logger.end(
                tracking_token=tracking_token,
                is_success=False,
                message="Tender processing failed",
                event_type="TenderProcessingFailed",
                payload={
                    "company_id": company_id,
                    "tender_id": tender_id,
                    "error": str(ex),
                },
            )

            raise