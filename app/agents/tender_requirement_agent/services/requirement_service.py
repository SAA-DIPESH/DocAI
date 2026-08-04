import asyncio
from collections import defaultdict
from typing import Any, Dict, List

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementState,
)
from app.agents.tender_requirement_agent.graph.workflow import (
    tender_requirement_graph,
)
from app.agents.tender_requirement_agent.services.tender_retriever_qdrant import (
    tender_retriever,
)
from app.agents.tender_requirement_agent.utils.helper import create_batches
from app.infrastructure.logger import Logging


logger = Logging(
    agent_name="Requirements_Detection_And_Intent_Agent",
    source_module="requirement_service",
)


class RequirementService:
    def __init__(
        self,
        processing_batch_size: int = 20,
        max_concurrency: int = 20,
        batch_parallelism: int = 4,
    ) -> None:
        self.processing_batch_size = processing_batch_size
        self.max_concurrency = max_concurrency

        # Limits the number of batches processed simultaneously.
        self.batch_semaphore = asyncio.Semaphore(batch_parallelism)

    @staticmethod
    def create_initial_state(
        chunk: Dict[str, Any],
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> TenderRequirementState:
        """
        Create the initial workflow state for a single chunk.
        """

        return {
            "company_id": company_id,
            "tender_id": chunk.get("tender_id"),
            "user_id": user_id,
            "user_name": user_name,
            "status": status,
            "document_id": chunk.get("document_id"),
            "chunk_id": chunk.get("chunk_id"),
            "source_document": chunk.get("document_name"),
            "page_number": chunk.get("page_number"),
            "heading": chunk.get("related_section"),
            "chunk_text": chunk.get("text", ""),
            "requirements": [],
            "workflow_status": "pending",
            "error": None,
            "node_latencies": {},
        }

    @staticmethod
    def aggregate_token_usage(
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Aggregate token usage across all processed chunks.
        """

        model_usage_totals = defaultdict(
            lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }
        )

        total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "models": model_usage_totals,
        }

        for result in results:
            usage = result.get("token_usage")

            if not usage:
                continue

            total_usage["input_tokens"] += usage.get(
                "input_tokens", 0
            )
            total_usage["output_tokens"] += usage.get(
                "output_tokens", 0
            )
            total_usage["total_tokens"] += usage.get(
                "total_tokens", 0
            )

            for model, model_usage in usage.get(
                "models", {}
            ).items():
                model_usage_totals[model]["input_tokens"] += (
                    model_usage.get("input_tokens", 0)
                )
                model_usage_totals[model]["output_tokens"] += (
                    model_usage.get("output_tokens", 0)
                )
                model_usage_totals[model]["total_tokens"] += (
                    model_usage.get("total_tokens", 0)
                )

        total_usage["models"] = dict(model_usage_totals)

        return total_usage

    async def process_batch(
        self,
        batch: List[Dict[str, Any]],
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> List[Dict[str, Any]]:
        """
        Process a single batch.

        A semaphore limits the number of batches that
        execute simultaneously.
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
        """
        Process all tender chunks, detect requirements, and return summary metrics.
        """

        tracking_token = logger.start(
            message="Tender processing started",
            event_type="TenderProcessingStarted",
        )

        try:
            retrieval_result = tender_retriever.retrieve_chunks(
                tender_id=tender_id,
            )

            chunks = retrieval_result.get("chunks", [])

            if not chunks:
                response = {
                    "CompanyId": company_id,
                    "TenderId": tender_id,
                    "TotalChunks": 0,
                    "ProcessedChunks": 0,
                    "RequirementsProcessed": 0,
                    "RequirementsGenerated": 0,
                    "ChunksWithoutRequirements": 0,
                    "Status": "NoChunksFound",
                    "TokenUsage": {},
                }

                logger.end(
                    tracking_token=tracking_token,
                    is_success=True,
                    message="No chunks found for tender",
                    event_type="TenderProcessingCompleted",
                    payload={
                        "company_id": company_id,
                        "tender_id": tender_id,
                        "status": "NoChunksFound",
                    },
                )

                return response

            # ----------------------------------------------------
            # Create & execute batch processing tasks
            # ----------------------------------------------------
            tasks = [
                self.process_batch(
                    batch=batch,
                    company_id=company_id,
                    user_id=user_id,
                    user_name=user_name,
                    status=status,
                )
                for batch in create_batches(chunks, self.processing_batch_size)
            ]

            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            # ----------------------------------------------------
            # Flatten results & track batch failures
            # ----------------------------------------------------
            all_results = []
            failed_batches = []

            for index, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    failed_batches.append(
                        {
                            "batch_index": index,
                            "error": str(result),
                        }
                    )
                    continue

                all_results.extend(result)

            # ----------------------------------------------------
            # Metric Calculations
            # ----------------------------------------------------
            total_chunks = len(chunks)
            processed_chunks = len(all_results)

            requirements_processed = 0
            chunks_with_requirements = 0
            chunks_without_requirements = 0

            for res in all_results:
                reqs = res.get("requirements", []) or []
                req_count = len(reqs)

                requirements_processed += req_count

                if req_count > 0:
                    chunks_with_requirements += 1
                else:
                    chunks_without_requirements += 1

            # ----------------------------------------------------
            # Token usage aggregation & Business status calculation
            # ----------------------------------------------------
            total_token_usage = self.aggregate_token_usage(all_results)

            if processed_chunks == total_chunks:
                business_status = "Completed"
            elif processed_chunks == 0:
                business_status = "Failed"
            else:
                business_status = "PartiallyCompleted"

            # ----------------------------------------------------
            # Final Aggregated Summary Response
            # ----------------------------------------------------
            response = {
                "CompanyId": company_id,
                "TenderId": tender_id,
                "TotalChunks": total_chunks,
                "ProcessedChunks": processed_chunks,
                "TotalRequirements": requirements_processed,            # Updated key name (406)
                "ChunksWithRequirements": chunks_with_requirements,      # Updated key name (121)
                "ChunksWithoutRequirements": chunks_without_requirements, # Updated key name (144)
                "FailedBatches": failed_batches,
                "Status": business_status,
                "TokenUsage": total_token_usage,
            }

            logger.end(
                tracking_token=tracking_token,
                is_success=business_status != "Failed",
                message="Tender processing completed",
                event_type="TenderProcessingCompleted",
                payload={
                    "company_id": company_id,
                    "tender_id": tender_id,
                    "total_chunks": total_chunks,
                    "processed_chunks": processed_chunks,
                    "total_requirements": requirements_processed,
                    "chunks_with_requirements": chunks_with_requirements,
                    "chunks_without_requirements": chunks_without_requirements,
                    "failed_batches": len(failed_batches),
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