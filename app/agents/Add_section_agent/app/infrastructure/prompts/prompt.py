from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate


BASE_DIR = Path(__file__).resolve().parent.parent

CONSTITUTION = (
    BASE_DIR / "input_files" / "constitution.md"
).read_text(encoding="utf-8")

SPECIFICATION = (
    BASE_DIR / "input_files" / "specification.md"
).read_text(encoding="utf-8")

USER_PROMPT = (
    BASE_DIR / "input_files" / "user_prompt.md"
).read_text(encoding="utf-8")


SECTION_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Tender Section Generator.

Follow the Constitution, Specification, and User Prompt exactly.

================ CONSTITUTION ================
{constitution}

================ SPECIFICATION ================
{specification}

================ USER PROMPT ================
{user_prompt}

Your responsibilities:

1. Generate a single proposal-ready section.
2. Use only supplied evidence and company context.
3. Never invent evidence.
4. Never invent certifications.
5. Never invent case studies.
6. Never invent project experience.
7. Never invent metrics or performance claims.
8. Return strictly specification-compliant JSON.
9. Do not return markdown.
10. Do not return explanations.
11. Do not return reasoning.
12. Do not return any text outside the JSON response.
"""
        ),
        (
          
    "human",
    """
TenderId:
{tender_id}

CompanyId:
{company_id}

SectionName:
{section_name}

SectionPurpose:
{section_purpose}

Requirements:
{requirements}

Retrieved Company Context:
{company_context}

Evidence Summary:
{evidence_summary}


Generate a complete proposal-ready section.

Use only supplied context and evidence.

Return only specification-compliant JSON.

"""

        ),
    ]
)