import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


class ProposalSummaryRepository:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI")
        database_name = os.getenv("MONGODB_DATABASE")
        collection_name = os.getenv("TENDER_PROPOSAL_SUMMARY_COLLECTION")

        if not mongo_uri:
            raise ValueError("MONGODB_URI is not configured.")

        if not database_name:
            raise ValueError("MONGODB_DATABASE is not configured.")

        if not collection_name:
            raise ValueError("TENDER_PROPOSAL_SUMMARY_COLLECTION is not configured.")

        client = MongoClient(mongo_uri)
        self.collection = client[database_name][collection_name]

    def save_proposal_summary(
        self,
        *,
        response: dict,
        is_regenerate: bool,
    ):
        """
        Saves the generated proposal summary.

        Status:
            Active        -> is_regenerate=False
            Regenerating  -> is_regenerate=True
        """

        status = "Regenerating" if is_regenerate else "Active"

        document = {
            "companyId": response["company_id"],
            "tenderId": response["tender_id"],
            "proposalPlanId": response["proposal_plan_id"],
            "userId": response["user_id"],
            "status": status,
            "isRegenerate": is_regenerate,
            "sections": [],
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
        }

        for section in response.get("section_results", []):
            generated = section["generated_content"]

            document["sections"].append({
                "sectionId": generated["SectionId"],
                "sectionName": generated["SectionName"],
                "generatedContent": generated["GeneratedContent"],
                "generatedSubSections": generated.get("GeneratedSubSections", []),
                "evaluationCriteria": generated.get("EvaluationCriteria", []),
                "internalReview": generated.get("InternalReview", {}),
            })

        filter_query = {
            "companyId": document["companyId"],
            "tenderId": document["tenderId"],
            "proposalPlanId": document["proposalPlanId"],
        }

        self.collection.update_one(
            filter_query,
            {
                "$set": {
                    "status": document["status"],
                    "isRegenerate": document["isRegenerate"],
                    "sections": document["sections"],
                    "updatedAt": document["updatedAt"],
                },
                "$setOnInsert": {
                    "companyId": document["companyId"],
                    "tenderId": document["tenderId"],
                    "proposalPlanId": document["proposalPlanId"],
                    "userId": document["userId"],
                    "createdAt": document["createdAt"],
                },
            },
            upsert=True,
        )