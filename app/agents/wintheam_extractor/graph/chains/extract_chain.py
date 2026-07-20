from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_extractor.prompts.prompt_loader import CONSTITUTION, SPECIFICATION, SYSTEM_PROMPT
from langchain_core.messages import SystemMessage


# Load LLM
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


LLM_CHAIN = PROMPT | llm | JsonOutputParser()