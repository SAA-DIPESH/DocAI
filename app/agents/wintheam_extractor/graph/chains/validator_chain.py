from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_extractor.prompts.prompt_loader import (
    VALIDATION_SYSTEM_PROMPT,
)

llm = create_llm()

RETRIEVAL_PLAN_VALIDATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            VALIDATION_SYSTEM_PROMPT,
        ),
        (
            "human",
            """
Validate the retrieval blueprint below against the validation rules.

Return only the required JSON response.

Retrieval Blueprint:

{retrieval_blueprint}
            """.strip(),
        ),
    ]
)

VALIDATION_CHAIN = (
    RETRIEVAL_PLAN_VALIDATION_PROMPT
    | llm
    | JsonOutputParser()
)