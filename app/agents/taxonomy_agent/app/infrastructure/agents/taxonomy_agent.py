import json

from app.agents.taxonomy_agent.app.infrastructure.llm.llm_factory import llm
from app.agents.taxonomy_agent.app.infrastructure.prompts.get_taxonomy_agent_prompt import TAXONOMY_AGENT_PROMPT
from app.infrastructure.token_usage import TokenUsageService

TokenUsageService=TokenUsageService()


async def taxonomy_agent(input_json: dict):
    formatted_messages = TAXONOMY_AGENT_PROMPT.invoke(
        {
            "input_json": json.dumps(input_json, indent=2)
        }
    )

    response = await llm.ainvoke(formatted_messages)
    token_usage = TokenUsageService.extract_token_usage(response)

    return {
        "data": json.loads(response.content),
        "token_usage": token_usage,
    }
