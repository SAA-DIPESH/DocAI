import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from pprint import pprint

from app.services.mongo.mongo_services import MongoService
from app.services.qdrant.qdrant_services import QdrantService


def test_full_retrieval():

    tender_id = "6a2ffcf49b077f038d5cce85"

    company_id = "6a202607915f3a8b0831fec6"

    section_name = (
        "Company Overview and Capability Statement"
    )

    section_data = (
        MongoService.get_section_requirements(
            tender_id=tender_id,
            company_id=company_id,
            section_name=section_name
        )
    )

    print("\n" + "=" * 100)
    print("SECTION DATA")
    print("=" * 100)

    pprint(section_data)

    search_query = section_data["SearchQuery"]

    print("\n" + "=" * 100)
    print("SEARCH QUERY")
    print("=" * 100)

    print(search_query)

    result = (
        QdrantService.retrieve_context_for_section(
            company_id=company_id,
            search_query=search_query,
            collection_name="CPDocuments",
            limit=3
        )
    )

    print( "=" * 100)
    print("RETRIEVED CHUNKS")
    print("=" * 100)

    pprint(result["Chunks"])

    print("\n" + "=" * 100)
    print("CONTEXT")
    print("=" * 100)

    print(result["Context"])


if __name__ == "__main__":
    test_full_retrieval()