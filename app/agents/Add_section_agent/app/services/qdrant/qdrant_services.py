import os
from typing import List, Dict, Any
from langchain_mistralai import MistralAIEmbeddings

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)

from langchain_openai import OpenAIEmbeddings

load_dotenv()


class QdrantService:

    _client = None
    _embedding_model = None

    @staticmethod
    def get_client():

        if QdrantService._client is None:

            qdrant_url = os.getenv("QDRANT_URL")

            if not qdrant_url:
                raise ValueError(
                    "QDRANT_URL not found in .env"
                )

            QdrantService._client = QdrantClient(
                url=qdrant_url
            )

        return QdrantService._client

    @staticmethod
    def get_embedding_model():

        if QdrantService._embedding_model is None:

            QdrantService._embedding_model = (
#                 MistralAIEmbeddings(
#     model="mistral-embed",
#     api_key=os.getenv("MISTRAL_API_KEY")
# )
                OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=os.getenv(
                        "OPENAI_API_KEY"
                    )
                )
            )

        return QdrantService._embedding_model

    @staticmethod
    def retrieve_company_context(
        company_id: str,
        search_query: str,
        collection_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:

        client = QdrantService.get_client()

        embedding_model = (
            QdrantService.get_embedding_model()
        )

        query_vector = (
            embedding_model.embed_query(
                search_query
            )
        )

        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="CompanyId",
                        match=MatchValue(
                            value=company_id
                        )
                    )
                ]
            ),
            limit=limit
        )

        chunks = []

        for point in results.points:

            payload = point.payload

            chunks.append(
                {
                    "ChunkId":
                        payload.get(
                            "ChunkId"
                        ),

                    "DocumentId":
                        payload.get(
                            "DocumentId"
                        ),

                    "DocumentName":
                        payload.get(
                            "DocumentName"
                        ),

                    "DocumentType":
                        payload.get(
                            "DocumentType"
                        ),

                    "RelatedSection":
                        payload.get(
                            "RelatedSection"
                        ),

                    "Text":
                        payload.get(
                            "Text"
                        ),

                    "Score":
                        point.score
                }
            )

        return chunks

    @staticmethod
    def build_context(
        chunks: List[Dict[str, Any]]
    ) -> str:

        if not chunks:
            return ""

        return "\n\n".join(
            chunk["Text"]
            for chunk in chunks
            if chunk.get("Text")
        )

    @staticmethod
    def retrieve_context_for_section(
        company_id: str,
        search_query: str,
        collection_name: str,
        limit: int = 3
    ) -> Dict[str, Any]:

        chunks = (
            QdrantService.retrieve_company_context(
                company_id=company_id,
                search_query=search_query,
                collection_name=collection_name,
                limit=limit
            )
        )

        context = (
            QdrantService.build_context(
                chunks
            )
        )

        return {
            "Chunks": chunks,
            "Context": context
        }


