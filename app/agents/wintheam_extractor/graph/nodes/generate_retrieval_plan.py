from typing import Dict, Any
from app.agents.wintheam_extractor.graph.agent_state import WintheamState
import time
from pathlib import Path
from app.utils.helpers import read_markdown_file
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.infrastructure.load_llms import create_llm
# from app.utils.token_usage_logger import extract_token_usage, TokenUsageService

# Load LLM
llm = create_llm()

# CONSTITUTION_PATH & SPECIFICATION_PATH files
CONSTITUTION_PATH = Path(r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_extractor\input_files\constitution.md")

SPECIFICATION_PATH = Path(r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_extractor\input_files\specification.md")

SYSTEM_PROMPT_PATH = Path(r"C:\Users\Dipesh Dhote\Desktop\Deployment\DocAI\app\agents\wintheam_extractor\input_files\system_prompt.md")

CONSTITUTION = read_markdown_file(CONSTITUTION_PATH, "Constitution")

SPECIFICATION = read_markdown_file(CONSTITUTION_PATH, "Specification")

SYSTEM_PROMPT = read_markdown_file(SYSTEM_PROMPT_PATH, "System Prompt")



FULL_SYSTEM_PROMPT = f"""
{SYSTEM_PROMPT}

==================================================
CONSTITUTION
==================================================

{CONSTITUTION}

==================================================
SPECIFICATION
==================================================

{SPECIFICATION}
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=FULL_SYSTEM_PROMPT),
        (
            "human",
            """
Company ID:
{company_id}

Industry:
{industry}

CPV Code:
{cpv_code}

{validation_feedback}
""".strip(),
        ),
    ]
)

# CHAIN = PROMPT | llm | JsonOutputParser()

LLM_CHAIN = PROMPT | llm
OUTPUT_PARSER = JsonOutputParser()


def generate_retrieval_plan_node(state: WintheamState) -> Dict[str, Any]:

    start = time.perf_counter()

    try:

        validation_feedback = state.get("validation_feedback") or []

        if validation_feedback:
            feedback_text = (
                "Previous Validation Feedback:\n"
                + "\n".join(f"- {item}" for item in validation_feedback)
            )
        else:
            feedback_text = ""

        raw_llm_response  = LLM_CHAIN.invoke(
            {
                "company_id": state["company_id"],
                "industry": state["industry"],
                "cpv_code": state["cpv_code"],
                "validation_feedback": feedback_text,
            }
        )

        llm_response = OUTPUT_PARSER.invoke(raw_llm_response)
        
        # # Token Usage Logger
        # usage = extract_token_usage(raw_llm_response)

        # payload = {
        #     "agent_name": "WinThemeExtractor",
        #     "company_id": state["company_id"],
        #     **usage,
        # }

        # # Save the token
        # try:
        #     TokenUsageService.log_usage(payload)
        # except Exception as log_error:
        #     print("Error in inserting log for ", log_error)

        anchor_groups = llm_response["anchor_groups"]

        if not isinstance(anchor_groups, list):
            raise ValueError("'anchor_groups' must be a list.")

        if len(anchor_groups) == 0:
            raise ValueError("'anchor_groups' cannot be empty.")

        end = time.perf_counter()

        return {
            "response": llm_response,
            "status": "success",
            "current_step": "generate_retrieval_plan",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "generate_retrieval_plan": round(end - start, 3),
            },
        }

    except Exception as e:

        end = time.perf_counter()

        return {
            "response": None,
            "status": "failed",
            "current_step": "generate_retrieval_plan_failed",
            "error": str(e),
            "validation_feedback": [str(e)],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "generate_retrieval_plan": round(end - start, 3),
            },
        }