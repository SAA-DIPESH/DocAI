from typing import Dict, Any
from app.agents.wintheam_extractor.graph.agent_state import WintheamState
import time
from app.utils.helpers import read_markdown_file
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
# from app.infrastructure.load_llms import llm

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.agents.wintheam_extractor.graph.chains.validator_chain import VALIDATION_CHAIN
from app.infrastructure.load_llms import create_llm



def validate_output_node(state: WintheamState):

    start = time.perf_counter()

    try:

        validation = VALIDATION_CHAIN.invoke(
            {
                "response": state["response"]
            }
        )


        status = validation.get("validation_status", "failed")

        feedback = validation.get("feedback", [])

        score = validation.get("score", 0)

      
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