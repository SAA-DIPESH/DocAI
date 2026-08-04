# 
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

load_dotenv()


def _load_cross_encoder(model_name: str):
    """
    Load the cross-encoder reranker only when CompanyRetriever
    is initialized.
    """
    try:
        from sentence_transformers import CrossEncoder
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Unable to load the Win Theme cross-encoder reranker. "
            "Verify the sentence-transformers/scikit-learn installation "
            "and local Application Control policy."
        ) from exc

    return CrossEncoder(model_name)


class CompanyRetriever:
    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        collection_name: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
        dense_vector_name: Optional[str] = None,
        reranker_model_name: str = (
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
    ) -> None:
        """
        Initialize Qdrant, OpenAI embeddings and the cross-encoder reranker.

        The Qdrant collection uses named vectors. The dense vector name
        defaults to "dense".
        """

        resolved_qdrant_url = (
            qdrant_url
            or os.getenv("QDRANT_URL")
        )

        resolved_collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION_NAME")
        )

        resolved_qdrant_api_key = (
            qdrant_api_key
            or os.getenv("QDRANT_API_KEY")
        )

        resolved_openai_api_key = os.getenv("OPENAI_API_KEY")

        if not resolved_qdrant_url:
            raise ValueError(
                "Qdrant URL is missing. Pass qdrant_url or "
                "set QDRANT_URL in the environment."
            )

        if not resolved_collection_name:
            raise ValueError(
                "Qdrant collection name is missing. Pass "
                "collection_name or set QDRANT_COLLECTION_NAME "
                "in the environment."
            )

        if not resolved_openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured."
            )

        self.collection_name = resolved_collection_name

        self.dense_vector_name = (
            dense_vector_name
            or os.getenv("QDRANT_DENSE_VECTOR_NAME")
            or "dense"
        )

        self.qdrant_client = QdrantClient(
            url=resolved_qdrant_url,
            api_key=resolved_qdrant_api_key,
            timeout=60,
        )

        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=resolved_openai_api_key,
        )

        self.reranker = _load_cross_encoder(
            reranker_model_name
        )

    def retrieve(
        self,
        company_id: str,
        anchor_group: Dict[str, Any],
        top_k: int = 5,
        search_limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search company documents using all anchor queries, remove duplicate
        chunks and rerank the retrieved results.

        Args:
            company_id:
                CompanyId used in the Qdrant payload filter.

            anchor_group:
                Dictionary containing values such as:
                - anchor_id
                - objective
                - anchor_query
                - query_variants

            top_k:
                Number of final reranked chunks to return.

            search_limit:
                Number of Qdrant results retrieved for each search query.
        """

        if not company_id or not company_id.strip():
            raise ValueError(
                "company_id cannot be empty."
            )

        if not isinstance(anchor_group, dict):
            raise ValueError(
                "anchor_group must be a dictionary."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if search_limit <= 0:
            raise ValueError(
                "search_limit must be greater than 0."
            )

        anchor_query = str(
            anchor_group.get("anchor_query") or ""
        ).strip()

        query_variants = (
            anchor_group.get("query_variants")
            or []
        )

        search_queries = self._normalise_search_queries(
            anchor_query=anchor_query,
            query_variants=query_variants,
        )

        if not search_queries:
            return {
                "anchor_id": anchor_group.get("anchor_id"),
                "objective": anchor_group.get("objective"),
                "anchor_query": anchor_query,
                "queries_used": [],
                "evidence": [],
            }

        metadata_filter = self._build_metadata_filter(
            company_id=company_id.strip()
        )

        all_results: List[Dict[str, Any]] = []

        for search_query in search_queries:
            query_results = self._dense_search(
                query=search_query,
                metadata_filter=metadata_filter,
                limit=search_limit,
            )

            all_results.extend(query_results)

        deduplicated_results = self._deduplicate_chunks(
            all_results
        )

        rerank_query = self._build_rerank_query(
            anchor_group
        )

        reranked_results = self._rerank(
            query=rerank_query,
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

    @staticmethod
    def _normalise_search_queries(
        anchor_query: str,
        query_variants: Any,
    ) -> List[str]:
        """
        Clean search queries and remove duplicate query variations.
        """

        if not isinstance(query_variants, list):
            query_variants = []

        queries = [
            anchor_query,
            *query_variants,
        ]

        normalised_queries: List[str] = []
        seen_queries = set()

        for value in queries:
            query = str(value or "").strip()

            if not query:
                continue

            deduplication_key = query.casefold()

            if deduplication_key in seen_queries:
                continue

            seen_queries.add(deduplication_key)
            normalised_queries.append(query)

        return normalised_queries

    @staticmethod
    def _build_metadata_filter(
        company_id: str,
    ) -> Filter:
        """
        Create the Qdrant CompanyId payload filter.
        """

        return Filter(
            must=[
                FieldCondition(
                    key="CompanyId",
                    match=MatchValue(
                        value=company_id
                    ),
                )
            ]
        )

    def _dense_search(
        self,
        query: str,
        metadata_filter: Filter,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Generate an OpenAI embedding and search the named Qdrant
        dense vector.

        The important fix is:

            using=self.dense_vector_name

        Without this property, Qdrant does not know whether it should
        search the "dense" or "sparse" named vector.
        """

        dense_vector = self.embedding_model.embed_query(
            query
        )

        response = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=dense_vector,

            # Required because the collection has named vectors:
            # "dense" and "sparse".
            using=self.dense_vector_name,

            query_filter=metadata_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        results: List[Dict[str, Any]] = []

        for result in response.points:
            payload = result.payload or {}

            # First check the correct ChunkId field.
            # Keep ChunckId support in case older data contains the typo.
            chunk_id = (
                payload.get("ChunkId")
                or payload.get("ChunckId")
                or str(result.id)
            )

            result_item = {
                "chunk_id": str(chunk_id),
                "document_id": payload.get(
                    "DocumentId"
                ),
                "document_name": payload.get(
                    "DocumentName"
                ),
                "document_type": payload.get(
                    "DocumentType"
                ),
                "text": payload.get(
                    "Text",
                    "",
                ),
                "retrieval_metadata": {
                    "dense_score": float(
                        result.score
                    ),
                    "title": payload.get(
                        "Title"
                    ),
                    "related_section": payload.get(
                        "RelatedSection"
                    ),
                    "source_query": query,
                    "vector_name": (
                        self.dense_vector_name
                    ),
                },
            }

            results.append(result_item)

        return results

    @staticmethod
    def _deduplicate_chunks(
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate chunks returned by different query variations.

        When the same chunk is returned more than once, keep the result
        with the highest dense retrieval score.
        """

        unique_chunks: Dict[
            str,
            Dict[str, Any],
        ] = {}

        for chunk in chunks:
            chunk_key = str(
                chunk.get("chunk_id") or ""
            ).strip()

            if not chunk_key:
                continue

            existing_chunk = unique_chunks.get(
                chunk_key
            )

            if existing_chunk is None:
                unique_chunks[chunk_key] = chunk
                continue

            existing_metadata = existing_chunk.get(
                "retrieval_metadata",
                {},
            )

            current_metadata = chunk.get(
                "retrieval_metadata",
                {},
            )

            existing_score = float(
                existing_metadata.get(
                    "dense_score",
                    0.0,
                )
            )

            current_score = float(
                current_metadata.get(
                    "dense_score",
                    0.0,
                )
            )

            if current_score > existing_score:
                unique_chunks[chunk_key] = chunk

        return list(
            unique_chunks.values()
        )

    @staticmethod
    def _build_rerank_query(
        anchor_group: Dict[str, Any],
    ) -> str:
        """
        Combine the objective, anchor query and query variants into one
        query for cross-encoder reranking.
        """

        query_variants = (
            anchor_group.get("query_variants")
            or []
        )

        if not isinstance(query_variants, list):
            query_variants = []

        query_parts = [
            str(
                anchor_group.get("objective")
                or ""
            ),
            str(
                anchor_group.get("anchor_query")
                or ""
            ),
            " ".join(
                str(item)
                for item in query_variants
                if item
            ),
        ]

        return " ".join(
            part.strip()
            for part in query_parts
            if part and part.strip()
        )

    def _rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        Rerank the retrieved Qdrant chunks using the cross-encoder model.
        """

        valid_chunks = [
            chunk
            for chunk in chunks
            if str(
                chunk.get("text") or ""
            ).strip()
        ]

        if not valid_chunks:
            return []

        # If no reranking query is available, retain the dense-score order.
        if not query.strip():
            sorted_chunks = sorted(
                valid_chunks,
                key=lambda item: item.get(
                    "retrieval_metadata",
                    {},
                ).get(
                    "dense_score",
                    0.0,
                ),
                reverse=True,
            )

            return sorted_chunks[:top_k]

        pairs = [
            [
                query,
                chunk["text"],
            ]
            for chunk in valid_chunks
        ]

        scores = self.reranker.predict(
            pairs
        )

        for chunk, score in zip(
            valid_chunks,
            scores,
        ):
            chunk.setdefault(
                "retrieval_metadata",
                {},
            )

            chunk["retrieval_metadata"][
                "rerank_score"
            ] = float(score)

        valid_chunks.sort(
            key=lambda item: item.get(
                "retrieval_metadata",
                {},
            ).get(
                "rerank_score",
                0.0,
            ),
            reverse=True,
        )

        return valid_chunks[:top_k]




# Create a object
company_retriever = CompanyRetriever()
