import time
from typing import Dict, Any

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_generator.prompts.prompt_loader import (
    CONSTITUTION,
    SPECIFICATION,
    SYS_PROMPT,
)

# -----------------------------
# Initialize once
# -----------------------------
llm = create_llm()

PARSER = JsonOutputParser()

PROMPT = ChatPromptTemplate.from_messages(
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

CHAIN = PROMPT | llm



def win_theme_generator_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Generates one company capability win theme for the current anchor group using current evidence.
    """

    start = time.perf_counter()

    try:
        context = state["context"]
        current_anchor_group = state["current_anchor_group"]
        current_evidence = state.get("current_evidence", [])

        llm_input = {
            "company_id": state["company_id"],
            "context": context,
            "anchor_group": current_anchor_group,
            "evidence": current_evidence,
            "rules": state.get(
                "rules",
                {
                    "minimum_evidence_items": 2,
                    "minimum_distinct_documents": 2,
                },
            ),
        }

        llm_start = time.perf_counter()

        raw_response = CHAIN.invoke(
            {
                "llm_input": llm_input,
            }
        )

        print(
            f"LLM Response Time: {time.perf_counter() - llm_start:.2f}s"
        )

        response = PARSER.invoke(raw_response)

        print("\nLLM RESPONSE:")
        print(response)

        end = time.perf_counter()

        return {
            "current_win_theme": response,
            "status": response.get("status", "candidate"),
            "validation_status": "passed",
            "warnings": response.get("validation", {}).get("warnings", []),
            "unsupported_claims_removed": response.get(
                "validation", {}
            ).get("unsupported_claims_removed", []),
            "current_step": "win_theme_generator",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "win_theme_generator": round(end - start, 3),
            },
        }

    except Exception as e:
        end = time.perf_counter()

        print("\nWIN THEME GENERATOR ERROR:")
        print(str(e))

        return {
            "current_win_theme": None,
            "status": "failed",
            "validation_status": "failed",
            "warnings": [str(e)],
            "current_step": "win_theme_generator",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "win_theme_generator": round(end - start, 3),
            },
        }

