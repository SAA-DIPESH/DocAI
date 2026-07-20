from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.infrastructure.load_llms import create_llm
from app.agents.wintheam_extractor.prompts.prompt_loader import VALIDATION_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage


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

VALIDATION_CHAIN = VALIDATION_PROMPT| llm | JsonOutputParser()
