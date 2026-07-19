from types import SimpleNamespace

import pytest

from section_planner.llm import (
    MistralSectionPlanner,
    NvidiaSectionPlanner,
    OpenAISectionPlanner,
    create_llm_provider,
)
from section_planner.models import DynamicSectionPlannerLLMDecision
from .test_section_planner import settings, valid_dynamic_decision


class Responses:
    def __init__(self, plan: DynamicSectionPlannerLLMDecision):
        self.plan = plan
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="resp-sdk-mock",
            output_parsed=self.plan,
            usage=SimpleNamespace(input_tokens=11, output_tokens=7, total_tokens=18),
        )


@pytest.mark.asyncio
async def test_official_responses_parse_is_called_with_pydantic_structured_output():
    responses = Responses(valid_dynamic_decision())
    client = SimpleNamespace(responses=responses)
    planner = OpenAISectionPlanner(settings(), client=client)

    result = await planner.generate_plan(
        instructions="complete instructions",
        runtime_prompt="complete runtime prompt",
        output_model=DynamicSectionPlannerLLMDecision,
    )

    assert result.response_id == "resp-sdk-mock"
    assert result.usage == {"InputTokens": 11, "OutputTokens": 7, "TotalTokens": 18}
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["model"] == "gpt-test"
    assert call["text_format"] is DynamicSectionPlannerLLMDecision
    assert call["max_output_tokens"] == 3000
    assert call["instructions"] == "complete instructions"
    assert call["input"][0]["content"][0]["text"] == "complete runtime prompt"
    assert "reasoning" not in call


@pytest.mark.asyncio
async def test_reasoning_effort_is_sent_only_to_supported_models():
    responses = Responses(valid_dynamic_decision())
    client = SimpleNamespace(responses=responses)
    app_settings = settings()
    object.__setattr__(app_settings, "openai_model", "gpt-5.1")
    planner = OpenAISectionPlanner(app_settings, client=client)

    await planner.generate_plan(
        instructions="instructions",
        runtime_prompt="prompt",
        output_model=DynamicSectionPlannerLLMDecision,
    )

    assert responses.calls[0]["reasoning"] == {"effort": "medium"}


class ChatCompletions:
    def __init__(self, plan: DynamicSectionPlannerLLMDecision):
        self.plan = plan
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="chatcmpl-nvidia-mock",
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.plan.model_dump_json()))],
            usage=SimpleNamespace(prompt_tokens=21, completion_tokens=9, total_tokens=30),
        )


@pytest.mark.asyncio
async def test_nvidia_provider_uses_chat_completions_and_validates_decision_model():
    completions = ChatCompletions(valid_dynamic_decision())
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    app_settings = settings()
    object.__setattr__(app_settings, "llm_provider", "nvidia")
    planner = NvidiaSectionPlanner(app_settings, client=client)

    result = await planner.generate_plan(
        instructions="complete instructions",
        runtime_prompt="complete runtime prompt",
        output_model=DynamicSectionPlannerLLMDecision,
    )

    assert result.provider == "NVIDIA Build"
    assert result.model == "meta/llama-3.3-70b-instruct"
    assert result.response_id == "chatcmpl-nvidia-mock"
    assert result.usage == {"InputTokens": 21, "OutputTokens": 9, "TotalTokens": 30}
    call = completions.calls[0]
    assert call["messages"][0] == {"role": "system", "content": "complete instructions"}
    assert call["messages"][1] == {"role": "user", "content": "complete runtime prompt"}
    assert call["extra_body"]["guided_json"] == (
        DynamicSectionPlannerLLMDecision.model_json_schema()
    )
    assert call["extra_body"]["chat_template_kwargs"] == {
        "enable_thinking": True,
        "clear_thinking": False,
    }
    assert call["temperature"] == 1.0
    assert call["top_p"] == 1.0
    assert call["max_tokens"] == 3000


@pytest.mark.asyncio
async def test_mistral_provider_uses_custom_json_schema_and_validates_decision_model():
    completions = ChatCompletions(valid_dynamic_decision())
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    app_settings = settings(llm_provider="mistral")
    planner = MistralSectionPlanner(app_settings, client=client)

    result = await planner.generate_plan(
        instructions="complete instructions",
        runtime_prompt="complete runtime prompt",
        output_model=DynamicSectionPlannerLLMDecision,
    )

    assert result.provider == "Mistral AI"
    assert result.model == "mistral-large-latest"
    assert result.response_id == "chatcmpl-nvidia-mock"
    assert result.usage == {"InputTokens": 21, "OutputTokens": 9, "TotalTokens": 30}
    call = completions.calls[0]
    assert call["model"] == "mistral-large-latest"
    assert call["messages"][0] == {"role": "system", "content": "complete instructions"}
    assert call["messages"][1] == {"role": "user", "content": "complete runtime prompt"}
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 3000
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "dynamic_section_planner_decision",
            "schema": DynamicSectionPlannerLLMDecision.model_json_schema(),
        },
    }
    assert call["stream"] is False


def test_provider_factory_uses_explicit_selection():
    app_settings = settings()
    assert isinstance(create_llm_provider(app_settings), OpenAISectionPlanner)
    object.__setattr__(app_settings, "llm_provider", "nvidia")
    assert isinstance(create_llm_provider(app_settings), NvidiaSectionPlanner)
    object.__setattr__(app_settings, "llm_provider", "mistral")
    assert isinstance(create_llm_provider(app_settings), MistralSectionPlanner)
