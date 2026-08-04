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
            raise ValueError("MONGO_URI is not configured.")

        if not database_name:
            raise ValueError("MONGODB_DATABASE or MONGO_DB_NAME is not configured.")

        if not collection_name:
            raise ValueError("TENDER_PROPOSAL_SUMMARY_COLLECTION is not configured.")

        self.client = MongoClient(mongo_uri)
        self.collection = self.client[database_name][collection_name]

    def close(self):
        self.client.close()

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
        now = datetime.now(timezone.utc)
        proposal_plan_id = response.get("proposal_plan_id")
        proposal_id = response.get("proposal_id") or proposal_plan_id

        if not proposal_plan_id:
            raise ValueError("proposal_plan_id is required to save proposal summary.")

        document = {
            "companyId": response["company_id"],
            "tenderId": response["tender_id"],
            "proposalId": proposal_id,
            "proposalPlanId": proposal_plan_id,
            "userId": response["user_id"],
            "userName": response["user_name"],
            "projectId": response["project_id"],
            "createdBy": response["user_name"],
            "CreatedBy": response["user_name"],
            "status": status,
            "isRegenerate": is_regenerate,
            "sections": [],
            "createdAt": now,
            "updatedAt": now,
        }

        for section in response.get("section_results", []):
            generated = section.get("generated_content")

            if not generated:
                continue

            document["sections"].append({
                "sectionId": generated.get("SectionId") or section.get("section_id"),
                "sectionName": generated.get("SectionName") or section.get("section_name"),
                "generatedContent": generated.get("GeneratedContent"),
                "generatedSubSections": generated.get("GeneratedSubSections", []),
                "evaluationCriteria": generated.get("EvaluationCriteria", []),
                "internalReview": generated.get("InternalReview", {}),
            })

        if is_regenerate:
            self.collection.insert_one(document)
            return document["proposalId"]

        filter_query = {
            "companyId": document["companyId"],
            "tenderId": document["tenderId"],
            "proposalPlanId": document["proposalPlanId"],
        }

        set_on_insert = {
            "companyId": document["companyId"],
            "tenderId": document["tenderId"],
            "proposalId": document["proposalId"],
            "proposalPlanId": document["proposalPlanId"],
            "createdAt": document["createdAt"],
        }

        self.collection.update_one(
            filter_query,
            {
                "$set": {
                    "userId": document["userId"],
                    "userName": document["userName"],
                    "projectId": document["projectId"],
                    "createdBy": document["createdBy"],
                    "CreatedBy": document["CreatedBy"],
                    "status": document["status"],
                    "isRegenerate": document["isRegenerate"],
                    "sections": document["sections"],
                    "updatedAt": document["updatedAt"],
                },
                "$setOnInsert": set_on_insert,
            },
            upsert=True,
        )
        return None
