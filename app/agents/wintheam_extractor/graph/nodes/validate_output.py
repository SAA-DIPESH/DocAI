from typing import Dict, Any
from app.agents.wintheam_extractor.graph.agent_state import WintheamState
import time
from app.utils.helpers import read_markdown_file
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
# from app.infrastructure.load_llms import llm

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.agents.wintheam_extractor.input_files.validation_prompt import VALIDATION_SYSTEM_PROMPT
from app.infrastructure.load_llms import create_llm
# from app.utils.token_usage_logger import extract_token_usage, TokenUsageService

# Load LLM
llm = create_llm()

VALIDATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", VALIDATION_SYSTEM_PROMPT),
        (
            "human",
            """
Validate the following retrieval plan.

{response}
""",
        ),
    ]
)

# VALIDATION_CHAIN = VALIDATION_PROMPT| llm | JsonOutputParser()
VALIDATION_LLM_CHAIN = VALIDATION_PROMPT | llm
VALIDATION_OUTPUT_PARSER  = JsonOutputParser()

def validate_output_node(state: WintheamState):

    start = time.perf_counter()

    try:

        raw_validation = VALIDATION_LLM_CHAIN.invoke(
            {
                "response": state["response"]
            }
        )

        validation = VALIDATION_OUTPUT_PARSER.invoke(raw_validation)


        status = validation.get("validation_status", "failed")

        feedback = validation.get("feedback", [])

        score = validation.get("score", 0)

       # Token Usage Logger
        # usage = extract_token_usage(raw_validation)

        # payload = {
        #     "agent_name": "WinThemeExtractValidator",
        #     "company_id": state["company_id"],
        #     **usage,
        # }

        # # Save the token
        # try:
        #     TokenUsageService.log_usage(payload)
        # except Exception as log_error:
        #     print("Error in inserting log for WinThemeExtractValidator", log_error)


        end = time.perf_counter()

        return {
            "validation_status": status,
            "validation_feedback": feedback,
            "validation_score": score,
            "current_step": "validate_output",
            "status": "success",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "validate_output": round(end - start, 3),
            },
        }

    except Exception as e:


        end = time.perf_counter()

        return {
            "validation_status": "failed",
            "validation_feedback": [str(e)],
            "validation_score": 0,
            "status": "failed",
            "current_step": "validate_output_failed",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "validate_output": round(end - start, 3),
            },
        }