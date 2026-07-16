from datetime import datetime
from typing import Any

from bson import ObjectId

from .mongo_client import _get_database


def _serialize_document(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [_serialize_document(item) for item in value]

    if isinstance(value, dict):
        return {
            key: _serialize_document(item)
            for key, item in value.items()
        }

    return value


class TaxonomyRepository:
    COLLECTION = "DocumentTaxonomy"

    @classmethod
    def _collection(cls):
        return _get_database()[cls.COLLECTION]

    @classmethod
    def find_by_scope(
        cls,
        *,
        cpv_code: str,
        cpv_set_for: str,
        tender_id: str | None = None,
        company_id: str | None = None,
    ) -> dict | None:
        query = {
            "CPVsetfor": cpv_set_for,
            "$or": [
                {"cpvProfile.primaryCpvCode": cpv_code},
                {"cpv.code": cpv_code},
                {"primaryCpvCode": cpv_code},
            ],
        }

        if cpv_set_for == "Tender":
            query["tenderId"] = tender_id
            if company_id:
                query["companyId"] = company_id
        else:
            query["tenderId"] = None
            query["companyId"] = company_id

        document = cls._collection().find_one(query)

        if not document:
            return None

        return _serialize_document(document)

    @classmethod
    def find_by_cpv_code(cls, cpv_code: str) -> dict | None:
        document = cls._collection().find_one(
            {
                "$or": [
                    {"cpvProfile.primaryCpvCode": cpv_code},
                    {"cpv.code": cpv_code},
                    {"primaryCpvCode": cpv_code},
                ]
            }
        )

        if not document:
            return None

        return _serialize_document(document)

    @classmethod
    def save(cls, taxonomy_json: dict):
        document = {
            **taxonomy_json,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }

        result = cls._collection().insert_one(document)

        document["_id"] = str(result.inserted_id)

        return _serialize_document(document)
