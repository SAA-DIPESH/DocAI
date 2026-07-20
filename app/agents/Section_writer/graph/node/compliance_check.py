from typing import Dict, Any
from app.agents.Section_writer.schemas.state import SectionState
from app.agents.Section_writer.prompts.get_compliance_check import COMPLIANCE_CHECK_PROMPT
import json
from app.infrastructure.load_llms import create_llm
from typing import Dict, Any
from app.infrastructure.token_usage import TokenUsageService


llm=create_llm()


def _extract_json_object(content: str) -> Dict[str, Any]:
    text = (content or "").strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise

# async def compliance_agent(
#     generated_content: Dict[str, Any],
#     section_context: Dict[str, Any]
# ) -> Dict[str, Any]:
#     """
#     Reviews the generated proposal section.

#     Returns a dictionary containing both the structured evaluation 
#     and the associated token metrics.
#     """
#     messages = COMPLIANCE_CHECK_PROMPT.format_messages(
#         generated_content=json.dumps(
#             generated_content,
#             indent=2,
#             ensure_ascii=False,
#         ),
#         section_context=json.dumps(
#             section_context,
#             indent=2,
#             ensure_ascii=False,
#         ),
#     )

#     response = await llm.ainvoke(messages)
#     token_usage = TokenUsageService.extract_token_usage(response)
    
#     # Try parsing the LLM output safely
#     try:
#         review_data = json.loads(response.content)
#     except json.JSONDecodeError:
#         # Fallback mechanism if the LLM output is malformed raw string
#         review_data = {"error": "Failed to parse compliance response as JSON.", "raw_content": response.content}

#     # Return both items wrapped together
#     return {
#         "review": review_data,
#         "token_usage": token_usage
#     }

async def compliance_agent(
    generated_content: Dict[str, Any],
    section_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Reviews the generated proposal section.

    Returns:
    {
        "review": {...},
        "token_usage": {...}
    }
    """

    messages = COMPLIANCE_CHECK_PROMPT.format_messages(
        generated_content=json.dumps(
            generated_content,
            indent=2,
            ensure_ascii=False,
        ),
        section_context=json.dumps(
            section_context,
            indent=2,
            ensure_ascii=False,
        ),
    )

    response = await llm.ainvoke(messages)

    token_usage = TokenUsageService.extract_token_usage(response)

    raw_content = response.content or ""

    try:
        review_data = _extract_json_object(raw_content)
    except json.JSONDecodeError:
        review_data = {
            "status": "FAIL",
            "score": 0,
            "feedback": [
                "Compliance agent returned invalid JSON."
            ],
            "missing_requirements": [],
            "missing_win_themes": [],
            "missing_evaluation_criteria": [],
            "unsupported_claims": [],
            "improvement_suggestions": [],
            "raw_model_output": raw_content[:1000],
        }

    return {
        "review": review_data,
        "token_usage": token_usage,
    }




##################################################  Compliance Check Node  ##################################################     

async def compliance_check_node(
    state: SectionState,
) -> Dict[str, Any]:
    
    agent_output = await compliance_agent(
        generated_content=state["generated_content"],
        section_context=state["generation_context"]["Section"],
    )
    compliance_result = agent_output["review"]
    workflow_metadata = {
        **state.get("workflow_metadata", {}),
        "current_node": "compliance_check",
        "workflow_status": "Completed",
    }


    return {
    "compliance_result": compliance_result,
    "improvement_feedback": compliance_result.get(
        "improvement_suggestions",
        []
    ),
    "compliance_token_usage": agent_output["token_usage"],
    "workflow_metadata": workflow_metadata,
}
