from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_extractor.prompts.prompt_loader import (
    CONSTITUTION,
    SPECIFICATION,
    SYSTEM_PROMPT,
)

llm = create_llm()

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
""".strip()

PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=FULL_SYSTEM_PROMPT),
        (
            "human",
            """
Generate an evidence retrieval blueprint using the following input.

Company ID:
{company_id}

Industry:
{industry}

CPV Codes:
{cpv_codes}

Previous Validation Feedback:
{validation_feedback}
            """.strip(),
        ),
    ]
)

RETRIEVAL_PLAN_CHAIN = (
    PROMPT
    | llm
    | JsonOutputParser()
)