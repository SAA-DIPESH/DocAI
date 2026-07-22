from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.load_llms import create_llm
from app.agents.tender_requirement_agent.utils.helper import read_markdown_file

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
    / "requirement_detection"
)

DETECTOR_SYSTEM_PROMPT = read_markdown_file(
    INPUT_FILES / "system_prompt.md"
)

DETECTOR_CONSTITUTION = read_markdown_file(
    INPUT_FILES / "constitution.md"
)

DETECTOR_SPECIFICATION = read_markdown_file(
    INPUT_FILES / "specification.md"
)

# ==========================================================
# Prompt
# ==========================================================

DETECTOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
{system_prompt}

{constitution}

{specification}
""",
        ),
        (
            "human",
            """
Tender Document Chunk

{chunk_text}

Return ONLY valid JSON.
""",
        ),
    ]
)

# ==========================================================
# Chain
# ==========================================================

LLM_CHAIN = DETECTOR_PROMPT | llm

PARSER = JsonOutputParser()

# ==========================================================
# Wrapper
# ==========================================================

async def detect_and_extract(
    chunk_text: str,
):
    raw_response = await LLM_CHAIN.ainvoke(
        {
            "system_prompt": DETECTOR_SYSTEM_PROMPT,
            "constitution": DETECTOR_CONSTITUTION,
            "specification": DETECTOR_SPECIFICATION,
            "chunk_text": chunk_text,
        }
    )

    parsed_response = PARSER.invoke(raw_response)

    return raw_response, parsed_response