from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Protocol

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from .exceptions import (
    ConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    StructuredOutputError,
)
from .settings import Settings


@dataclass(frozen=True)
class LLMResult:
    plan: BaseModel
    response_id: str
    usage: dict[str, int]
    provider: str
    model: str


class SectionPlannerLLMProvider(Protocol):
    async def generate_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        output_model: type[BaseModel],
    ) -> LLMResult: ...

    async def repair_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        previous_output: dict[str, Any],
        validation_errors: list[str],
        output_model: type[BaseModel],
    ) -> LLMResult: ...


def build_repair_input(
    runtime_prompt: str,
    previous_output: dict[str, Any],
    validation_errors: list[str],
) -> str:
    return (
        f"{runtime_prompt}\n\n"
        "[INVALID DECISION]\n"
        f"{json.dumps(previous_output, ensure_ascii=False, separators=(',', ':'))}\n"
        "[VALIDATION ISSUES]\n"
        f"{json.dumps(validation_errors, ensure_ascii=False, separators=(',', ':'))}\n"
        "[REPAIR]\nFix only these issues. Preserve valid source IDs and return the complete "
        "structured decision."
    )


def estimate_input_tokens(
    instructions: str,
    runtime_prompt: str,
    output_model: type[BaseModel] | None = None,
) -> int:
    """Conservative local estimate without an external tokenizer/API call."""

    schema = (
        json.dumps(output_model.model_json_schema(), separators=(",", ":"))
        if output_model
        else ""
    )
    return max(1, math.ceil((len(instructions) + len(runtime_prompt) + len(schema)) / 4))


def ensure_input_budget(
    settings: Settings,
    instructions: str,
    runtime_prompt: str,
    output_model: type[BaseModel],
) -> None:
    estimated = estimate_input_tokens(instructions, runtime_prompt, output_model)
    if estimated > settings.llm_max_input_tokens:
        raise LLMServiceError(
            "Compact LLM input exceeds configured token budget: "
            f"estimated={estimated}, maximum={settings.llm_max_input_tokens}"
        )


class OpenAISectionPlanner:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings
        self.client = client or AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )

    async def generate_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        output_model: type[BaseModel],
    ) -> LLMResult:
        ensure_input_budget(self.settings, instructions, runtime_prompt, output_model)
        request = {
            "model": self.settings.openai_model,
            "instructions": instructions,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": runtime_prompt}],
                }
            ],
            "text_format": output_model,
            "max_output_tokens": self.settings.llm_max_output_tokens,
        }
        if self._supports_reasoning(self.settings.openai_model):
            request["reasoning"] = {"effort": self.settings.openai_reasoning_effort}
        try:
            response = await self.client.responses.parse(**request)
        except APITimeoutError as exc:
            raise LLMTimeoutError("OpenAI request timed out") from exc
        except RateLimitError as exc:
            raise LLMRateLimitError("OpenAI rate limit exceeded after retries") from exc
        except APIConnectionError as exc:
            raise LLMServiceError("Unable to connect to OpenAI") from exc
        except Exception as exc:
            raise LLMServiceError("OpenAI structured-output request failed") from exc
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise StructuredOutputError("OpenAI returned no parsed Section Planner output")
        if not isinstance(parsed, output_model):
            try:
                parsed = output_model.model_validate(parsed)
            except ValidationError as exc:
                raise StructuredOutputError("OpenAI returned invalid structured output") from exc
        return LLMResult(
            plan=parsed,
            response_id=str(getattr(response, "id", "")),
            usage=self._responses_usage(getattr(response, "usage", None)),
            provider="OpenAI",
            model=self.settings.openai_model,
        )

    async def repair_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        previous_output: dict[str, Any],
        validation_errors: list[str],
        output_model: type[BaseModel],
    ) -> LLMResult:
        return await self.generate_plan(
            instructions=instructions,
            runtime_prompt=build_repair_input(
                runtime_prompt, previous_output, validation_errors
            ),
            output_model=output_model,
        )

    @staticmethod
    def _supports_reasoning(model: str) -> bool:
        return model.lower().startswith(("gpt-5", "o1", "o3", "o4"))

    @staticmethod
    def _responses_usage(usage: Any) -> dict[str, int]:
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or input_tokens + output_tokens)
        return {
            "InputTokens": input_tokens,
            "OutputTokens": output_tokens,
            "TotalTokens": total_tokens,
        }


class NvidiaSectionPlanner:
    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings
        self.client = client or AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            timeout=settings.nvidia_timeout_seconds,
            max_retries=settings.nvidia_max_retries,
        )

    async def generate_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        output_model: type[BaseModel],
    ) -> LLMResult:
        ensure_input_budget(self.settings, instructions, runtime_prompt, output_model)
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.nvidia_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": runtime_prompt},
                ],
                temperature=self.settings.nvidia_temperature,
                top_p=self.settings.nvidia_top_p,
                max_tokens=min(
                    self.settings.nvidia_max_tokens,
                    self.settings.llm_max_output_tokens,
                ),
                extra_body={
                    "guided_json": output_model.model_json_schema(),
                    "chat_template_kwargs": {
                        "enable_thinking": self.settings.nvidia_enable_thinking,
                        "clear_thinking": self.settings.nvidia_clear_thinking,
                    },
                },
                stream=False,
            )
        except APITimeoutError as exc:
            raise LLMTimeoutError("NVIDIA Build request timed out") from exc
        except RateLimitError as exc:
            raise LLMRateLimitError("NVIDIA Build rate limit exceeded after retries") from exc
        except APIConnectionError as exc:
            raise LLMServiceError("Unable to connect to NVIDIA Build") from exc
        except Exception as exc:
            raise LLMServiceError("NVIDIA Build generation request failed") from exc
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise StructuredOutputError("NVIDIA Build returned no Section Planner output")
        try:
            parsed = output_model.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            raise StructuredOutputError("NVIDIA Build returned invalid structured JSON") from exc
        return LLMResult(
            plan=parsed,
            response_id=str(getattr(response, "id", "")),
            usage=self._chat_usage(getattr(response, "usage", None)),
            provider="NVIDIA Build",
            model=self.settings.nvidia_model,
        )

    async def repair_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        previous_output: dict[str, Any],
        validation_errors: list[str],
        output_model: type[BaseModel],
    ) -> LLMResult:
        return await self.generate_plan(
            instructions=instructions,
            runtime_prompt=build_repair_input(
                runtime_prompt, previous_output, validation_errors
            ),
            output_model=output_model,
        )

    @staticmethod
    def _chat_usage(usage: Any) -> dict[str, int]:
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or input_tokens + output_tokens)
        return {
            "InputTokens": input_tokens,
            "OutputTokens": output_tokens,
            "TotalTokens": total_tokens,
        }


class MistralSectionPlanner:
    """Mistral AI provider using its OpenAI-compatible chat endpoint."""

    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self.settings = settings
        self.client = client or AsyncOpenAI(
            api_key=settings.mistral_api_key,
            base_url=settings.mistral_base_url,
            timeout=settings.mistral_timeout_seconds,
            max_retries=settings.mistral_max_retries,
        )

    async def generate_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        output_model: type[BaseModel],
    ) -> LLMResult:
        ensure_input_budget(self.settings, instructions, runtime_prompt, output_model)
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.mistral_model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": runtime_prompt},
                ],
                temperature=self.settings.mistral_temperature,
                max_tokens=self.settings.llm_max_output_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "dynamic_section_planner_decision",
                        "schema": output_model.model_json_schema(),
                    },
                },
                stream=False,
            )
        except APITimeoutError as exc:
            raise LLMTimeoutError("Mistral request timed out") from exc
        except RateLimitError as exc:
            raise LLMRateLimitError("Mistral rate limit exceeded after retries") from exc
        except APIConnectionError as exc:
            raise LLMServiceError("Unable to connect to Mistral") from exc
        except Exception as exc:
            raise LLMServiceError("Mistral structured-output request failed") from exc
        content = response.choices[0].message.content if response.choices else None
        if not isinstance(content, str) or not content.strip():
            raise StructuredOutputError("Mistral returned no Section Planner output")
        try:
            parsed = output_model.model_validate_json(content)
        except (ValidationError, ValueError) as exc:
            raise StructuredOutputError("Mistral returned invalid structured JSON") from exc
        return LLMResult(
            plan=parsed,
            response_id=str(getattr(response, "id", "")),
            usage=self._chat_usage(getattr(response, "usage", None)),
            provider="Mistral AI",
            model=self.settings.mistral_model,
        )

    async def repair_plan(
        self,
        *,
        instructions: str,
        runtime_prompt: str,
        previous_output: dict[str, Any],
        validation_errors: list[str],
        output_model: type[BaseModel],
    ) -> LLMResult:
        return await self.generate_plan(
            instructions=instructions,
            runtime_prompt=build_repair_input(
                runtime_prompt, previous_output, validation_errors
            ),
            output_model=output_model,
        )

    @staticmethod
    def _chat_usage(usage: Any) -> dict[str, int]:
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(
            getattr(usage, "total_tokens", 0) or input_tokens + output_tokens
        )
        return {
            "InputTokens": input_tokens,
            "OutputTokens": output_tokens,
            "TotalTokens": total_tokens,
        }


def create_llm_provider(settings: Settings) -> SectionPlannerLLMProvider:
    if settings.llm_provider == "openai":
        return OpenAISectionPlanner(settings)
    if settings.llm_provider == "nvidia":
        return NvidiaSectionPlanner(settings)
    if settings.llm_provider == "mistral":
        return MistralSectionPlanner(settings)
    raise ConfigurationError("LLM_PROVIDER must be openai, nvidia, or mistral")
