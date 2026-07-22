import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TokenUsageService:
    
    # Model Pricing List change if price updated
    MODEL_PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "text-embedding-3-small": {"input": 0.02, "output": 0.0},
        "mistral-small-2506": {"input": 0.10, "output": 0.30},
        "mistral-large-2411": {"input": 2.00, "output": 6.00},
    }

    @staticmethod
    def extract_token_usage(response: Any) -> dict:

        metadata = getattr(response, "response_metadata", {}) or {}

        usage = (
            getattr(response, "usage_metadata", None)
            or metadata.get("token_usage")
            or metadata.get("usage")
            or {}
        )

        input_tokens = (
            getattr(usage, "input_tokens", None)
            or usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or 0
        )

        output_tokens = (
            getattr(usage, "output_tokens", None)
            or usage.get("output_tokens")
            or usage.get("completion_tokens")
            or 0
        )

        total_tokens = (
            getattr(usage, "total_tokens", None)
            or usage.get("total_tokens")
            or (input_tokens + output_tokens)
        )

        model = (
            metadata.get("model_name")
            or metadata.get("model")
            or getattr(response, "model_name", "")
        )

        return {
            "model": model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "total_tokens": int(total_tokens),
        }

    @staticmethod
    def merge_usage(total_usage: dict, usage: dict):

        total_usage["input_tokens"] += usage["input_tokens"]
        total_usage["output_tokens"] += usage["output_tokens"]
        total_usage["total_tokens"] += usage["total_tokens"]

        model = usage["model"] or "unknown"

        if model not in total_usage["models"]:
            total_usage["models"][model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

        total_usage["models"][model]["input_tokens"] += usage["input_tokens"]
        total_usage["models"][model]["output_tokens"] += usage["output_tokens"]
        total_usage["models"][model]["total_tokens"] += usage["total_tokens"]

    @staticmethod
    def update_state(state: dict, response: Any):

        usage = TokenUsageService.extract_token_usage(response)

        if "token_usage" not in state:
            state["token_usage"] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "models": {},
            }

        TokenUsageService.merge_usage(
            state["token_usage"],
            usage,
        )

        return usage

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int):

        if not model:
            return 0

        rates = TokenUsageService.MODEL_PRICING.get(model.lower())

        if not rates:
            return 0

        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]

        return round(input_cost + output_cost, 8)

    @staticmethod
    async def log_usage(api_url: str, payload: dict, token: str):

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                api_url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            return response.json()

    @staticmethod
    async def log_agent_usage(
        request,
        token_usage: dict,
        duration_ms: int,
        correlation_id: str,
        application_name: str,
        source_ids: list,
        purpose: str,
        method: str,
        agent_name: str,
        usage_type: str,
    ):

        total_cost = sum(
            TokenUsageService.calculate_cost(
                model=model,
                input_tokens=model_usage["input_tokens"],
                output_tokens=model_usage["output_tokens"],
            )
            for model, model_usage in token_usage.get("models", {}).items()
        )

        payload = {
            "applicationName": application_name,
            "sourceIds": [
                {
                    "sourceIdType": "TenderId",
                    "id": request.TenderId,
                }
            ],
            "runId": correlation_id,
            "userId": request.UserId,
            "purpose": purpose,
            "method": method,
            "agentName": agent_name,
            "usageType": usage_type,
            "inputToken": token_usage.get("input_tokens", 0),
            "outputToken": token_usage.get("output_tokens", 0),
            "totalTokens": token_usage.get("total_tokens", 0),
            "model": ",".join(token_usage.get("models", {}).keys()),
            "duration": duration_ms,
            "cost": {
                "currency": "USD",
                "value": total_cost,
            },
            "companyId": request.CompanyId,
            "tenderId": request.TenderId,
            "projectId": request.ProjectId,
        }

        api_url = os.getenv("AI_USAGE_LOG_API")

        if not api_url:
            raise ValueError(
                "AI_USAGE_LOG_API is not configured in the .env file."
            )

        return await TokenUsageService.log_usage(
            api_url=api_url,
            payload=payload,
            token=request.JwtToken,
        )