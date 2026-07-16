import json
import time

from app.agents.Section_writer.prompts.get_section_writer_agent_prompt import TENDER_SECTION_WRITER_PROMPT





# async def document_classifier_agent(
#     *,
#     document_metadata: dict,
#     classification_set: list[dict],
#     usage_context: dict | None = None,
# ):
#     document_text = document_metadata.get("summary", "")
#     formatted_messages = TENDER_SECTION_WRITER_PROMPT.invoke(
#         {
#             "document_name": document_metadata.get("document_title", ""),
#             "page_count": document_metadata.get("page_count", 0),
#             "table_count": document_metadata.get("table_count", 0),
#             "classification_set": json.dumps(
#                 classification_set,
#                 indent=2,
#             ),
#             "document_text": document_text,
#         }
#     )

#     started_at = time.perf_counter()
#     response = await llm.ainvoke(formatted_messages)
#     duration_ms = (time.perf_counter() - started_at) * 1000

#     usage = TokenUsageService.extract_token_usage(response)
#     cost = TokenUsageService.calculate_token_cost(
#         model=usage["model"],
#         input_tokens=usage["input_tokens"],
#         output_tokens=usage["output_tokens"],
#     )
#     usage_context = usage_context or {}
#     await TokenUsageService.log_usage(
#         {
#             "applicationName": usage_context.get("applicationName", "Tender"),
#             "sourceIds": usage_context.get("sourceIds", []),
#             "runId": usage_context.get("runId"),
#             "userId": usage_context.get("userId"),
#             "purpose": usage_context.get("purpose"),
#             "method": "ClassifyUploadedTenderDocumentAsync",
#             "agentName": "Tender Document Classification Agent",
#             "usageType": "llm",
#             "inputToken": usage["input_tokens"],
#             "outputToken": usage["output_tokens"],
#             "totalTokens": usage["total_tokens"],
#             "model": usage["model"],
#             "duration": duration_ms,
#             "cost": cost,
#             "companyId": usage_context.get("companyId"),
#             "tenderId": usage_context.get("tenderId"),
#             "projectId": usage_context.get("projectId"),
#         },
#         bearer_token=usage_context.get("bearerToken"),
#     )

#     classification_data = _normalize_classification_data(json.loads(response.content))

#     return {
#         "data": classification_data,
#         # "token_usage": extract_token_usage(response),
#     }
