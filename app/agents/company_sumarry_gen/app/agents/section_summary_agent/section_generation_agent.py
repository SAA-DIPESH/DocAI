from app.infrastructure.llm.loader import LLMFactory
from app.infrastructure.llm.embedding_model import EmbeddingService

from app.agents.section_summary_agent.prompt.prompt import (
    SECTION_GENERATION_PROMPT
)

from app.utils.file_loader import (
    load_prompt_file
)




import json
import re


# class SectionGenerationAgent:

#     @staticmethod
#     def generate_section(
#         company_id: str,
#         section_name: str,
#         purpose: str,
#         provider: str = "mistral"
#     ):

#         # =========================
#         # LOAD PROMPT FILES
#         # =========================

#         constitution = load_prompt_file(
#             "agents/section_summary_agent/input_files/constitution.md"
#         )

#         specification = load_prompt_file(
#             "agents/section_summary_agent/input_files/specification.md"
#         )

#         user_prompt = load_prompt_file(
#             "agents/section_summary_agent/input_files/user_prompt.md"
#         )

#         # =========================
#         # RETRIEVE COMPANY CONTEXT
#         # =========================

#         retrieved_chunks = (
#             EmbeddingService.retrieve_context(
#                 company_id=company_id,
#                 section_name=section_name,
#                 purpose=purpose,
#                 limit=3
#             )
#         )

#         retrieved_context = "\n\n".join([
#             chunk["text"]
#             for chunk in retrieved_chunks
#         ])

#         # =========================
#         # BUILD PROMPT
#         # =========================

#         prompt = (
#             SECTION_GENERATION_PROMPT
#             .format(
#                 constitution=constitution,
#                 specification=specification,
#                 user_prompt=user_prompt,
#                 section_name=section_name,
#                 purpose=purpose,
#                 retrieved_context=retrieved_context
#             )
#         )

#         # =========================
#         # LOAD LLM
#         # =========================

#         llm = LLMFactory.get_llm(
#             provider=provider
#         )

#         # =========================
#         # GENERATE RESPONSE
#         # =========================

#         response = llm.invoke(prompt)

#         # =========================
#         # CLEAN RESPONSE
#         # =========================

#         content = response.content.strip()

#         content = re.sub(
#             r"```json|```",
#             "",
#             content
#         ).strip()

#         # =========================
#         # SAFE JSON PARSE
#         # =========================

#         try:

#             parsed_response = json.loads(content)

#             return parsed_response

#         except Exception:

#             return {
#                 "section_name": section_name,
#                 "section_generated_summary": content,
#                 "subsections": []
#             }
class SectionGenerationAgent:

    @staticmethod
    def generate_section(
        company_id: str,
        section_name: str,
        purpose: str
    ):

        constitution = load_prompt_file(
            "agents/section_summary_agent/input_files/constitution.md"
        )

        specification = load_prompt_file(
            "agents/section_summary_agent/input_files/specification.md"
        )

        user_prompt = load_prompt_file(
            "agents/section_summary_agent/input_files/user_prompt.md"
        )

        retrieved_chunks = (
            EmbeddingService.retrieve_context(
                company_id=company_id,
                section_name=section_name,
                purpose=purpose,
                limit=3
            )
        )

        retrieved_context = "\n\n".join([
            chunk["text"]
            for chunk in retrieved_chunks
        ])

        prompt = SECTION_GENERATION_PROMPT.format(
            constitution=constitution,
            specification=specification,
            user_prompt=user_prompt,
            section_name=section_name,
            purpose=purpose,
            retrieved_context=retrieved_context
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
                "section_generated_summary": content,
                "subsections": []
            }