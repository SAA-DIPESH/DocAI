from langchain_core.prompts import ChatPromptTemplate
from app.utils.file_loader import load_prompt_file

SECTION_GENERATION_PROMPT = ChatPromptTemplate.from_template(
    """

You are an expert AI business document generation assistant.

Your task is to generate a highly relevant section for a company document.

You must analyze:

1. Constitution File
2. Specification File
3. User Prompt
4. Retrieved Company Context

and generate a structured response.


=========================
CONSTITUTION FILE
=========================

{constitution}


=========================
SPECIFICATION FILE
=========================

{specification}


=========================
USER PROMPT
=========================

{user_prompt}


=========================
SECTION NAME
=========================

{section_name}


=========================
SECTION PURPOSE
=========================

{purpose}


=========================
RETRIEVED COMPANY CONTEXT
=========================

{retrieved_context}


=========================
IMPORTANT INSTRUCTIONS
=========================

- Use ONLY relevant information.
- Generate concise but meaningful business language.
- Maintain professional tone.
- Use retrieved company context heavily.
- Ensure subsection summaries are aligned with section purpose.
- Do not hallucinate unnecessary information.
- Follow the structure exactly.


=========================
OUTPUT FORMAT
=========================

Return ONLY valid JSON.

{{
    "section_name": "",
    "section_generated_summary": "",
    "subsections": [
        {{
            "subsection_name": "",
            "subsection_summary": ""
        }}
    ]
}}

"""
)
# constitution = load_prompt_file(
#     "prompts/documents/constitution.md"
# )

# specification = load_prompt_file(
#     "prompts/documents/specification.md"
# )

# user_prompt = load_prompt_file(
#     "prompts/documents/user_prompt.md"
# )

