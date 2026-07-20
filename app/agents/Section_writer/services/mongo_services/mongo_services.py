import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def _required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    joined_names = " or ".join(names)
    raise ValueError(f"{joined_names} is required for Section Writer MongoDB context.")


# class ContextBuilder:

#     def __init__(self):
#         mongo_uri = _required_env("MONGO_URI")
#         database_name = _required_env("MONGODB_DATABASE", "MONGO_DB_NAME")
#         section_collection_name = _required_env(
#             "TENDER_SECTION_PLAN_COLLECTION",
#             "TENDER_SECTION_COLLECTION",
#             "TENDER_COLLECTION_NAME",
#         )
#         evidence_collection_name = _required_env(
#             "EVIDENCE_SUMMARY_COLLECTION",
#             "DEDUPLICATION_REQUIREMENTS_COLLECTION",
#             "REQUIREMENTS_COLLECTION",
#         )
#         win_theme_collection_name = _required_env(
#             "WIN_THEME_COLLECTION",
#             "DOCAI_COLLECTION",
#         )
#         evaluation_criteria_collection_name = _required_env(
#             "EVALUATION_CRITERIA_COLLECTION",
#         )

#         self.client = MongoClient(mongo_uri)

#         self.db = self.client[database_name]

#         self.section_collection = self.db[section_collection_name]

#         self.evidence_collection = self.db[evidence_collection_name]

#         self.win_theme_collection = self.db[win_theme_collection_name]

#         self.evaluation_criteria_collection = self.db[
#             evaluation_criteria_collection_name
#         ]

#     def close(self):
#         self.client.close()

#     def get_tender_sections(
#         self,
#         tender_id: str,
#         company_id: str
#     ) -> List[Dict[str, Any]]:

#         document = self.section_collection.find_one(
#             {
#                 "TenderId": tender_id,
#                 "CompanyId": company_id
#             },
#             {
#                 "_id": 0,
#                 "FinalJson.ProposalGroups.Sections": 1,
#                 "FinalJson.ProposalGroups.GroupName": 1
#             }
#         )

#         sections = []

#         if not document:
#             return sections

#         proposal_groups = (
#             document.get("FinalJson", {})
#             .get("ProposalGroups", [])
#         )

#         for group in proposal_groups:

#             group_name = group.get("GroupName")

#             for section in group.get("Sections", []):

#                 section["GroupName"] = group_name

#                 sections.append(section)

#         return sections

#     def add_evidence_summary(
#         self,
#         sections: List[Dict[str, Any]],
#         tender_id: str,
#         company_id: str
#     ) -> List[Dict[str, Any]]:

#         for section in sections:

#             requirement_ids = section.get("RequirementIds", [])

#             if not requirement_ids:
#                 section["EvidenceSummary"] = []
#                 continue

#             pipeline = [
#                 {
#                     "$match": {
#                         "TenderId": tender_id,
#                         "CompanyId": company_id
#                     }
#                 },
#                 {
#                     "$unwind": "$FinalJson.CanonicalRequirements"
#                 },
#                 {
#                     "$match": {
#                         "FinalJson.CanonicalRequirements.CanonicalRequirementId": {
#                             "$in": requirement_ids
#                         }
#                     }
#                 },
#                 {
#                     "$replaceRoot": {
#                         "newRoot": "$FinalJson.CanonicalRequirements"
#                     }
#                 }
#             ]

#             section["EvidenceSummary"] = list(
#                 self.evidence_collection.aggregate(pipeline)
#             )

#         return sections

#     def get_win_themes(
#         self,
#         company_id: str
#     ) -> List[Dict[str, Any]]:
#         """
#         Returns generated win themes for a company.
#         """

#         pipeline = [
#             {
#                 "$match": {
#                     "$or": [
#                         {"CompanyId": company_id},
#                         {"company_id": company_id},
#                         {"generated_themes.company_id": company_id},
#                     ]
#                 },
#             },
#             {
#                 "$unwind": {
#                     "path": "$generated_themes",
#                     "preserveNullAndEmptyArrays": True,
#                 }
#             },
#             {
#                 "$match": {
#                     "$or": [
#                         {"CompanyId": company_id},
#                         {"company_id": company_id},
#                         {"generated_themes.company_id": company_id},
#                     ]
#                 }
#             },
#             {
#                 "$project": {
#                     "_id": 0,
#                     "theme": {
#                         "$ifNull": ["$generated_themes", "$$ROOT"]
#                     },
#                 }
#             },
#             {"$replaceRoot": {"newRoot": "$theme"}},
#         ]

#         return list(self.win_theme_collection.aggregate(pipeline))

#     def get_evaluation_criteria(
#         self,
#         tender_id: str,
#         company_id: str,
#     ) -> List[Dict[str, Any]]:
#         document = self.evaluation_criteria_collection.find_one(
#             {
#                 "$or": [
#                     {"CompanyId": company_id, "TenderId": tender_id},
#                     {"company_id": company_id, "tender_id": tender_id},
#                 ]
#             },
#             {"_id": 0},
#             sort=[("CreatedAt", -1), ("_id", -1)],
#         )

#         if not document:
#             return []

#         criteria = (
#             document.get("EvaluationCriteria")
#             or document.get("Criteria")
#             or document.get("FinalJson", {}).get("EvaluationCriteria")
#             or document.get("FinalJson", {}).get("Criteria")
#             or []
#         )

#         return criteria if isinstance(criteria, list) else [criteria]

#     def add_evaluation_criteria(
#         self,
#         sections: List[Dict[str, Any]],
#         tender_id: str,
#         company_id: str,
#     ) -> List[Dict[str, Any]]:
#         criteria = self.get_evaluation_criteria(
#             tender_id=tender_id,
#             company_id=company_id,
#         )

#         for section in sections:
#             section.setdefault("EvaluationCriteria", criteria)

#         return sections

#     def build_context(
#         self,
#         tender_id: str,
#         company_id: str
#     ) -> Dict[str, Any]:

#         sections = self.get_tender_sections(
#             tender_id=tender_id,
#             company_id=company_id
#         )

#         sections = self.add_evidence_summary(
#             sections=sections,
#             tender_id=tender_id,
#             company_id=company_id
#         )

#         sections = self.add_evaluation_criteria(
#             sections=sections,
#             tender_id=tender_id,
#             company_id=company_id,
#         )

#         return {
#             "Sections": sections,
#             "WinThemes": self.get_win_themes(company_id=company_id),
#         }

class ContextBuilder:

    def __init__(self):
        mongo_uri = _required_env("MONGO_URI")

        database_name = _required_env(
            "MONGODB_DATABASE",
            "MONGO_DB_NAME",
        )

        section_collection_name = _required_env(
            "TENDER_SECTION_PLAN_COLLECTION",
            "TENDER_SECTION_COLLECTION",
            "TENDER_COLLECTION_NAME",
        )

        evidence_collection_name = _required_env(
            "EVIDENCE_SUMMARY_COLLECTION",
            "REQUIREMENTS_COLLECTION",
        )

        win_theme_collection_name = _required_env(
            "WIN_THEME_COLLECTION",
            "DOCAI_COLLECTION",
        )

        evaluation_criteria_collection_name = _required_env(
            "EVALUATION_CRITERIA_COLLECTION",
        )

        self.client = MongoClient(mongo_uri)

        self.db = self.client[database_name]

        self.section_collection = self.db[
            section_collection_name
        ]

        self.evidence_collection = self.db[
            evidence_collection_name
        ]

        self.win_theme_collection = self.db[
            win_theme_collection_name
        ]

        self.evaluation_criteria_collection = self.db[
            evaluation_criteria_collection_name
        ]

    def close(self):
        self.client.close()

    @staticmethod
    def _get_status(is_regenerate: bool) -> str:
        return (
            "Regenerating"
            if is_regenerate
            else "Active"
        )

    def get_tender_sections(
        self,
        tender_id: str,
        company_id: str,
        status: str,
    ) -> List[Dict[str, Any]]:

        document = self.section_collection.find_one(
            {
                "TenderId": tender_id,
                "CompanyId": company_id,
                "Status": status,
            },
            {
                "_id": 0,
                "JsonOutput.ProposalGroups.Sections": 1,
                "JsonOutput.ProposalGroups.GroupName": 1,
            },
        )

        sections = []

        if not document:
            return sections

        proposal_groups = (
            document.get("JsonOutput", {})
            .get("ProposalGroups", [])
        )

        for group in proposal_groups:

            group_name = group.get("GroupName")

            for section in group.get("Sections", []):

                section["GroupName"] = group_name

                sections.append(section)

        return sections

    def add_evidence_summary(
        self,
        sections: List[Dict[str, Any]],
        tender_id: str,
        company_id: str,
        status: str,
    ) -> List[Dict[str, Any]]:

        for section in sections:

            requirement_ids = section.get(
                "RequirementIds",
                [],
            )

            if not requirement_ids:
                section["EvidenceSummary"] = []
                continue

            pipeline = [
                {
                    "$match": {
                        "TenderId": tender_id,
                        "CompanyId": company_id,
                        "Status": status,
                    }
                },
                {
                    "$unwind": "$JsonOutput.CanonicalRequirements"
                },
                {
                    "$match": {
                        "JsonOutput.CanonicalRequirements.CanonicalRequirementId": {
                            "$in": requirement_ids
                        }
                    }
                },
                {
                    "$replaceRoot": {
                        "newRoot": "$JsonOutput.CanonicalRequirements"
                    }
                },
            ]

            section["EvidenceSummary"] = list(
                self.evidence_collection.aggregate(
                    pipeline
                )
            )

        return sections

    def get_win_themes(
        self,
        company_id: str,
        status: str,
    ) -> List[Dict[str, Any]]:
        """
        Returns win themes for the requested status.
        If no document exists for that status, falls back to CompanyId only.
        """

        pipeline = [
            {
                "$match": {
                    "$or": [
                        {
                            "CompanyId": company_id,
                            "Status": status,
                        },
                        {
                            "company_id": company_id,
                            "status": status,
                        },
                        {
                            "generated_themes.company_id": company_id,
                            "Status": status,
                        },
                    ]
                }
            },
            {
                "$unwind": {
                    "path": "$generated_themes",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "theme": {
                        "$ifNull": [
                            "$generated_themes",
                            "$$ROOT",
                        ]
                    },
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": "$theme"
                }
            },
        ]

        themes = list(
            self.win_theme_collection.aggregate(pipeline)
        )

        if themes:
            return themes

        # ------------------------------
        # Fallback: CompanyId only
        # ------------------------------

        fallback_pipeline = [
            {
                "$match": {
                    "$or": [
                        {"CompanyId": company_id},
                        {"company_id": company_id},
                        {"generated_themes.company_id": company_id},
                    ]
                }
            },
            {
                "$unwind": {
                    "path": "$generated_themes",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "theme": {
                        "$ifNull": [
                            "$generated_themes",
                            "$$ROOT",
                        ]
                    },
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": "$theme"
                }
            },
        ]

        return list(
            self.win_theme_collection.aggregate(
                fallback_pipeline
            )
        )

    def get_evaluation_criteria(
        self,
        tender_id: str,
        company_id: str,
    ) -> List[Dict[str, Any]]:

        document = self.evaluation_criteria_collection.find_one(
            {
                "$or": [
                    {
                        "CompanyId": company_id,
                        "TenderId": tender_id,
                    },
                    {
                        "company_id": company_id,
                        "tender_id": tender_id,
                    },
                ]
            },
            {"_id": 0},
            sort=[
                ("CreatedAt", -1),
                ("_id", -1),
            ],
        )

        if not document:
            return []

        criteria = (
            document.get(
                "EvaluationCriteria"
            )
            or document.get("Criteria")
            or document.get(
                "JsonOutput",
                {},
            ).get("EvaluationCriteria")
            or document.get(
                "JsonOutput",
                {},
            ).get("Criteria")
            or []
        )

        return (
            criteria
            if isinstance(criteria, list)
            else [criteria]
        )

    def add_evaluation_criteria(
        self,
        sections: List[Dict[str, Any]],
        tender_id: str,
        company_id: str,
    ) -> List[Dict[str, Any]]:

        criteria = self.get_evaluation_criteria(
            tender_id=tender_id,
            company_id=company_id,
        )

        for section in sections:
            section.setdefault(
                "EvaluationCriteria",
                criteria,
            )

        return sections

    def build_context(
        self,
        tender_id: str,
        company_id: str,
        is_regenerate: bool,
    ) -> Dict[str, Any]:

        status = self._get_status(
            is_regenerate
        )

        sections = self.get_tender_sections(
            tender_id=tender_id,
            company_id=company_id,
            status=status,
        )

        sections = self.add_evidence_summary(
            sections=sections,
            tender_id=tender_id,
            company_id=company_id,
            status=status,
        )

        sections = self.add_evaluation_criteria(
            sections=sections,
            tender_id=tender_id,
            company_id=company_id,
        )

        return {
            "Sections": sections,
            "WinThemes": self.get_win_themes(
                company_id=company_id,
                status=status
                
            ),
        }
###################### OUTPUT EXAMPLE ######################


#   {
#     "SectionId": "sec-001",
#     "SectionName": "Mandatory Declarations",
#     "SectionDescription": "Provide mandatory declarations confirming the provider’s acceptance of being appointed to the Dynamic Purchasing System (DPS) for Vehicle Telematics & Journey Recorders as per the compliance and legal requirements outlined in the tender.",
#     "Required": true,
#     "Priority": "High",
#     "RequirementIds": [
#       "CR5"
#     ],
#     "EvaluationCriteria": [],
#     "SubSections": [],
#     "EvidenceRequired": false,
#     "CaseStudyRequired": false,
#     "Dependencies": [],
#     "AutoCreated": false,
#     "AutoCreatedReason": "None",
#     "GroupName": "None"
#   }


############################################################



# def get_sections_with_evidence_summary(
#     sections: List[Dict[str, Any]],
#     tender_id: str,
#     company_id: str
# ) -> List[Dict[str, Any]]:

#     client = MongoClient(MONGO_URI)

#     db = client[os.getenv("MONGODB_DATABASE")]
#     evidence_collection = db[os.getenv("EVIDENCE_SUMMARY_COLLECTION")]

#     for section in sections:

#         requirement_ids = section.get("RequirementIds", [])

#         if not requirement_ids:
#             section["EvidenceSummary"] = []
#             continue

#         pipeline = [
#             {
#                 "$match": {
#                     "TenderId": tender_id,
#                     "CompanyId": company_id
#                 }
#             },
#             {
#                 "$unwind": "$FinalJson.CanonicalRequirements"
#             },
#             {
#                 "$match": {
#                     "FinalJson.CanonicalRequirements.CanonicalRequirementId": {
#                         "$in": requirement_ids
#                     }
#                 }
#             },
#             {
#                 "$replaceRoot": {
#                     "newRoot": "$FinalJson.CanonicalRequirements"
#                 }
#             }
#         ]

#         section["EvidenceSummary"] = list(
#             evidence_collection.aggregate(pipeline)
#         )

#     client.close()

#     return sections

# sections = get_tender_sections(
#     db_name=os.getenv("DATABASE_NAME"),
#     collection_name=os.getenv("TENDER_SECTION_COLLECTION"),
#     tender_id="6a1d4ca365788fd338df68dc",
#     company_id="6a1d37b5b500467c0a6f03c5"
# )

# result = get_sections_with_evidence_summary(
#     sections=sections,
#     tender_id="6a1d4ca365788fd338df68dc",
#     company_id="6a1d37b5b500467c0a6f03c5"
# )

# from pprint import pprint
# pprint(result)


############################################ Testing #####################################################
