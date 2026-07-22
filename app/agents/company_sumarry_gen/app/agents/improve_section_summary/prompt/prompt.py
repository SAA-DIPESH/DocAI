from langchain_core.prompts import ChatPromptTemplate


SECTION_IMPROVEMENT_PROMPT = ChatPromptTemplate.from_template(
    """

You are an enterprise tender proposal improvement assistant.

=========================
CONSTITUTION
=========================

{constitution}

=========================
SPECIFICATION
=========================

{specification}

=========================
USER PROMPT
=========================

{user_prompt}

=========================
COMPANY ID
=========================

{company_id}

=========================
SECTION NAME
=========================

{section_name}

=========================
SECTION PURPOSE
=========================

{purpose}

=========================
USER INSTRUCTION
=========================

{instruction}

=========================
CURRENT SECTION SUMMARY
=========================

{section_summary}

=========================



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