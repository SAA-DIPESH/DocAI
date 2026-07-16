from pathlib import Path
import json

from app.infrastructure.token_usage import TokenUsageService
from ..llm.llm_factory import llm
from ..prompts.get_grammer_correction_prompt import GRAMMER_CORRECTION_AGENT_GENERATION_PROMPT

BASE_DIR = Path(__file__).resolve().parent.parent / "prompts"


CONSTITUTION = (
    BASE_DIR / "grammer_agent_input_files" / "constitution.md"
).read_text(encoding="utf-8")

SPECIFICATION = (
    BASE_DIR / "grammer_agent_input_files" / "specification.md"
).read_text(encoding="utf-8")

SYSTEM_PROMPT = (
    BASE_DIR / "grammer_agent_input_files" / "system_prompt.md"
).read_text(encoding="utf-8")


async def grammer_agent(content):
    formatted_messages = GRAMMER_CORRECTION_AGENT_GENERATION_PROMPT.invoke(
        {
            "constitution": CONSTITUTION,
            "specification": SPECIFICATION,
            "user_prompt": SYSTEM_PROMPT,
            "content": content
        }
    )
    response = await llm.ainvoke(formatted_messages)
    token_usage = TokenUsageService.extract_token_usage(response)
    # print(type(response))
    # print(response.response_metadata)
    # print(response.usage_metadata)

    return {
        "data": json.loads(response.content),
        "token_usage": token_usage,
    }
