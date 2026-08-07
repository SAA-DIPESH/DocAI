import asyncio
from collections import defaultdict
from typing import Any, Dict, List

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.graph.workflow import (
    tender_requirement_graph,
)

from app.agents.tender_requirement_agent.services.tender_retriever_qdrant import (
    tender_retriever,
)

from app.agents.tender_requirement_agent.utils.helper import (
    create_batches,
)

from app.infrastructure.logger import Logging


logger = Logging(
    agent_name="Requirements_Detection_And_Intent_Agent",
    source_module="requirement_service",
)


class RequirementService:

    def __init__(
        self,
        processing_batch_size: int = 5,
        max_concurrency: int = 20,
        batch_parallelism: int = 4,
    ) -> None:

        # Number of chunks sent in a single LLM call
        self.processing_batch_size = processing_batch_size

        # LangGraph parallelism
        self.max_concurrency = max_concurrency

        # Number of graph executions running simultaneously
        self.batch_semaphore = asyncio.Semaphore(
            batch_parallelism
        )

    # ==========================================================
    # Create Batch State
    # ==========================================================

    @staticmethod
    def create_batch_state(
        batch: List[Dict[str, Any]],
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> TenderRequirementBatchState:

        if not batch:
            raise ValueError(
                "Batch cannot be empty."
            )

        return {

            # --------------------------------------------
            # Tender Metadata
            # --------------------------------------------

            "company_id": company_id,
            "tender_id": batch[0].get(
                "tender_id"
            ),
            "user_id": user_id,
            "user_name": user_name,
            "status": status,

            # --------------------------------------------
            # Batch Chunks
            # --------------------------------------------

            "chunks": [
                {

                    "document_id": chunk.get(
                        "document_id"
                    ),

                    "chunk_id": chunk.get(
                        "chunk_id"
                    ),

                    "source_document": chunk.get(
                        "document_name"
                    ),

                    "page_number": chunk.get(
                        "page_number"
                    ),

                    "heading": chunk.get(
                        "related_section"
                    ),

                    "chunk_text": chunk.get(
                        "text",
                        "",
                    ),

                    "requirements": [],

                    "saved_requirement_ids": [],

                    "failed_requirement_ids": [],

                    "error": None,

                }
                for chunk in batch
            ],

            # --------------------------------------------
            # Workflow
            # --------------------------------------------

            "workflow_status": "pending",

            "current_step": "start",

            # --------------------------------------------
            # Performance
            # --------------------------------------------

            "node_latencies": {},

            "total_processing_time": 0,

            # --------------------------------------------
            # Error
            # --------------------------------------------

            "error": None,
        }

    # ==========================================================
    # Aggregate Token Usage
    # ==========================================================

    @staticmethod
    def aggregate_token_usage(
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

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

            usage = result.get(
                "token_usage"
            )

            if not usage:
                continue

            total_usage["input_tokens"] += usage.get(
                "input_tokens",
                0,
            )

            total_usage["output_tokens"] += usage.get(
                "output_tokens",
                0,
            )

            total_usage["total_tokens"] += usage.get(
                "total_tokens",
                0,
            )

            for (
                model,
                model_usage,
            ) in usage.get(
                "models",
                {},
            ).items():

                model_usage_totals[model][
                    "input_tokens"
                ] += model_usage.get(
                    "input_tokens",
                    0,
                )

                model_usage_totals[model][
                    "output_tokens"
                ] += model_usage.get(
                    "output_tokens",
                    0,
                )

                model_usage_totals[model][
                    "total_tokens"
                ] += model_usage.get(
                    "total_tokens",
                    0,
                )

        total_usage["models"] = dict(
            model_usage_totals
        )

        return total_usage

    # ==========================================================
    # Process One Batch
    # ==========================================================

    async def process_batch(
        self,
        batch: List[Dict[str, Any]],
        company_id: str,
        user_id: str,
        user_name: str,
        status: str,
    ) -> Dict[str, Any]:
        """
        Process one batch of chunks.

        One batch == One Graph Execution == One LLM Call
        """

        async with self.batch_semaphore:

            batch_state = self.create_batch_state(
                batch=batch,
                company_id=company_id,
                user_id=user_id,
                user_name=user_name,
                status=status,
            )

            result = await tender_requirement_graph.ainvoke(
                batch_state,
                config={
                    "max_concurrency": self.max_concurrency,
                },
            )

            return result


    # ==========================================================
    # Process Tender
    # ==========================================================

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

            chunks = retrieval_result.get(
                "chunks",
                [],
            )

            # --------------------------------------------------
            # No Chunks
            # --------------------------------------------------

            if not chunks:

                response = {
                    "CompanyId": company_id,
                    "TenderId": tender_id,
                    "TotalChunks": 0,
                    "ProcessedChunks": 0,
                    "TotalRequirements": 0,
                    "ChunksWithRequirements": 0,
                    "ChunksWithoutRequirements": 0,
                    "FailedBatches": [],
                    "Status": "NoChunksFound",
                    "TokenUsage": {},
                }

                logger.end(
                    tracking_token=tracking_token,
                    is_success=True,
                    message="No chunks found.",
                    event_type="TenderProcessingCompleted",
                )

                return response

            # --------------------------------------------------
            # Execute Batch Graphs
            # --------------------------------------------------

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

            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

            # --------------------------------------------------
            # Aggregate Results
            # --------------------------------------------------

            all_results = []

            failed_batches = []

            for index, result in enumerate(
                batch_results
            ):

                if isinstance(
                    result,
                    Exception,
                ):

                    failed_batches.append(
                        {
                            "batch_index": index,
                            "error": str(result),
                        }
                    )

                    continue

                all_results.append(
                    result
                )

            # --------------------------------------------------
            # Metrics
            # --------------------------------------------------

            total_chunks = len(chunks)

            processed_chunks = 0

            total_requirements = 0

            chunks_with_requirements = 0

            chunks_without_requirements = 0

            for batch in all_results:

                for chunk in batch.get(
                    "chunks",
                    [],
                ):

                    processed_chunks += 1

                    req_count = len(
                        chunk.get(
                            "requirements",
                            [],
                        )
                    )

                    total_requirements += req_count

                    if req_count:

                        chunks_with_requirements += 1

                    else:

                        chunks_without_requirements += 1

            # --------------------------------------------------
            # Token Usage
            # --------------------------------------------------

            total_token_usage = (
                self.aggregate_token_usage(
                    all_results
                )
            )

            # --------------------------------------------------
            # Business Status
            # --------------------------------------------------

            if processed_chunks == total_chunks:

                business_status = "Completed"

            elif processed_chunks == 0:

                business_status = "Failed"

            else:

                business_status = "PartiallyCompleted"

            # --------------------------------------------------
            # Response
            # --------------------------------------------------

            response = {

                "CompanyId": company_id,

                "TenderId": tender_id,

                "TotalChunks": total_chunks,

                "ProcessedChunks": processed_chunks,

                "TotalRequirements": total_requirements,

                "ChunksWithRequirements": (
                    chunks_with_requirements
                ),

                "ChunksWithoutRequirements": (
                    chunks_without_requirements
                ),

                "FailedBatches": failed_batches,

                "Status": business_status,

                "TokenUsage": total_token_usage,

            }

            logger.end(
                tracking_token=tracking_token,
                is_success=(
                    business_status != "Failed"
                ),
                message="Tender processing completed",
                event_type="TenderProcessingCompleted",
                payload=response,
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