import os
import httpx
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TokenUsageService:
    @staticmethod
    def _get_value(source: Any, key: str, default: Any = None) -> Any:
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    @staticmethod
    def extract_token_usage(response: Any) -> dict:
        metadata = (
            TokenUsageService._get_value(response, "response_metadata", {}) or {}
        )

        usage = (
            TokenUsageService._get_value(response, "usage_metadata", None)
            or TokenUsageService._get_value(response, "usage", None)
            or metadata.get("token_usage")
            or metadata.get("usage")
            or {}
        )

        input_tokens = (
            TokenUsageService._get_value(usage, "input_tokens", None)
            or TokenUsageService._get_value(usage, "prompt_tokens", None)
            or 0
        )

        output_tokens = (
            TokenUsageService._get_value(usage, "output_tokens", None)
            or TokenUsageService._get_value(usage, "completion_tokens", None)
            or 0
        )

        total_tokens = (
            TokenUsageService._get_value(usage, "total_tokens", None)
            or input_tokens + output_tokens
        )

        model = (
            metadata.get("model_name")
            or metadata.get("model")
            or TokenUsageService._get_value(response, "model_name", "")
            or ""
        )

        return {
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "model": model,
        }

    @staticmethod
    async def log_usage(payload: dict, bearer_token: str | None = None):
        api_url = os.getenv(
            "AI_USAGE_LOG_API",
            "https://vibeappop.saa.ai/DocAI/api/Contract/InsertAiUsageLog",
        )

        if not api_url:
            return None

        payload = {
            key: value
            for key, value in payload.items()
            if value is not None
        }

        headers = {}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    api_url,
                    json=payload,
                    headers=headers,
                )

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as ex:
                logger.warning(
                    "Token usage logging failed with status %s: %s",
                    ex.response.status_code,
                    ex.response.text,
                )
                return {
                    "success": False,
                    "status_code": ex.response.status_code,
                    "message": "Token usage logging failed",
                }

            except httpx.HTTPError as ex:
                logger.warning("Token usage logging request failed: %s", ex)
                return {
                    "success": False,
                    "message": "Token usage logging request failed",
                }
                
 
 
 
######################################## Token Uasge ########################################
 
                
# usage = TokenUsageService.extract_token_usage(response)

# await TokenUsageService.log_usage(
#     payload=usage,
#     bearer_token=token,
#
