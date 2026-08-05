import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from fastembed import SparseTextEmbedding

from langchain_openai import OpenAIEmbeddings

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    SparseVector,
)

load_dotenv()


# ---------------------------------------------------------
# Singleton Models (Loaded only once)
# ---------------------------------------------------------

QDRANT_CLIENT = QdrantClient(
    url=os.getenv("QDRANT_URL"),
)

EMBEDDING_MODEL = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)

SPARSE_MODEL = SparseTextEmbedding(
    model_name="Qdrant/bm25"
)


def _load_cross_encoder(model_name: str):
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(model_name)

    except Exception as exc:
        raise RuntimeError(
            f"Unable to load CrossEncoder : {model_name}"
        ) from exc


RERANKER = _load_cross_encoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# ---------------------------------------------------------
# Embedding Cache
# ---------------------------------------------------------

@lru_cache(maxsize=512)
def get_dense_embedding(query: str):

    return EMBEDDING_MODEL.embed_query(query)


@lru_cache(maxsize=512)
def get_sparse_embedding(query: str):

    sparse = next(
        SPARSE_MODEL.embed([query])
    )

    return SparseVector(
        indices=sparse.indices.tolist(),
        values=sparse.values.tolist(),
    )


# ---------------------------------------------------------
# Company Retriever
# ---------------------------------------------------------

class CompanyRetriever:

    def __init__(
        self,
        collection_name: Optional[str] = None,
    ):

        self.qdrant_client = QDRANT_CLIENT
        self.embedding_model = EMBEDDING_MODEL
        self.sparse_model = SPARSE_MODEL
        self.reranker = RERANKER

        self.collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION_NAME")
        )


    def _build_metadata_filter(
        self,
        company_id: str,
    ) -> Filter:

        return Filter(
            must=[
                FieldCondition(
                    key="CompanyId",
                    match=MatchValue(value=company_id),
                )
            ]
        )


    def _build_rerank_query(
        self,
        anchor_group: Dict[str, Any],
    ) -> str:

        parts = [
            anchor_group.get("objective", ""),
            anchor_group.get("anchor_query", ""),
            " ".join(
                anchor_group.get(
                    "query_variants",
                    [],
                )
            ),
        ]

        return " ".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def _dense_search(
        self,
        query: str,
        metadata_filter: Filter,
        limit: int,
    ) -> List[Dict[str, Any]]:

        dense_vector = get_dense_embedding(query)

        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=dense_vector,
            using="dense",
            query_filter=metadata_filter,
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "chunk_id": point.payload.get("ChunckId") or str(point.id),
                "document_id": point.payload.get("DocumentId"),
                "document_name": point.payload.get("DocumentName"),
                "document_type": point.payload.get("DocumentType"),
                "text": point.payload.get("Text", ""),
                "retrieval_metadata": {
                    "dense_score": float(point.score),
                    "title": point.payload.get("Title"),
                    "related_section": point.payload.get("RelatedSection"),
                    "source": "dense",
                },
            }
            for point in results
        ]


    def _sparse_search(
        self,
        query: str,
        metadata_filter: Filter,
        limit: int,
    ) -> List[Dict[str, Any]]:

        sparse_vector = get_sparse_embedding(query)

        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=sparse_vector,
            using="sparse",
            query_filter=metadata_filter,
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "chunk_id": point.payload.get("ChunckId") or str(point.id),
                "document_id": point.payload.get("DocumentId"),
                "document_name": point.payload.get("DocumentName"),
                "document_type": point.payload.get("DocumentType"),
                "text": point.payload.get("Text", ""),
                "retrieval_metadata": {
                    "sparse_score": float(point.score),
                    "title": point.payload.get("Title"),
                    "related_section": point.payload.get("RelatedSection"),
                    "source": "sparse",
                },
            }
            for point in results
        ]


    def _hybrid_search(
        self,
        query: str,
        metadata_filter: Filter,
        limit: int,
    ) -> List[Dict[str, Any]]:

        dense_results = self._dense_search(
            query=query,
            metadata_filter=metadata_filter,
            limit=limit,
        )

        sparse_results = self._sparse_search(
            query=query,
            metadata_filter=metadata_filter,
            limit=limit,
        )

        return dense_results + sparse_results


    def _deduplicate_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        unique_chunks: Dict[str, Dict[str, Any]] = {}

        for chunk in chunks:

            chunk_id = chunk["chunk_id"]

            if chunk_id not in unique_chunks:
                unique_chunks[chunk_id] = chunk
                continue

            existing = unique_chunks[chunk_id]

            existing_score = max(
                existing["retrieval_metadata"].get(
                    "dense_score",
                    0,
                ),
                existing["retrieval_metadata"].get(
                    "sparse_score",
                    0,
                ),
            )

            current_score = max(
                chunk["retrieval_metadata"].get(
                    "dense_score",
                    0,
                ),
                chunk["retrieval_metadata"].get(
                    "sparse_score",
                    0,
                ),
            )

            if current_score > existing_score:
                unique_chunks[chunk_id] = chunk

        return list(unique_chunks.values())