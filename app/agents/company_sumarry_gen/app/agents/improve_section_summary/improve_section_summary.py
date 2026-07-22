import json
import re

from app.infrastructure.llm.loader import LLMFactory
from app.infrastructure.llm.embedding_model import EmbeddingService

from app.agents.improve_section_summary.prompt.prompt import (
    SECTION_IMPROVEMENT_PROMPT
)

from app.utils.file_loader import (
    load_prompt_file
)

class SectionImprovementAgent:

    @staticmethod
    def improve_section(
        company_id: str,
        section_name: str,
        section_summary: str,
        purpose: str,
        instruction: str
    ):

        constitution = load_prompt_file(
            "agents/improve_section_summary/input_files/constitution.md"
        )

        specification = load_prompt_file(
            "agents/improve_section_summary/input_files/specification.md"
        )

        user_prompt = load_prompt_file(
            "agents/improve_section_summary/input_files/user_prompt.md"
        )

        prompt = SECTION_IMPROVEMENT_PROMPT.format(
            constitution=constitution,
            specification=specification,
            user_prompt=user_prompt,
            company_id=company_id,
            section_name=section_name,
            purpose=purpose,
            instruction=instruction,
            section_summary=section_summary,
        )

        llm = LLMFactory.get_llm()

        response = llm.invoke(prompt)

        content = response.content.strip()

        content = re.sub(
            r"```json|```",
            "",
            content
        ).strip()

        try:
            return json.loads(content)

        except Exception:
            return {
                "section_name": section_name,
                "improved_section_summary": content,
                "subsections": []
            }