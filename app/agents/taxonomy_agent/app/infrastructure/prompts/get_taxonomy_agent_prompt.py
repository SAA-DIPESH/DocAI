from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

BASE_DIR = Path(__file__).resolve().parent.parent

CONSTITUTION = (
    BASE_DIR
    / "input_files"
    / "Constitution.md"
).read_text(encoding="utf-8")

SPECIFICATION = (
    BASE_DIR
    / "input_files"
    / "Specification.md"
).read_text(encoding="utf-8")

SYSTEM_PROMPT = (
    BASE_DIR
    / "input_files"
    / "System_Prompts.md"
).read_text(encoding="utf-8")


TAXONOMY_AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
================ CONSTITUTION ================
{constitution}

================ SPECIFICATION ================
{specification}

================ SYSTEM PROMPT ================
{system_prompt}

You MUST strictly follow the Constitution, Specification and System Prompt.

Rules:
- Return ONLY valid JSON.
- Do NOT return markdown.
- Do NOT explain your reasoning.
- Do NOT invent CPV labels or document types.
- Use only the document taxonomy defined by the specification.
- Include all universal document types.
- Add sector-specific document types based on the supplied CPV division.
- Deduplicate document types.
- Preserve the required JSON schema exactly.
"""
        ),
        (
            "human",
            """
================ TAXONOMY INPUT ================

{input_json}


{{
    "tenderId": "... | null",
    "companyId": "... | null",
    "cpv": {{
        "code": "72000000-5",
        "label": "IT services | null",
        "additionalCodes": []
    }},
    "context": {{
        "country": "UK | null",
        "procedure": "Open | null",
        "sectorHint": "IT | null"
    }},
    "CPVsetfor": "Tender|Company"
}}

{{
  "tenderId": "string|null",
  "companyId": "string|null",
  "cpvProfile": {{
    "primaryCpvCode": "string",
    "primaryCpvLabel": "string|null",
    "cpvDivision": "string",
    "sectorFamilies": ["string"],
    "confidence": "HIGH|MEDIUM|LOW|UNKNOWN",
    "rationale": "string"
  }},
  "classificationSet": [
    {{
      "code": "string",
      "name": "string",
      "group": "Universal|SectorSpecific",
      "priority": "Core|Likely|Optional",
      "expectedSignals": ["string"]
    }}
  ],
  "downstreamUse": {{
    "instruction": "Use classificationSet as the allowed taxonomy for later document classification.",
    "universalTypesIncluded": true,
    "cpvSpecificTypesIncluded": true,
    "doNotUseCpvAsDocumentEvidence": true
  }},
  "warnings": ["string"],
  "CPVsetfor": "Tender|Company"
}}


Generate the document taxonomy according to the supplied Constitution, Specification and System Prompt.

Return ONLY the required JSON.
"""
        ),
    ]
).partial(
    constitution=CONSTITUTION,
    specification=SPECIFICATION,
    system_prompt=SYSTEM_PROMPT,
)
