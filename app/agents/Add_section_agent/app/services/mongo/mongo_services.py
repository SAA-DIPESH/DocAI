# import os
# from typing import List, Dict, Any, Optional

# from pymongo import MongoClient
# from dotenv import load_dotenv

# load_dotenv()


# class MongoService:
#     """
#     Mongo Service for Tender Section Generator

#     Required .env variables:
#     MONGO_URI=mongodb://localhost:27017
#     DATABASE_NAME=TenderDB

#     OR

#     MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
#     DATABASE_NAME=TenderDB
#     """

#     _client = None
#     _db = None

#     @staticmethod
#     def get_database():
#         if MongoService._db is None:
#             mongo_uri = os.getenv("MONGO_URI")
#             database_name = os.getenv("DATABASE_NAME")

#             if not mongo_uri:
#                 raise ValueError("MONGO_URI not found in .env")

#             if not database_name:
#                 raise ValueError("DATABASE_NAME not found in .env")

#             MongoService._client = MongoClient(mongo_uri)
#             MongoService._db = MongoService._client[database_name]

#         return MongoService._db

#     @staticmethod
#     def get_tender_section_plan(
#         tender_id: str,
#         company_id: str
#     ) -> Optional[Dict[str, Any]]:
#         """
#         Retrieve TenderSectionPlans document
#         """
#         collection = MongoService.get_database()["TenderSectionPlans"]

#         projection = {
#             "_id": 0,
#             "CompanyId": 1,
#             "TenderId": 1,
#             "FinalJson.ProposalGroups": 1
#         }

#         return collection.find_one(
#             {
#                 "TenderId": tender_id,
#                 "CompanyId": company_id
#             },
#             projection
#         )

#     @staticmethod
#     def get_section_by_name(
#         tender_id: str,
#         company_id: str,
#         section_name: str
#     ) -> Optional[Dict[str, Any]]:
#         """
#         Get a section by its name
#         """
#         plan = MongoService.get_tender_section_plan(
#             tender_id=tender_id,
#             company_id=company_id
#         )

#         if not plan:
#             raise ValueError(
#                 "TenderSectionPlans document not found"
#             )

#         sections = MongoService.extract_sections(plan)

#         print("\nAVAILABLE SECTIONS:")
#         for section in sections:
#             print(f"'{section['SectionName']}'")

#         print(f"\nSEARCHING FOR: '{section_name}'")

#         for section in sections:
#             if (
#                 section["SectionName"]
#                 .strip()
#                 .lower()
#                 ==
#                 section_name
#                 .strip()
#                 .lower()
#             ):
#                 return section

#         return None

#     @staticmethod
#     def extract_sections(
#         tender_section_plan: Dict[str, Any]
#     ) -> List[Dict[str, Any]]:
#         """
#         Extract sections and roll up subsection requirements
#         """
#         sections = []

#         proposal_groups = (
#             tender_section_plan
#             .get("FinalJson", {})
#             .get("ProposalGroups", [])
#         )

#         for group in proposal_groups:
#             for section in group.get("Sections", []):
#                 requirement_ids = list(
#                     section.get("RequirementIds", [])
#                 )

#                 subsections = []

#                 for subsection in section.get(
#                     "SubSections",
#                     []
#                 ):
#                     subsection_requirement_ids = (
#                         subsection.get(
#                             "RequirementIds",
#                             []
#                         )
#                     )

#                     requirement_ids.extend(
#                         subsection_requirement_ids
#                     )

#                     subsections.append(
#                         {
#                             "SubSectionId":
#                                 subsection.get(
#                                     "SubSectionId"
#                                 ),
#                             "SectionId":
#                                 subsection.get(
#                                     "SectionId"
#                                 ),
#                             "SectionName":
#                                 subsection.get(
#                                     "SectionName"
#                                 ),
#                             "RequirementIds":
#                                 subsection_requirement_ids,
#                             "EvidenceRequired":
#                                 subsection.get(
#                                     "EvidenceRequired",
#                                     False
#                                 ),
#                             "CaseStudyRequired":
#                                 subsection.get(
#                                     "CaseStudyRequired",
#                                     False
#                                 )
#                         }
#                     )

#                 requirement_ids = list(
#                     dict.fromkeys(requirement_ids)
#                 )

#                 sections.append(
#                     {
#                         "SectionId":
#                             section.get(
#                                 "SectionId"
#                             ),
#                         "SectionName":
#                             section.get(
#                                 "SectionName"
#                             ),
#                         "RequirementIds":
#                             requirement_ids,
#                         "EvidenceRequired":
#                             section.get(
#                                 "EvidenceRequired",
#                                 False
#                             ),
#                         "CaseStudyRequired":
#                             section.get(
#                                 "CaseStudyRequired",
#                                 False
#                             ),
#                         "SubSections":
#                             subsections
#                     }
#                 )

#         return sections

#     @staticmethod
#     def get_capability_intents(
#         tender_id: str,
#         company_id: str,
#         requirement_ids: List[str]
#     ) -> List[Dict[str, Any]]:
#         """
#         Retrieve only useful capability fields
#         """
#         collection = MongoService.get_database()[
#             "TenderCapabilityIntents"
#         ]

#         document = collection.find_one(
#             {
#                 "TenderId": tender_id,
#                 "CompanyId": company_id
#             },
#             {
#                 "_id": 0,
#                 "FinalJson.CapabilityIntents": 1
#             }
#         )

#         if not document:
#             return []

#         capability_intents = (
#             document
#             .get("FinalJson", {})
#             .get("CapabilityIntents", [])
#         )

#         filtered_requirements = []

#         for item in capability_intents:
#             if item.get("RequirementId") in requirement_ids:
#                 filtered_requirements.append(
#                     {
#                         "RequirementId": item.get(
#                             "RequirementId"
#                         ),
#                         "RequirementText": item.get(
#                             "RequirementText"
#                         ),
#                         "CapabilityIntent": item.get(
#                             "CapabilityIntent",
#                             []
#                         ),
#                         "EvidenceSections": item.get(
#                             "EvidenceSections",
#                             []
#                         ),
#                         "SemanticAnchors": item.get(
#                             "SemanticAnchors",
#                             []
#                         ),
#                         "EvidenceSummary": item.get(
#                             "EvidenceSummary",
#                             ""
#                         ),
#                         "EvidenceGap": item.get(
#                             "EvidenceGap",
#                             False
#                         ),
#                         "MissingEvidenceReason": item.get(
#                             "MissingEvidenceReason",
#                             ""
#                         )
#                     }
#                 )

#         return filtered_requirements

#     @staticmethod
#     def build_search_query(
#         section_name: str,
#         requirements: List[Dict[str, Any]]
#     ) -> str:
#         """
#         Build a search query from section name and requirements
#         """
#         requirement_texts = []

#         for req in requirements:
#             text = req.get(
#                 "RequirementText",
#                 ""
#             )

#             if text:
#                 requirement_texts.append(text)

#         return f"""
# Section:
# {section_name}

# Requirements:
# {' '.join(requirement_texts)}
# """.strip()
    
    
#     @staticmethod
#     def find_best_matching_section(
#     tender_id: str,
#     company_id: str,
#     section_name: str,
#     section_purpose: str
# ) -> Dict[str, Any]:

#     plan = MongoService.get_tender_section_plan(
#         tender_id=tender_id,
#         company_id=company_id
#     )

#     available_sections = []

#     for group in plan["ProposalGroups"]:

#         for section in group["Sections"]:

#             available_sections.append(
#                 {
#                     "SectionId": section["SectionId"],
#                     "SectionName": section["SectionName"]
#                 }
#             )

#     embedding_model = OpenAIEmbeddings(
#         model="text-embedding-3-small",
#         api_key=os.getenv("OPENAI_API_KEY")
#     )

#     query_text = f"""
#     Section Name:
#     {section_name}

#     Section Purpose:
#     {section_purpose}
#     """

#     query_embedding = (
#         embedding_model.embed_query(
#             query_text
#         )
#     )

#     best_match = None
#     best_score = -1

#     for section in available_sections:

#         section_embedding = (
#             embedding_model.embed_query(
#                 section["SectionName"]
#             )
#         )

#         score = cosine_similarity(
#             query_embedding,
#             section_embedding
#         )

#         if score > best_score:

#             best_score = score
#             best_match = section

#     return {
#         "MatchedSectionId":
#             best_match["SectionId"],

#         "MatchedSectionName":
#             best_match["SectionName"],

#         "SimilarityScore":
#             round(best_score, 4)
#     }
#     # @staticmethod
#     # def get_section_requirements(
#     #     tender_id: str,
#     #     company_id: str,
#     #     section_name: str
#     # ) -> Dict[str, Any]:
#     #     """
#     #     Complete helper method

#     #     Returns:
#     #     {
#     #         SectionId,
#     #         SectionName,
#     #         RequirementIds,
#     #         Requirements,
#     #         SearchQuery,
#     #         SubSections
#     #     }
#     #     """
#     #     section = MongoService.get_section_by_name(
#     #         tender_id=tender_id,
#     #         company_id=company_id,
#     #         section_name=section_name
#     #     )

#     #     if not section:
#     #         raise ValueError(
#     #             f"Section '{section_name}' not found"
#     #         )

#     #     requirements = (
#     #         MongoService.get_capability_intents(
#     #             tender_id=tender_id,
#     #             company_id=company_id,
#     #             requirement_ids=section["RequirementIds"]
#     #         )
#     #     )

#     #     search_query = (
#     #         MongoService.build_search_query(
#     #             section_name=section["SectionName"],
#     #             requirements=requirements
#     #         )
#     #     )

#     #     return {
#     #         "SectionId": section["SectionId"],
#     #         "SectionName": section["SectionName"],
#     #         "RequirementIds": section["RequirementIds"],
#     #         "Requirements": requirements,
#     #         "SearchQuery": search_query,
#     #         "SubSections": section.get(
#     #             "SubSections",
#     #             []
#     #         )
#     #     }

import os
from typing import List, Dict, Any, Optional

# Expected standard or community packages for embeddings/similarity
from langchain_openai import OpenAIEmbeddings 
import numpy as np 

from pymongo import MongoClient
from dotenv import load_dotenv
import os
from langchain_mistralai import MistralAIEmbeddings
load_dotenv()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Helper mathematical fallback for cosine similarity using numpy"""
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if not norm_a or not norm_b:
        return 0.0
    return float(dot_product / (norm_a * norm_b))


class MongoService:
    """
    Mongo Service for Tender Section Generator

    Required .env variables:
    MONGO_URI=mongodb://localhost:27017
    DATABASE_NAME=TenderDB
    OPENAI_API_KEY=sk-...

    OR

    MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
    DATABASE_NAME=TenderDB
    """

    _client = None
    _db = None

    @staticmethod
    def get_database():
        if MongoService._db is None:
            mongo_uri = os.getenv("MONGO_URI")
            database_name = os.getenv("DATABASE_NAME")

            if not mongo_uri:
                raise ValueError("MONGO_URI not found in .env")

            if not database_name:
                raise ValueError("DATABASE_NAME not found in .env")

            MongoService._client = MongoClient(mongo_uri)
            MongoService._db = MongoService._client[database_name]

        return MongoService._db

    @staticmethod
    def get_tender_section_plan(
        tender_id: str,
        company_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve TenderSectionPlans document
        """
        collection = MongoService.get_database()["TenderSectionPlans"]

        projection = {
            "_id": 0,
            "CompanyId": 1,
            "TenderId": 1,
            "FinalJson.ProposalGroups": 1
        }

        return collection.find_one(
            {
                "TenderId": tender_id,
                "CompanyId": company_id
            },
            projection
        )

    @staticmethod
    def get_section_by_name(
        tender_id: str,
        company_id: str,
        section_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a section by its name
        """
        plan = MongoService.get_tender_section_plan(
            tender_id=tender_id,
            company_id=company_id
        )

        if not plan:
            raise ValueError(
                "TenderSectionPlans document not found"
            )

        sections = MongoService.extract_sections(plan)

        print("\nAVAILABLE SECTIONS:")
        for section in sections:
            print(f"'{section['SectionName']}'")

        print(f"\nSEARCHING FOR: '{section_name}'")

        for section in sections:
            if (
                section["SectionName"]
                .strip()
                .lower()
                ==
                section_name
                .strip()
                .lower()
            ):
                return section

        return None

    @staticmethod
    def extract_sections(
        tender_section_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract sections and roll up subsection requirements
        """
        sections = []
        if not tender_section_plan:
            return sections

        proposal_groups = (
            tender_section_plan
            .get("FinalJson", {})
            .get("ProposalGroups", [])
        )

        for group in proposal_groups:
            for section in group.get("Sections", []):
                requirement_ids = list(
                    section.get("RequirementIds", [])
                )

                subsections = []

                for subsection in section.get(
                    "SubSections",
                    []
                ):
                    subsection_requirement_ids = (
                        subsection.get(
                            "RequirementIds",
                            []
                        )
                    )

                    requirement_ids.extend(
                        subsection_requirement_ids
                    )

                    subsections.append(
                        {
                            "SubSectionId":
                                subsection.get(
                                    "SubSectionId"
                                ),
                            "SectionId":
                                subsection.get(
                                    "SectionId"
                                ),
                            "SectionName":
                                subsection.get(
                                    "SectionName"
                                ),
                            "RequirementIds":
                                subsection_requirement_ids,
                            "EvidenceRequired":
                                subsection.get(
                                    "EvidenceRequired",
                                    False
                                ),
                            "CaseStudyRequired":
                                subsection.get(
                                    "CaseStudyRequired",
                                    False
                                )
                        }
                    )

                requirement_ids = list(
                    dict.fromkeys(requirement_ids)
                )

                sections.append(
                    {
                        "SectionId":
                            section.get(
                                "SectionId"
                            ),
                        "SectionName":
                            section.get(
                                "SectionName"
                            ),
                        "RequirementIds":
                            requirement_ids,
                        "EvidenceRequired":
                            section.get(
                                "EvidenceRequired",
                                False
                            ),
                        "CaseStudyRequired":
                            section.get(
                                "CaseStudyRequired",
                                False
                            ),
                        "SubSections":
                            subsections
                    }
                )

        return sections

    @staticmethod
    def get_capability_intents(
        tender_id: str,
        company_id: str,
        requirement_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve only useful capability fields
        """
        collection = MongoService.get_database()[
            "TenderCapabilityIntents"
        ]

        document = collection.find_one(
            {
                "TenderId": tender_id,
                "CompanyId": company_id
            },
            {
                "_id": 0,
                "FinalJson.CapabilityIntents": 1
            }
        )

        if not document:
            return []

        capability_intents = (
            document
            .get("FinalJson", {})
            .get("CapabilityIntents", [])
        )

        filtered_requirements = []

        for item in capability_intents:
            if item.get("RequirementId") in requirement_ids:
                filtered_requirements.append(
                    {
                        "RequirementId": item.get(
                            "RequirementId"
                        ),
                        "RequirementText": item.get(
                            "RequirementText"
                        ),
                        "CapabilityIntent": item.get(
                            "CapabilityIntent",
                            []
                        ),
                        "EvidenceSections": item.get(
                            "EvidenceSections",
                            []
                        ),
                        "SemanticAnchors": item.get(
                            "SemanticAnchors",
                            []
                        ),
                        "EvidenceSummary": item.get(
                            "EvidenceSummary",
                            ""
                        ),
                        "EvidenceGap": item.get(
                            "EvidenceGap",
                            False
                        ),
                        "MissingEvidenceReason": item.get(
                            "MissingEvidenceReason",
                            ""
                        )
                    }
                )

        return filtered_requirements

    @staticmethod
    def build_search_query(
        section_name: str,
        requirements: List[Dict[str, Any]]
    ) -> str:
        """
        Build a search query from section name and requirements
        """
        requirement_texts = []

        for req in requirements:
            text = req.get(
                "RequirementText",
                ""
            )

            if text:
                requirement_texts.append(text)

        return f"""
Section:
{section_name}

Requirements:
{' '.join(requirement_texts)}
""".strip()

    @staticmethod
    def build_custom_section_requirements(
        section_name: str,
        section_purpose: str = ""
    ) -> Dict[str, Any]:
        """
        Build section data for user-requested sections that are not present in
        TenderSectionPlans. This keeps custom section generation evidence-bound
        while avoiding a hard dependency on a precomputed proposal plan.
        """
        requirement_text = (
            section_purpose.strip()
            or f"Write a complete proposal-ready section for {section_name}."
        )

        requirement = {
            "RequirementId": "custom-section-requirement",
            "RequirementText": requirement_text,
            "CapabilityIntent": [section_name],
            "EvidenceSections": [],
            "SemanticAnchors": [
                section_name,
                *[
                    token.strip()
                    for token in section_purpose.replace(",", " ").split()
                    if token.strip()
                ],
            ],
            "EvidenceSummary": "",
            "EvidenceGap": False,
            "MissingEvidenceReason": ""
        }

        search_query = f"""
Section:
{section_name}

Purpose:
{section_purpose}

Requirements:
{requirement_text}
""".strip()

        return {
            "SectionId": section_name,
            "SectionName": section_name,
            "RequirementIds": [requirement["RequirementId"]],
            "Requirements": [requirement],
            "SearchQuery": search_query,
            "SubSections": [],
            "IsCustomSection": True
        }

    @staticmethod
    def find_best_matching_section(
        tender_id: str,
        company_id: str,
        section_name: str,
        section_purpose: str
    ) -> Dict[str, Any]:
        """
        Finds the closest section using OpenAI embeddings and cosine similarity.
        Always returns the best match regardless of how low the score is.
        """
        plan = MongoService.get_tender_section_plan(
            tender_id=tender_id,
            company_id=company_id
        )

        if not plan:
            raise ValueError(
                "TenderSectionPlans document not found"
            )

        sections = MongoService.extract_sections(plan)

        if not sections:
            raise ValueError(
                "No sections found"
            )
    #     embedding_model = MistralAIEmbeddings(
    # model="mistral-embed",
    # api_key=os.getenv("MISTRAL_API_KEY")


        embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        query_text = f"""
Section Name:
{section_name}

Section Purpose:
{section_purpose}
"""

        query_embedding = embedding_model.embed_query(query_text)

        best_section = None
        # Initializing score lower to correctly capture negative correlations if they happen
        best_score = -1.0

        for section in sections:
            section_text = f"""
Section Name:
{section['SectionName']}
"""
            section_embedding = embedding_model.embed_query(section_text)
            score = cosine_similarity(query_embedding, section_embedding)

            if score > best_score:
                best_score = score
                best_section = section

        # Boundary fallback to ensure best_section is never null before dictionary building
        if not best_section and sections:
            best_section = sections[0]

        return {
            "SectionId": best_section["SectionId"],
            "SectionName": best_section["SectionName"],
            "SimilarityScore": round(best_score, 4)
        }
    @staticmethod
    def get_section_requirements(
        tender_id: str,
        company_id: str,
        section_name: str
    ) -> Dict[str, Any]:
        """
        Complete helper method to fetch requirements for a verified section name.
        """
        section = MongoService.get_section_by_name(
            tender_id=tender_id,
            company_id=company_id,
            section_name=section_name
        )

        if not section:
            raise ValueError(
                f"Section '{section_name}' not found"
            )

        requirements = (
            MongoService.get_capability_intents(
                tender_id=tender_id,
                company_id=company_id,
                requirement_ids=section["RequirementIds"]
            )
        )

        search_query = (
            MongoService.build_search_query(
                section_name=section["SectionName"],
                requirements=requirements
            )
        )

        return {
            "SectionId": section["SectionId"],
            "SectionName": section["SectionName"],
            "RequirementIds": section["RequirementIds"],
            "Requirements": requirements,
            "SearchQuery": search_query,
            "SubSections": section.get("SubSections", [])
        }
