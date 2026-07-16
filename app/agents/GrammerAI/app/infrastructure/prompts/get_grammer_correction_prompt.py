from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

BASE_DIR = Path(__file__).resolve().parent.parent

# CONSTITUTION = (
#     BASE_DIR / "grammer_agent_input_files" / "constitution.md"
# ).read_text(encoding="utf-8")

# SPECIFICATION = (
#     BASE_DIR / "grammer_agent_input_files" / "specification.md"
# ).read_text(encoding="utf-8")

# USER_PROMPT = (
#     BASE_DIR / "grammer_agent_input_files" / "system_prompt.md"
# ).read_text(encoding="utf-8")


GRAMMER_CORRECTION_AGENT_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a Technical Proposal Editor for tender documents.

Follow the Constitution, Specification, and User Prompt instructions exactly.

================ CONSTITUTION ================
{constitution}

================ SPECIFICATION ================
{specification}

================ USER PROMPT ================
{user_prompt}

Your responsibilities:
1. Correct grammar, spelling, punctuation, and syntax for the provided text.
2. Preserve original meaning, technical terms, values, and units exactly.
3. Do not add, remove, summarize, or expand content.
4. Return strictly specification-compliant JSON following the format shown in the specification.
5. Do not return markdown, explanations, reasoning, or text outside the JSON.
"""
        ),
        (
            "human",
            """
Analyze and grammatically correct the following paragraph from a tender document.

================ INPUT TEXT ================
{content}

Return the output strictly inside the required JSON format:
{{
  "corrected_text": "<Your corrected paragraph here>"
}}
"""
        )
    ]
)
