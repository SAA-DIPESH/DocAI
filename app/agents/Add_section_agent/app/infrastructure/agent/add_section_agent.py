from app.infrastructure.prompts.prompt import (
    SECTION_GENERATION_PROMPT,
    CONSTITUTION,
    SPECIFICATION,
    USER_PROMPT
)
import json
from app.services.mongo.mongo_services import MongoService
from app.services.qdrant.qdrant_services import QdrantService
from app.infrastructure.llm.llm_factory import LLMFactory
from app.infrastructure.token_usage import TokenUsageService
import json
from typing import Dict, Any
def add_section_agent(
    tender_id: str,
    company_id: str,
    section_name: str,  # This is the user-passed name (e.g., "Company Details")
    section_purpose: str = ""
) -> Dict[str, Any]:
    """
    Generate a single proposal section ensuring strict JSON output.
    Forces the section names to match the user's requested string.
    """
    
    try:
        # 1. Attempt exact text lookup
        section_data = MongoService.get_section_requirements(
            tender_id=tender_id,
            company_id=company_id,
            section_name=section_name
        )
    except ValueError as exact_lookup_error:
        if "TenderSectionPlans document not found" in str(exact_lookup_error):
            section_data = MongoService.build_custom_section_requirements(
                section_name=section_name,
                section_purpose=section_purpose
            )
        else:
            # 2. FALLBACK: Vector search if exact text match fails
            try:
                best_match = MongoService.find_best_matching_section(
                    tender_id=tender_id,
                    company_id=company_id,
                    section_name=section_name,
                    section_purpose=section_purpose
                )
                
                resolved_section_name = best_match["SectionName"]
                
                # Fetch requirements using the database's internally mapped name
                section_data = MongoService.get_section_requirements(
                    tender_id=tender_id,
                    company_id=company_id,
                    section_name=resolved_section_name
                )
                
            except ValueError as fallback_error:
                if "TenderSectionPlans document not found" in str(fallback_error):
                    section_data = MongoService.build_custom_section_requirements(
                        section_name=section_name,
                        section_purpose=section_purpose
                    )
                else:
                    raise ValueError(
                        f"Section resolution failed entirely for '{section_name}'. "
                        f"Reason: {str(fallback_error)}"
                    )

    if not section_data:
        raise ValueError(
            f"No section data found for section_name={section_name}"
        )

    # 3. Context retrieval from Qdrant
    search_query = section_data["SearchQuery"]
    qdrant_response = QdrantService.retrieve_context_for_section(
        company_id=company_id,
        search_query=search_query,
        collection_name="CPDocuments",
        limit=3
    )

    company_context = qdrant_response["Context"]
    evidence_summaries = [
        req.get("EvidenceSummary", "") 
        for req in section_data["Requirements"] 
        if req.get("EvidenceSummary", "")
    ]
    evidence_summary = "\n".join(evidence_summaries)

    # 4. Prompt construction & LLM invocation
    messages = SECTION_GENERATION_PROMPT.format_messages(
        constitution=CONSTITUTION,
        specification=SPECIFICATION,
        user_prompt=USER_PROMPT,
        tender_id=tender_id,
        company_id=company_id,
        section_name=section_data["SectionName"],  # LLM gets the DB context name for content generation
        section_purpose=section_purpose,
        requirements=section_data["Requirements"],
        company_context=company_context,
        evidence_summary=evidence_summary
    )

    llm = LLMFactory.get_llm()
    response = llm.invoke(messages)
    content = response.content.strip()
    token_usage = TokenUsageService.extract_token_usage(response)
    
    
    # Standard markdown cleaning
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    # 5. Parsing & Structure Verification
    try:
        parsed_json = json.loads(content)
        
        # Handle nested data string transformation if required by your pipeline
        if isinstance(parsed_json, dict) and "data" in parsed_json:
            raw_res = parsed_json["data"].get("raw_response")
            if isinstance(raw_res, str) and raw_res.strip().startswith("{"):
                try:
                    parsed_json["data"]["raw_response"] = json.loads(raw_res)
                except json.JSONDecodeError:
                    pass

        # ---------------------------------------------------------
        # 🔥 CRITICAL OVERWRITE STEP
        # This replaces any dynamic fallback name with your expected input name
        # ---------------------------------------------------------
        if isinstance(parsed_json, dict):
            parsed_json["SectionName"] = section_name
            
            # If the LLM wrapper puts it inside a nested data dict too, update it
            if "data" in parsed_json and isinstance(parsed_json["data"], dict):
                parsed_json["data"]["SectionName"] = section_name

        return parsed_json

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": f"Failed to parse LLM response as JSON: {str(e)}",
            "data": {
                "raw_response": content,
                "SectionName": section_name,  # Fallback error payload preserves input name
                "CoverageStatus": "Failed",
                "EvidenceGap": True,
                "MissingEvidenceReasons": [],
                "GeneratedSubSections": []
            },
            "token_usage": token_usage
        }
    


    
# def add_section_agent(
#     tender_id: str,
#     company_id: str,
#     section_name: str,
#     section_purpose: str = ""
# ):
#     """
#     Generate a single proposal section ensuring strict JSON output.
#     """
#     section_data = MongoService.get_section_requirements(
#         tender_id=tender_id,
#         company_id=company_id,
#         section_name=section_name
#     )

#     if not section_data:
#         raise ValueError(
#             f"No section data found for section_id={section_name}"
#         )

#     search_query = section_data["SearchQuery"]

#     qdrant_response = (
#         QdrantService.retrieve_context_for_section(
#             company_id=company_id,
#             search_query=search_query,
#             collection_name="CPDocuments",
#             limit=3
#         )
#     )

#     company_context = qdrant_response["Context"]
#     evidence_summaries = []

#     for requirement in section_data["Requirements"]:
#         evidence_summary = requirement.get("EvidenceSummary", "")
#         if evidence_summary:
#             evidence_summaries.append(evidence_summary)

#     evidence_summary = "\n".join(evidence_summaries)

#     messages = SECTION_GENERATION_PROMPT.format_messages(
#         constitution=CONSTITUTION,
#         specification=SPECIFICATION,
#         user_prompt=USER_PROMPT,
#         tender_id=tender_id,
#         company_id=company_id,
#         section_name=section_data["SectionName"],
#         section_purpose=section_purpose,
#         requirements=section_data["Requirements"],
#         company_context=company_context,
#         evidence_summary=evidence_summary
#     )

#     llm = LLMFactory.get_llm()
#     response = llm.invoke(messages)

#     content = response.content.strip()
    
#     # Clean up standard Markdown blocks safely
#     if content.startswith("```"):
#         content = content.split("```")[1]
#         if content.startswith("json"):
#             content = content[4:]
#         content = content.strip()

#     try:
#         parsed_json = json.loads(content)
        
#         # FIX: If the LLM returns {"success": true, "data": {"raw_response": "{...}"}}
#         # where raw_response is a nested JSON string, we force parse it as well.
#         if isinstance(parsed_json, dict) and "data" in parsed_json:
#             raw_res = parsed_json["data"].get("raw_response")
#             if isinstance(raw_res, str) and raw_res.strip().startswith("{"):
#                 try:
#                     parsed_json["data"]["raw_response"] = json.loads(raw_res)
#                 except json.JSONDecodeError:
#                     pass # Keep it as string if it's genuinely text

#         return parsed_json

#     except json.JSONDecodeError as e:
#         # Guaranteeing the return is ALWAYS valid JSON matching your schema structure
#         return {
#             "success": False,
#             "message": f"Failed to parse LLM response as JSON: {str(e)}",
#             "data": {
#                 "raw_response": content,
#                 "CoverageStatus": "Failed",
#                 "EvidenceGap": True,
#                 "MissingEvidenceReasons": [],
#                 "GeneratedSubSections": []
#             }
#         }
