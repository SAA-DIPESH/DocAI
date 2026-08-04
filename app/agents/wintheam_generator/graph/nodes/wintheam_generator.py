import time
from typing import Any, Dict

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.agents.wintheam_generator.prompts.prompt_loader import (
    CONSTITUTION,
    SPECIFICATION,
    SYS_PROMPT,
)
from app.infrastructure.load_llms import create_llm


llm = create_llm()

DEFAULT_RULES = {
    "minimum_evidence_items": 2,
    "minimum_distinct_documents": 2,
}

CHAIN = (
    ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=CONSTITUTION),
            SystemMessage(content=SPECIFICATION),
            SystemMessage(content=SYS_PROMPT),
            (
                "human",
                """
Generate one company capability win theme using the following input.

Input JSON:
{llm_input}

Return JSON only.
""",
            ),
        ]
    )
    | llm
    | JsonOutputParser()
)


def win_theme_generator_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Generate a single win theme for the current anchor group.
    """

    start = time.perf_counter()

    try:
        llm_input = {
            "company_id": state["company_id"],
            "context": state["context"],
            "anchor_group": state["current_anchor_group"],
            "evidence": state.get("current_evidence", []),
            "rules": state.get("rules", DEFAULT_RULES),
        }

        response = CHAIN.invoke(
            {
                "llm_input": llm_input,
            }
        )

        latency = round(time.perf_counter() - start, 3)

        return {
            "current_win_theme": response,
            "status": response.get("status", "candidate"),
            "validation_status": "passed",
            "warnings": [
                *state.get("warnings", []),
                *response.get("validation", {}).get("warnings", []),
            ],
            "unsupported_claims_removed": response.get(
                "validation",
                {},
            ).get("unsupported_claims_removed", []),
            "current_step": "win_theme_generator",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "win_theme_generator": latency,
            },
        }

    except Exception as e:
        latency = round(time.perf_counter() - start, 3)

        return {
            "current_win_theme": None,
            "status": "failed",
            "validation_status": "failed",
            "warnings": [
                *state.get("warnings", []),
                str(e),
            ],
            "current_step": "win_theme_generator",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "win_theme_generator": latency,
            },
        }