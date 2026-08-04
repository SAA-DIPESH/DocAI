import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

load_dotenv()


def _load_cross_encoder(model_name: str):
    """Load the reranker model once."""
    try:
        from sentence_transformers import CrossEncoder
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Unable to load the Win Theme cross-encoder reranker. "
            "Verify the sentence-transformers/scikit-learn installation."
        ) from exc

    return CrossEncoder(model_name)


# ---------------------------------------------------------------------
# Singleton instances (loaded once when this module is imported)
# ---------------------------------------------------------------------

QDRANT_CLIENT = QdrantClient(
    url=os.getenv("QDRANT_URL"),
)

EMBEDDING_MODEL = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)

RERANKER = _load_cross_encoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


class CompanyRetriever:
    def __init__(
        self,
        collection_name: Optional[str] = None,
    ):
        self.qdrant_client = QDRANT_CLIENT
        self.embedding_model = EMBEDDING_MODEL
        self.reranker = RERANKER

        self.collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION_NAME")
        )

    def retrieve(
        self,
        company_id: str,
        anchor_group: Dict[str, Any],
        top_k: int = 5,
        search_limit: int = 10,
    ) -> Dict[str, Any]:

        anchor_query = anchor_group.get("anchor_query", "")
        query_variants = anchor_group.get("query_variants", [])

        search_queries = [
            query.strip()
            for query in [anchor_query, *query_variants]
            if query and query.strip()
        ]

        metadata_filter = self._build_metadata_filter(company_id)

        all_results: List[Dict[str, Any]] = []

        for query in search_queries:
            all_results.extend(
                self._dense_search(
                    query=query,
                    metadata_filter=metadata_filter,
                    limit=search_limit,
                )
            )

        deduplicated_results = self._deduplicate_chunks(
            all_results
        )

        reranked_results = self._rerank(
            query=self._build_rerank_query(anchor_group),
            chunks=deduplicated_results,
            top_k=top_k,
        )

        for chunk in reranked_results:
            chunk["evidence_id"] = chunk["chunk_id"]

        return {
            "anchor_id": anchor_group.get("anchor_id"),
            "objective": anchor_group.get("objective"),
            "anchor_query": anchor_query,
            "queries_used": search_queries,
            "evidence": reranked_results,
        }

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

    def _dense_search(
        self,
        query: str,
        metadata_filter: Filter,
        limit: int,
    ) -> List[Dict[str, Any]]:

        dense_vector = self.embedding_model.embed_query(query)

        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=dense_vector,
            query_filter=metadata_filter,
            limit=limit,
            with_payload=True,
        ).points

        return [
            {
                "chunk_id": result.payload.get("ChunckId") or str(result.id),
                "document_id": result.payload.get("DocumentId"),
                "document_name": result.payload.get("DocumentName"),
                "document_type": result.payload.get("DocumentType"),
                "text": result.payload.get("Text", ""),
                "retrieval_metadata": {
                    "dense_score": float(result.score),
                    "title": result.payload.get("Title"),
                    "related_section": result.payload.get(
                        "RelatedSection"
                    ),
                    "source_query": query,
                },
            }
            for result in results
        ]

    def _deduplicate_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        unique_chunks: Dict[str, Dict[str, Any]] = {}

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")

            if not chunk_id:
                continue

            existing = unique_chunks.get(chunk_id)

            if (
                existing is None
                or chunk["retrieval_metadata"]["dense_score"]
                > existing["retrieval_metadata"]["dense_score"]
            ):
                unique_chunks[chunk_id] = chunk

        return list(unique_chunks.values())

    def _build_rerank_query(
        self,
        anchor_group: Dict[str, Any],
    ) -> str:

        return " ".join(
            part.strip()
            for part in [
                anchor_group.get("objective", ""),
                anchor_group.get("anchor_query", ""),
                " ".join(
                    anchor_group.get(
                        "query_variants",
                        [],
                    )
                ),
            ]
            if part and part.strip()
        )

    def _rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:

        valid_chunks = [
            chunk
            for chunk in chunks
            if chunk.get("text")
        ]

        if not valid_chunks:
            return []

        scores = self.reranker.predict(
            [[query, chunk["text"]] for chunk in valid_chunks]
        )

        for chunk, score in zip(valid_chunks, scores):
            chunk["retrieval_metadata"][
                "rerank_score"
            ] = float(score)

        valid_chunks.sort(
            key=lambda chunk: chunk["retrieval_metadata"][
                "rerank_score"
            ],
            reverse=True,
        )

        return valid_chunks[:top_k]


# ---------------------------------------------------------------------
# Singleton retriever
# ---------------------------------------------------------------------

COMPANY_RETRIEVER = CompanyRetriever()