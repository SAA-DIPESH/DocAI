import json
import time
from app.infrastructure.load_llms import create_llm
from app.agents.Section_writer.prompts.get_section_writer_agent_prompt import TENDER_SECTION_WRITER_PROMPT
from app.infrastructure.token_usage import TokenUsageService
from pathlib import Path
from app.agents.Section_writer.schemas.state import ProposalGenerationState,SectionState


llm=create_llm(

)


# BASE_DIR = Path(__file__).resolve().parent / "input_files"

# def read_prompt_file(file_path: Path) -> str:
#     if file_path.exists():
#         return file_path.read_text(encoding="utf-8")
#     # Fallback to an empty string or a placeholder if the file is missing
#     return ""

# CONSTITUTION = read_prompt_file(BASE_DIR / "constitution.md")
# SPECIFICATION = read_prompt_file(BASE_DIR / "specification.md")
# USER_PROMPT = read_prompt_file(BASE_DIR / "system_prompt.md")
##################################### Section Writer Agent #####################################

def _extract_json_object(content: str) -> dict:
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


def _fallback_section_response(generation_context: dict, raw_content: str) -> dict:
    section = generation_context.get("Section", generation_context)

    return {
        "SectionId": section.get("SectionId", ""),
        "SectionName": section.get("SectionName", ""),
        "GeneratedContent": "",
        "GeneratedSubSections": [],
        "InternalReview": {
            "CoverageStatus": "InsufficientEvidence",
            "EvidenceGap": True,
            "PublicationStatus": "Blocked",
            "MissingEvidence": [
                {
                    "RequirementId": "",
                    "RequirementText": "",
                    "GapType": "NoSupportingEvidence",
                    "MissingInformation": [
                        "Section writer returned invalid JSON."
                    ],
                    "RecommendedResolution": "Regenerate the section or adjust the section writer prompt to return strict JSON.",
                }
            ],
            "Traceability": [],
            "RawModelOutput": (raw_content or "")[:1000],
        },
    }


async def section_writer(
    *,
    generation_context: dict,
    improvement_feedback: list | None = None,
):
    """
    Generates or regenerates a proposal section.

    generation_context may contain:
    - Section
    - WinThemes
    - RetrievedDocuments
    - EvidenceSummary
    - EvaluationCriteria
    - WritingGuidelines
    - etc.
    """

    formatted_messages = TENDER_SECTION_WRITER_PROMPT.invoke(
        {
            "section_context": json.dumps(
                generation_context.get("Section", generation_context),
                indent=2,
                ensure_ascii=False,
            ),
            "Win_Theme": json.dumps(
                generation_context.get("WinThemes", []),
                indent=2,
                ensure_ascii=False,
            ),
        }
    )

    response = await llm.ainvoke(formatted_messages)

    token_usage = TokenUsageService.extract_token_usage(response)
    raw_content = response.content or ""

    try:
        parsed_response = _extract_json_object(raw_content)
    except json.JSONDecodeError:
        parsed_response = _fallback_section_response(
            generation_context=generation_context,
            raw_content=raw_content,
        )

    return {
        "response": parsed_response,
        "token_usage": token_usage,
    }
    
################################################################################################################


async def section_writer_node(
    state: SectionState,
):

    generation_context = state["generation_context"]

    improvement_feedback = state.get(
        "improvement_feedback",
        [],
    )

    result = await section_writer(
        generation_context=generation_context,
        improvement_feedback=improvement_feedback,
    )

    workflow_metadata = {
        **state.get("workflow_metadata", {})
    }

    workflow_metadata["current_node"] = "section_writer"
    workflow_metadata["workflow_status"] = "Completed"

    # 
    return {
    "generated_content": result["response"],
    "section_writer_token_usage": result["token_usage"],
    "workflow_metadata": workflow_metadata,
}
  




