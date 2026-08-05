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
    MatchAny,
    MatchValue,
    SparseVector,
)
import time
import traceback


load_dotenv()

# ==========================================================
# Singleton Models
# ==========================================================

QDRANT_CLIENT = QdrantClient(
    url=os.getenv("QDRANT_URL"),
)

EMBEDDING_MODEL = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)

SPARSE_MODEL = SparseTextEmbedding(
    model_name="Qdrant/bm25",
)


def _load_cross_encoder(model_name: str):
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(model_name)

    except Exception as exc:
        raise RuntimeError(
            f"Unable to load CrossEncoder: {model_name}"
        ) from exc


RERANKER = _load_cross_encoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


# ==========================================================
# Embedding Cache
# ==========================================================

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


# ==========================================================
# Company Retriever
# ==========================================================

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

    # ------------------------------------------------------
    # Metadata Filter
    # ------------------------------------------------------
    def _build_metadata_filter(
        self,
        company_id: str,
        anchor_group: Dict[str, Any],
    ) -> Filter:

        return Filter(
            must=[
                FieldCondition(
                    key="CompanyId",
                    match=MatchValue(value=company_id),
                )
            ]
        )

    # ------------------------------------------------------
    # Query Normalization
    # ------------------------------------------------------

    def _normalize_queries(
        self,
        anchor_group: Dict[str, Any],
    ) -> List[str]:
        """
        Remove duplicate search queries while preserving order.
        """

        queries = [
            anchor_group.get(
                "anchor_query",
                "",
            ),
            *anchor_group.get(
                "query_variants",
                [],
            ),
        ]

        normalized = []
        seen = set()

        for query in queries:

            query = query.strip()

            if not query:
                continue

            key = query.lower()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(query)

        return normalized

    # ------------------------------------------------------
    # Rerank Query
    # ------------------------------------------------------

    def _build_rerank_query(
        self,
        anchor_group: Dict[str, Any],
    ) -> str:
        """
        Build a richer semantic query for CrossEncoder.
        """

        parts = [
            anchor_group.get(
                "objective",
                "",
            ),
            anchor_group.get(
                "anchor_query",
                "",
            ),
            " ".join(
                anchor_group.get(
                    "anchor_tags",
                    [],
                )
            ),
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

    # ------------------------------------------------------
    # Dense Search
    # ------------------------------------------------------

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

        chunks = []

        for rank, point in enumerate(results, start=1):

            chunks.append(
                {
                    "chunk_id": point.payload.get(
                        "ChunkId"
                    )
                    or str(point.id),

                    "document_id": point.payload.get(
                        "DocumentId"
                    ),

                    "document_name": point.payload.get(
                        "DocumentName"
                    ),

                    "document_type": point.payload.get(
                        "DocumentClassification"
                    ),

                    "text": point.payload.get(
                        "Text",
                        "",
                    ),

                    "retrieval_metadata": {
                        "dense_score": float(
                            point.score
                        ),
                        "dense_rank": rank,
                        "source": "dense",
                        "title": point.payload.get(
                            "Title"
                        ),
                        "related_section": point.payload.get(
                            "RelatedSection"
                        ),
                    },
                }
            )

        return chunks

    # ------------------------------------------------------
    # Sparse Search
    # ------------------------------------------------------

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

        chunks = []

        for rank, point in enumerate(results, start=1):

            chunks.append(
                {
                    "chunk_id": point.payload.get(
                        "ChunkId"
                    )
                    or str(point.id),

                    "document_id": point.payload.get(
                        "DocumentId"
                    ),

                    "document_name": point.payload.get(
                        "DocumentName"
                    ),

                    "document_type": point.payload.get(
                        "DocumentClassification"
                    ),

                    "text": point.payload.get(
                        "Text",
                        "",
                    ),

                    "retrieval_metadata": {
                        "sparse_score": float(
                            point.score
                        ),
                        "sparse_rank": rank,
                        "source": "sparse",
                        "title": point.payload.get(
                            "Title"
                        ),
                        "related_section": point.payload.get(
                            "RelatedSection"
                        ),
                    },
                }
            )

        return chunks


    # ------------------------------------------------------
    # Reciprocal Rank Fusion (RRF)
    # ------------------------------------------------------

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Fuse dense and sparse search results using
        Reciprocal Rank Fusion (RRF).

        Score = Σ 1 / (k + rank)
        """

        fused: Dict[str, Dict[str, Any]] = {}

        # Dense ranking
        for rank, chunk in enumerate(dense_results, start=1):

            chunk_id = chunk["chunk_id"]

            if chunk_id not in fused:
                fused[chunk_id] = chunk
                fused[chunk_id]["retrieval_metadata"]["rrf_score"] = 0.0

            fused[chunk_id]["retrieval_metadata"]["rrf_score"] += (
                1.0 / (k + rank)
            )

        # Sparse ranking
        for rank, chunk in enumerate(sparse_results, start=1):

            chunk_id = chunk["chunk_id"]

            if chunk_id not in fused:
                fused[chunk_id] = chunk
                fused[chunk_id]["retrieval_metadata"]["rrf_score"] = 0.0

            fused[chunk_id]["retrieval_metadata"]["rrf_score"] += (
                1.0 / (k + rank)
            )

        fused_results = list(fused.values())

        fused_results.sort(
            key=lambda x: x["retrieval_metadata"]["rrf_score"],
            reverse=True,
        )

        return fused_results

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

        return self._reciprocal_rank_fusion(
            dense_results,
            sparse_results,
        )


    def _deduplicate_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Keep the chunk with the highest RRF score.
        """

        unique_chunks = {}

        for chunk in chunks:

            chunk_id = chunk["chunk_id"]

            score = chunk["retrieval_metadata"].get(
                "rrf_score",
                0,
            )

            if chunk_id not in unique_chunks:

                unique_chunks[chunk_id] = chunk
                continue

            existing_score = unique_chunks[
                chunk_id
            ]["retrieval_metadata"].get(
                "rrf_score",
                0,
            )

            if score > existing_score:

                unique_chunks[chunk_id] = chunk

        return list(unique_chunks.values())


    def _rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:

        valid_chunks = [
            c
            for c in chunks
            if c.get("text")
        ]

        if not valid_chunks:
            return []

        pairs = [
            (query, c["text"])
            for c in valid_chunks
        ]

        scores = self.reranker.predict(
            pairs,
            batch_size=32,
        )

        for chunk, score in zip(valid_chunks, scores):

            chunk["retrieval_metadata"][
                "rerank_score"
            ] = float(score)

        valid_chunks.sort(
            key=lambda x: x["retrieval_metadata"][
                "rerank_score"
            ],
            reverse=True,
        )

        return valid_chunks[:top_k]


    def retrieve(
        self,
        company_id: str,
        anchor_group: Dict[str, Any],
        top_k: int = 5,
        search_limit: int = 10,
    ) -> Dict[str, Any]:

        try:
            overall = time.perf_counter()

            # print("=" * 80)
            # print("START RETRIEVE")
            # print("=" * 80)

            t = time.perf_counter()
            search_queries = self._normalize_queries(anchor_group)
            # print(
            #     f"Normalize Queries: {time.perf_counter()-t:.3f}s"
            # )
            # print(search_queries)

            t = time.perf_counter()
            metadata_filter = self._build_metadata_filter(
                company_id=company_id,
                anchor_group=anchor_group,
            )
            # print(
            #     f"Metadata Filter: {time.perf_counter()-t:.3f}s"
            # )

            all_chunks = []

            for i, query in enumerate(search_queries, start=1):

                # print("-" * 80)
                # print(f"QUERY {i}")
                # print(query)

                qt = time.perf_counter()

                results = self._hybrid_search(
                    query=query,
                    metadata_filter=metadata_filter,
                    limit=search_limit,
                )

                # print(
                #     f"Hybrid Search: {time.perf_counter()-qt:.3f}s"
                # )
                # print(
                #     f"Returned: {len(results)}"
                # )

                all_chunks.extend(results)

            t = time.perf_counter()
            deduplicated = self._deduplicate_chunks(
                all_chunks
            )
            # print(
            #     f"Deduplicate: {time.perf_counter()-t:.3f}s"
            # )
            # print(
            #     f"Chunks: {len(deduplicated)}"
            # )

            t = time.perf_counter()
            reranked = self._rerank(
                query=self._build_rerank_query(anchor_group),
                chunks=deduplicated,
                top_k=top_k,
            )
            # print(
            #     f"Rerank: {time.perf_counter()-t:.3f}s"
            # )

            for chunk in reranked:
                chunk["evidence_id"] = chunk["chunk_id"]

            # print("=" * 80)
            # print(
            #     f"TOTAL TIME: {time.perf_counter()-overall:.3f}s"
            # )
            # print("=" * 80)

            return {
                "anchor_id": anchor_group.get("anchor_id"),
                "objective": anchor_group.get("objective"),
                "anchor_query": anchor_group.get("anchor_query"),
                "queries_used": search_queries,
                "evidence": reranked,
                "retrieval_stats": {
                    "queries": len(search_queries),
                    "retrieved_chunks": len(all_chunks),
                    "deduplicated_chunks": len(deduplicated),
                    "returned_chunks": len(reranked),
                },
            }

        except Exception:
            # print("=" * 80)
            # print("RETRIEVE FAILED")
            # traceback.print_exc()
            # print("=" * 80)
            raise



COMPANY_RETRIEVER = CompanyRetriever()