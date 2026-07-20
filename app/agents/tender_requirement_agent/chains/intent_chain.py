from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.load_llms import create_llm
from app.agents.tender_requirement_agent.utils.helper import (
    read_markdown_file,
)

# ==========================================================
# LLM
# ==========================================================

llm = create_llm()

# ==========================================================
# Load Prompt Files
# ==========================================================

BASE_PATH = Path(__file__).resolve().parent.parent

INPUT_FILES = (
    BASE_PATH
    / "input_files"
    / "intent_understanding"
)

INTENT_SYSTEM_PROMPT = read_markdown_file(
    INPUT_FILES / "system_prompt.md"
)

INTENT_CONSTITUTION = read_markdown_file(
    INPUT_FILES / "constitution.md"
)

INTENT_SPECIFICATION = read_markdown_file(
    INPUT_FILES / "specification.md"
)

# ==========================================================
# Prompt
# ==========================================================

INTENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
{system_prompt}

{constitution}

{specification}
"""
        ),
        (
            "human",
            """
Heading:

{heading}

Requirement Type:

{requirement_type}

Requirement Strength:

{requirement_strength}

Requirement:

{requirement}

Return ONLY valid JSON.
"""
        ),
    ]
)

# ==========================================================
# Chain
# ==========================================================

LLM_CHAIN = INTENT_PROMPT | llm

PARSER = JsonOutputParser()

# ==========================================================
# Wrapper
# ==========================================================

async def understand_intent(
    requirement: str,
    requirement_type: str,
    requirement_strength: str,
    heading: str | None,
):

    raw_response = await LLM_CHAIN.ainvoke(
        {
            "system_prompt": INTENT_SYSTEM_PROMPT,
            "constitution": INTENT_CONSTITUTION,
            "specification": INTENT_SPECIFICATION,
            "heading": heading,
            "requirement": requirement,
            "requirement_type": requirement_type,
            "requirement_strength": requirement_strength,
        }
    )

    parsed_response = PARSER.invoke(raw_response)

    return raw_response, parsed_response