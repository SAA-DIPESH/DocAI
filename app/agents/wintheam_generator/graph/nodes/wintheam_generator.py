import time
from typing import Dict, Any
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.utils.helpers import read_markdown_file
# from app.infrastructure.load_llms import llm
from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_generator.prompts.prompt_loader import CONSTITUTION, SPECIFICATION, SYS_PROMPT
# from app.utils.token_usage_logger import extract_token_usage, TokenUsageService

# Load LLM
llm = create_llm()


# CONSTITUTION_PATH & SPECIFICATION_PATH files
# CONSTITUTION_PATH = Path(r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_generator\input_files\constitution.md").expanduser().resolve()
# SPECIFICATION_PATH = Path(r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_generator\input_files\specification.md").expanduser().resolve()
# SYS_PROMPT =  Path( r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_generator\input_files\system_prompt.md").expanduser().resolve()

def win_theme_generator_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Generates one company capability win theme for the current anchor group using current evidence.
    """

    start = time.perf_counter()

    try:
        context = state["context"]
        current_anchor_group = state["current_anchor_group"]
        current_evidence = state.get("current_evidence", [])

        # cons_content = read_markdown_file(CONSTITUTION_PATH, file_label="Constitution")
        # spec_content = read_markdown_file(SPECIFICATION_PATH, file_label="Specification")
        # sys_content = read_markdown_file(SYS_PROMPT, file_label="SystemPrompt")

        formatted_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=CONSTITUTION),
            SystemMessage(content=SPECIFICATION),
            SystemMessage(content=SYS_PROMPT),
            ("human", """
        Generate one company capability win theme using the following input.

        Input JSON:
        {llm_input}

        Return JSON only.
        """)
        ])

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

        parser = JsonOutputParser()
        chain = formatted_prompt | llm 

        raw_response = chain.invoke({
            "llm_input": llm_input,
        })

        response = parser.invoke(raw_response)

        # Token Usage Logger
        # usage = extract_token_usage(response)

        # payload = {
        #     "agent_name": "WinThemeGenerator",
        #     "company_id": state["company_id"],
        #     **usage,
        # }

        # Save the token
        # try:
        #     TokenUsageService.log_usage(payload)
        # except Exception as log_error:
        #     print("Error in inserting", log_error)     

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