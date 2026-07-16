from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

BASE_DIR = Path(__file__).resolve().parent.parent

# CONSTITUTION = (
#     BASE_DIR / "sentance_rephraser_agent_input_files" / "constitution.md"
# ).read_text(encoding="utf-8")

# SPECIFICATION = (
#     BASE_DIR / "sentance_rephraser_agent_input_files" / "specification.md"
# ).read_text(encoding="utf-8")

# USER_PROMPT = (
#     BASE_DIR / "sentance_rephraser_agent_input_files" / "system_prompt.md"
# ).read_text(encoding="utf-8")


SENTANCE_REPHRASER_AGENT_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
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
1. Rephrase the provided paragraph to improve clarity, readability, and professional tone.
2. Preserve the original meaning, technical terms, company names, standards, values, dates, references, and units exactly.
3. Do not add, remove, summarize, or expand any information.
4. Maintain proposal-quality business language suitable for tender documents.
5. Return strictly specification-compliant JSON following the required format.
6. Do not return markdown, explanations, reasoning, or text outside the JSON.
"""
        ),
        (
            "human",
            """
Rephrase the following paragraph from a tender document while preserving its original meaning.

================ INPUT TEXT ================
{content}
{content}

Return the output strictly in the following JSON format:

{{
  "rephrased_versions": [
    {{
      "version": 1,
      "text": "<First rephrased paragraph>"
    }},
    {{
      "version": 2,
      "text": "<Second rephrased paragraph>"
    }},
    {{
      "version": 3,
      "text": "<Third rephrased paragraph>"
    }}
  ]
}}
"""
        ),
    ]
)
