import os
import uuid
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

load_dotenv()


class EmbeddingService:

    COLLECTION_NAME = "CPDocuments"

    embedding_model = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
    )

    qdrant_client = QdrantClient(url="http://localhost:6333")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200
    )

    PAYLOAD_COMPANY_ID_KEYS = ("CompanyId", "company_id")
    PAYLOAD_TEXT_KEYS = ("Text", "text")

    @staticmethod
    def _payload_value(payload: dict, keys: tuple[str, ...], default=None):
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value
        return default

    @staticmethod
    def create_collection():
        collections = EmbeddingService.qdrant_client.get_collections().collections
        existing = [collection.name for collection in collections]

        if EmbeddingService.COLLECTION_NAME in existing:
            print("Collection already exists")
            return

        EmbeddingService.qdrant_client.create_collection(
            collection_name=EmbeddingService.COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print("Collection created")

    @staticmethod
    def embed_company_document(company_id: str, document_text: str):
        EmbeddingService.create_collection()

        chunks = EmbeddingService.text_splitter.split_text(document_text)
        embeddings = EmbeddingService.embedding_model.embed_documents(chunks)

        points = []
        for chunk, vector in zip(chunks, embeddings):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    # Note: These are lowercase payload keys
                    payload={"company_id": company_id, "text": chunk},
                )
            )

        EmbeddingService.qdrant_client.upsert(
            collection_name=EmbeddingService.COLLECTION_NAME, points=points
        )
        print(f"{len(points)} chunks inserted")

    @staticmethod
    def embed_company_file(company_id: str, file_path: str):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            document_text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        else:
            document_text = path.read_text(encoding="utf-8")

        if not document_text.strip():
            raise ValueError(f"No text could be extracted from: {file_path}")

        EmbeddingService.embed_company_document(
            company_id=company_id, document_text=document_text
        )

    @staticmethod
    def search_company_documents(company_id: str, query: str, limit: int = 5):
        query_vector = EmbeddingService.embedding_model.embed_query(query)

        for company_id_key in EmbeddingService.PAYLOAD_COMPANY_ID_KEYS:
            results = EmbeddingService.qdrant_client.search(
                collection_name=EmbeddingService.COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                query_filter={
                    "must": [
                        {"key": company_id_key, "match": {"value": company_id}}
                    ]
                },
            )
            if results:
                return results

        return []

    @staticmethod
    def inspect_collection(limit: int = 5, with_vectors: bool = False):
        collection_info = EmbeddingService.qdrant_client.get_collection(
            collection_name=EmbeddingService.COLLECTION_NAME
        )

        points, next_page = EmbeddingService.qdrant_client.scroll(
            collection_name=EmbeddingService.COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=with_vectors,
        )

        print("Collection:")
        pprint(collection_info)
        print("\nSample points:")

        for point in points:
            payload = point.payload or {}
            text = EmbeddingService._payload_value(
                payload, EmbeddingService.PAYLOAD_TEXT_KEYS
            )

            print("-" * 80)
            print(f"id: {point.id}")
            print(f"payload_keys: {list(payload.keys())}")

            company_id = EmbeddingService._payload_value(
                payload, EmbeddingService.PAYLOAD_COMPANY_ID_KEYS
            )
            if company_id:
                print(f"company_id: {company_id}")

            if text:
                preview = text[:500].replace("\n", " ")
                print(f"text_preview: {preview}")

            if with_vectors and point.vector is not None:
                if isinstance(point.vector, dict):
                    vector_sizes = {
                        name: len(vector)
                        for name, vector in point.vector.items()
                    }
                    print(f"vector_sizes: {vector_sizes}")
                else:
                    print(f"vector_size: {len(point.vector)}")

        print(f"\nnext_page_offset: {next_page}")

    @staticmethod
    def retrieve_context(
        company_id: str, section_name: str, purpose: str, limit: int = 3
    ):  # Fixed class indentation block
        search_query = f"""
        Tender Section:
        {section_name}

        Purpose:
        {purpose}

        Find relevant products, services,
        capabilities, expertise, implementations,
        and technical details.
        """

        query_vector = EmbeddingService.embedding_model.embed_query(
            search_query
        )

        response = None
        for company_id_key in EmbeddingService.PAYLOAD_COMPANY_ID_KEYS:
            response = EmbeddingService.qdrant_client.query_points(
                collection_name=EmbeddingService.COLLECTION_NAME,
                query=query_vector,
                limit=limit,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key=company_id_key,
                            match=MatchValue(value=company_id),
                        )
                    ]
                ),
                with_payload=True,
            )
            if response.points:
                break

        relevant_chunks = []
        for result in response.points:
            payload = result.payload or {}
            relevant_chunks.append(
                {
                    "score": result.score,
                    "chunk_id": payload.get("ChunkId") or payload.get("ChunckId"),
                    "document_id": payload.get("DocumentId"),
                    "document_name": payload.get("DocumentName")
                    or payload.get("document_name"),
                    "document_type": payload.get("DocumentType"),
                    "title": payload.get("Title") or payload.get("title"),
                    "related_section": payload.get("RelatedSection")
                    or payload.get("related_section"),
                    "text": EmbeddingService._payload_value(
                        payload, EmbeddingService.PAYLOAD_TEXT_KEYS, ""
                    ),
                }
            )

        return relevant_chunks


# --- Execution Example ---
if __name__ == "__main__":
    # EmbeddingService.create_collection()
    # EmbeddingService.embed_company_file(
    #     company_id="bharat_tech_001",
    #     file_path="/Users/apple/company_sumarry_gen/bharat_tech_solutions_company_profile 2.pdf"
    # )

    results = EmbeddingService.retrieve_context(
        company_id="6a1dd60c16798335df3b0052",
        section_name="Potential capabilities",
        purpose="Potential capabilities",
    )
    pprint(results)
