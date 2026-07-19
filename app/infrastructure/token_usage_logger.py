import os
import time
from typing import Any, Dict, List

import httpx


class AIUsageLogger:
    """Logs AI model token usage to the custom AI Usage API."""

    @staticmethod
    def get_token_usage(response: Any) -> Dict[str, Any]:
        """
        Extract token usage from a LangChain AIMessage.
        Supports OpenAI, Mistral and Groq.
        """

        usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": "",
        }

        # OpenAI / New LangChain
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            metadata = response.usage_metadata

            usage["input_tokens"] = metadata.get("input_tokens", 0)
            usage["output_tokens"] = metadata.get("output_tokens", 0)
            usage["total_tokens"] = metadata.get("total_tokens", 0)

        # Provider metadata (OpenAI, Mistral, Groq)
        response_metadata = getattr(response, "response_metadata", {}) or {}

        token_usage = response_metadata.get("token_usage", {})

        if token_usage:
            usage["input_tokens"] = token_usage.get(
                "prompt_tokens",
                usage["input_tokens"],
            )

            usage["output_tokens"] = token_usage.get(
                "completion_tokens",
                usage["output_tokens"],
            )

            usage["total_tokens"] = token_usage.get(
                "total_tokens",
                usage["total_tokens"],
            )

        usage["model"] = (
            response_metadata.get("model_name")
            or response_metadata.get("model")
            or ""
        )

        return usage

    @staticmethod
    async def log_usage(
        *,
        response: Any,
        application_name: str,
        source_ids: List[str],
        correlation_id: str,
        user_id: str,
        company_id: str,
        tender_id: str,
        project_id: str,
        purpose: str,
        method: str,
        agent_name: str,
        usage_type: str,
        start_time: float,
    ) -> None:
        """
        Log AI token usage to the custom API.
        """

        api_url = os.getenv("AI_USAGE_LOG_API")

        if not api_url:
            return

        token_usage = AIUsageLogger.get_token_usage(response)

        duration = round(time.perf_counter() - start_time, 3)

        payload = {
            "applicationName": application_name,
            "sourceIds": source_ids,
            "runId": correlation_id,
            "userId": user_id,
            "purpose": purpose,
            "method": method,
            "agentName": agent_name,
            "usageType": usage_type,
            "inputToken": token_usage["input_tokens"],
            "outputToken": token_usage["output_tokens"],
            "totalTokens": token_usage["total_tokens"],
            "model": token_usage["model"],
            "duration": duration,
            "cost": 0,
            "companyId": company_id,
            "tenderId": tender_id,
            "projectId": project_id,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()

        except Exception as e:
            print(f"Failed to log AI usage: {e}")