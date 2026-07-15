"""
Evaluation Criteria Retrieval Agent - Qdrant retriever (Profile-driven, ChunkIndex + PageID)
=======================================================

Purpose
-------
Use an evaluation-criteria retrieval profile (the JSON configuration you created)
to retrieve grounded tender evidence from Qdrant before sending it to an LLM.

The script is intentionally written against the payload currently stored in your
Qdrant collection, for example:
    CompanyId, TenderId, DocumentId, ChunkId, DocumentName, Text,
    DocumentType, CreatedAt, RelatedSection

Important ingestion requirement
-------------------------------
For exact previous/next chunk retrieval, every point MUST also contain:
    ChunkIndex: integer, monotonic within one DocumentId (0, 1, 2, ...)
    PageID: stable identifier shared by every chunk created from the same page
            (for example: '<DocumentId>:page:11' or a numeric page ID)

    Optional display field:
    PageNumber: integer

Without ChunkIndex, Qdrant cannot know which point was immediately before or
after a match. In that situation this script falls back to collecting the whole
matched document (up to MAX_DOCUMENT_FALLBACK_CHUNKS) so that important
neighbouring evaluation evidence is not silently lost.

Install
-------
    pip install "qdrant-client>=1.17" sentence-transformers

Optional, only if your collection has a compatible sparse vector:
    pip install fastembed

Environment variables
---------------------
    QDRANT_URL=http://localhost:6333
    QDRANT_API_KEY=...                         # optional for local Qdrant
    QDRANT_COLLECTION=tender_chunks
    COMPANY_ID=6a202607915f3a8b0831fec6
    TENDER_ID=6a33e2ae3d4dce0e34ae271e
    RETRIEVAL_PROFILE_PATH=./evaluation_retrieval_profile.json

    # This must be EXACTLY the dense model used when the Qdrant collection
    # was ingested. Do not choose a model only for querying.
    DENSE_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

    # Enable only where the collection has a sparse vector created using the
    # same sparse model / vocabulary strategy.
    ENABLE_SPARSE=false
    SPARSE_MODEL_NAME=Qdrant/bm25

Output
------
Writes evaluation_evidence.json. This file is the evidence pack that should be
provided to the Evaluation Criteria LLM extraction prompt.
"""

from __future__ import annotations

import hashlib
import argparse
import json
import logging
import os
import re
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from qdrant_client import QdrantClient, models


def _load_environment() -> None:
    """Load .env without requiring python-dotenv; existing process values win."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except ImportError:
        pass

    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_environment()


class ConfigurationError(Exception):
    """Invalid or missing retriever configuration."""


class EmbeddingError(Exception):
    """The embedding provider could not produce an embedding."""


class RetrieverError(Exception):
    """A retrieval operation failed."""


class VectorConfigurationError(RetrieverError):
    """The requested Qdrant vector configuration is unavailable."""


class CollectionValidationError(RetrieverError):
    """The Qdrant collection is incompatible with this retriever."""


COMMON_ENV_NAMES = {
    "QDRANT_URL",
    "MONGO_URI",
    "CONFIG_COLLECTION_NAME",
    "MONGO_DB_NAME",
    "EMBEDDING_MODEL",
    "ENCRYPTION_KEY",
    "SECRET_DB",
    "SECRET_COLLECTION",
    "LLM_PROVIDER",
    "OPENAI_MODEL",
    "LOG_URL",
    "OBJECT_ID",
}


def _env_value(name: str, default: Any = None) -> Any:
    key = name if name in COMMON_ENV_NAMES else f"EC_{name}"
    return os.environ.get(key, default)


def _env_bool(name: str, default: bool) -> bool:
    value = _env_value(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_value(name, default))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_value(name, default))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be numeric.") from exc


# -----------------------------------------------------------------------------
# 1. Settings: change these only if your payload field names change.
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PayloadFields:
    """Maps logical fields to the ACTUAL keys currently in your Qdrant payload."""

    company_id: str = "CompanyId"
    tender_id: str = "TenderId"
    document_id: str = "DocumentId"
    chunk_id: str = "ChunkId"
    document_name: str = "DocumentName"
    text: str = "Text"
    document_type: str = "DocumentType"
    created_at: str = "CreatedAt"
    related_section: str = "RelatedSection"

    # Required for reliable ordered and page-level context retrieval.
    # ChunkIndex must be sequential within each DocumentId.
    # PageID must be identical for all chunks created from the same PDF page.
    chunk_index: str = "ChunkIndex"
    page_id: str = "PageID"

    # Optional human-readable page number. It is never used to determine context.
    page_number: str = "PageNumber"
    section_heading: str = "SectionHeading"
    parent_section_id: str = "ParentSectionId"
    table_id: str = "TableId"
    table_caption: str = "TableCaption"
    table_json: str = "TableJson"
    is_active: str = "IsActive"
    parse_status: str = "ParseStatus"
    document_version: str = "DocumentVersion"
    is_latest_document_version: str = "IsLatestDocumentVersion"


FIELDS = PayloadFields()


def configure_payload_fields(profile: dict[str, Any]) -> PayloadFields:
    """
    Read the Qdrant payload-key mapping from the retrieval profile.

    This lets the same retriever work with PascalCase payloads (for example
    CompanyId and ChunkIndex) or a future snake_case schema without editing
    the Python source. Unknown keys are ignored deliberately.
    """
    raw_mapping = (
        profile.get("qdrant_payload_schema", {})
        .get("field_mapping", {})
    )
    allowed = set(PayloadFields.__dataclass_fields__.keys())
    clean_mapping = {
        key: str(value)
        for key, value in raw_mapping.items()
        if key in allowed and value is not None and str(value).strip()
    }
    return PayloadFields(**clean_mapping)


# A safety cap for legacy payloads that do not yet have ChunkIndex.
MAX_DOCUMENT_FALLBACK_CHUNKS = 250
# A full page can occasionally be split into many chunks, especially with OCR.
MAX_SAME_PAGE_CHUNKS = 80
# Context collection can grow quickly; this prevents accidental huge LLM inputs.
MAX_CONTEXT_CHUNKS_PER_SEED = 80
# Limit worker count so Qdrant is not flooded with simultaneous anchor searches.
MAX_QUERY_WORKERS = 8

REQUIRED_PAYLOAD_FIELDS = (
    "CompanyId",
    "TenderId",
    "DocumentId",
    "ChunkId",
    "DocumentName",
    "DocumentType",
    "ChunkIndex",
    "PageNumber",
    "RelatedSection",
    "Text",
    "CreatedBy",
    "CreatedAt",
    "EmbeddingModel",
)

REQUIRED_PAYLOAD_INDEXES = {
    "CompanyId": models.PayloadSchemaType.KEYWORD,
    "TenderId": models.PayloadSchemaType.KEYWORD,
    "DocumentId": models.PayloadSchemaType.KEYWORD,
    "ChunkId": models.PayloadSchemaType.KEYWORD,
    "ChunkIndex": models.PayloadSchemaType.INTEGER,
    "PageNumber": models.PayloadSchemaType.INTEGER,
    "RelatedSection": models.PayloadSchemaType.KEYWORD,
}


# -----------------------------------------------------------------------------
# 2. Lightweight data structures.
# -----------------------------------------------------------------------------

@dataclass
class CandidateChunk:
    """A Qdrant point plus retrieval provenance accumulated across queries."""

    point_id: str
    payload: dict[str, Any]
    raw_max_score: float = 0.0
    rank_score: float = 0.0
    final_score: float = 0.0
    matched_anchors: set[str] = field(default_factory=set)
    matched_queries: set[str] = field(default_factory=set)
    is_context: bool = False
    context_reasons: set[str] = field(default_factory=set)

    def identity(self) -> str:
        """Stable logical identity used for exact duplicate removal."""
        document_id = str(self.payload.get(FIELDS.document_id, ""))
        chunk_id = str(self.payload.get(FIELDS.chunk_id, ""))
        # A point ID is a safe fallback if ChunkId was not stored in payload.
        return f"{document_id}::{chunk_id or self.point_id}"

    def text(self) -> str:
        return str(self.payload.get(FIELDS.text, "") or "")


# -----------------------------------------------------------------------------
# 3. Embedding providers.
# -----------------------------------------------------------------------------


class OpenAIEmbeddingProvider:
    """Official OpenAI SDK embedding provider with an optional in-memory cache."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 enable_cache: Optional[bool] = None) -> None:
        if not api_key:
            from app.infrastructure.secrets import resolve_openai_api_key

            api_key = resolve_openai_api_key()
        if not api_key:
            raise ConfigurationError("Encrypted OpenAI API key could not be resolved by infrastructure secrets.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ConfigurationError("Install the official OpenAI SDK: pip install openai") from exc
        self.model = model or _env_value("EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = OpenAI(api_key=api_key)
        self.enable_cache = _env_bool("ENABLE_EMBEDDING_CACHE", True) if enable_cache is None else enable_cache
        self._cache: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def embed(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if self.enable_cache:
            with self._lock:
                cached = self._cache.get(key)
            if cached is not None:
                return list(cached)
        try:
            response = self.client.embeddings.create(model=self.model, input=text)
            vector = [float(value) for value in response.data[0].embedding]
        except Exception as exc:
            raise EmbeddingError(f"OpenAI embedding failed using {self.model}: {exc}") from exc
        if not vector:
            raise EmbeddingError("OpenAI returned an empty embedding.")
        if self.enable_cache:
            with self._lock:
                self._cache[key] = vector
        return list(vector)


def build_local_dense_embedder(model_name: str = "text-embedding-3-small") -> Callable[[str], list[float]]:
    """Backward-compatible factory; dense embeddings now come only from OpenAI."""
    return OpenAIEmbeddingProvider(model=_env_value("EMBEDDING_MODEL", "text-embedding-3-small")).embed


def build_fastembed_sparse_embedder(
    model_name: str,
) -> Callable[[str], models.SparseVector]:
    """
    Optional sparse/BM25-style query embedder.

    Enable this only if the sparse vectors already in Qdrant were created using
    the same sparse model and compatible token-to-index mapping.
    """
    try:
        from fastembed import SparseTextEmbedding
    except ImportError as exc:
        raise ConfigurationError("Install fastembed: pip install fastembed") from exc

    model = SparseTextEmbedding(model_name=model_name)

    def embed(text: str) -> models.SparseVector:
        vector = next(iter(model.embed([text])))
        return models.SparseVector(
            indices=[int(index) for index in vector.indices],
            values=[float(value) for value in vector.values],
        )

    return embed


# -----------------------------------------------------------------------------
# 4. Qdrant filters and search helpers.
# -----------------------------------------------------------------------------


def match_value(key: str, value: Any) -> models.FieldCondition:
    """Create a Qdrant exact payload-match condition."""
    return models.FieldCondition(key=key, match=models.MatchValue(value=value))


def build_base_filter(company_id: str, tender_id: str) -> models.Filter:
    """
    The hard tenant boundary for every query.

    Your real payload uses CompanyId rather than tenant_id. It is deliberately
    applied to every semantic search and every context-expansion scroll.
    """
    return models.Filter(
        must=[
            match_value(FIELDS.company_id, company_id),
            match_value(FIELDS.tender_id, tender_id),
        ]
    )


def merge_filters(*filters: models.Filter) -> models.Filter:
    """Combine several Qdrant filters by joining their must/must_not clauses."""
    must: list[Any] = []
    must_not: list[Any] = []
    should: list[Any] = []
    for item in filters:
        if item.must:
            must.extend(item.must)
        if item.must_not:
            must_not.extend(item.must_not)
        if item.should:
            should.extend(item.should)
    return models.Filter(must=must or None, must_not=must_not or None, should=should or None)


def qdrant_points(response: Any) -> list[Any]:
    """Supports the current qdrant-client QueryResponse shape."""
    return list(getattr(response, "points", response))


def safe_payload(point: Any) -> dict[str, Any]:
    """Qdrant payload can be None; normalise it to a dictionary."""
    return dict(getattr(point, "payload", None) or {})


def normalise_text(text: str) -> str:
    """
    Normalise text for duplicate comparison without removing meaningful numbers
    or symbols such as %, £, question identifiers, or score values.
    """
    text = text.lower()
    text = text.replace("\u00a0", " ")
    # OCR can introduce irregular whitespace and repeated page labels.
    text = re.sub(r"\bpage\s+\d+(?:\s+of\s+\d+)?\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()


def is_near_duplicate(left: CandidateChunk, right: CandidateChunk, threshold: float) -> bool:
    """
    Conservative duplicate check.

    Never deduplicate across different documents: a clarification or addendum
    may repeat an earlier value but must remain available for conflict detection.
    """
    if left.payload.get(FIELDS.document_id) != right.payload.get(FIELDS.document_id):
        return False

    left_text = normalise_text(left.text())
    right_text = normalise_text(right.text())
    if not left_text or not right_text:
        return False
    if left_text == right_text:
        return True

    # Avoid expensive SequenceMatcher work where lengths are clearly unrelated.
    length_ratio = min(len(left_text), len(right_text)) / max(len(left_text), len(right_text))
    if length_ratio < 0.80:
        return False

    return SequenceMatcher(None, left_text, right_text).ratio() >= threshold


def page_sort_value(payload: dict[str, Any]) -> tuple[int, str]:
    """
    Return a stable page sort key.

    PageID is the authoritative page identity. PageNumber is optional and only
    improves human-readable ordering. Context retrieval never depends on parsing
    page labels from text.
    """
    page_number = payload.get(FIELDS.page_number)
    try:
        return int(page_number), str(payload.get(FIELDS.page_id, ""))
    except (TypeError, ValueError):
        page_id = str(payload.get(FIELDS.page_id, "") or "")
        try:
            return int(page_id), page_id
        except ValueError:
            return 10**12, page_id


# -----------------------------------------------------------------------------
# 5. Retriever.
# -----------------------------------------------------------------------------

class EvaluationCriteriaRetriever:
    """
    Executes all anchor groups from the JSON profile, deduplicates candidates,
    applies profile-inspired boosts, and expands surrounding evidence.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str,
        profile: dict[str, Any],
        dense_embedder: Callable[[str], list[float]],
        sparse_embedder: Optional[Callable[[str], models.SparseVector]] = None,
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.profile = profile
        self.dense_embedder = dense_embedder
        self.sparse_embedder = sparse_embedder

        strategy = profile.get("retrieval_strategy", {})
        self.dense_vector_name = strategy.get("dense_vector_name", "content_dense")
        self.sparse_vector_name = strategy.get("sparse_vector_name", "content_sparse")
        self.candidate_limit = int(strategy.get("candidate_limit_per_query_variant", 15))
        self.max_per_anchor = int(strategy.get("maximum_candidates_per_anchor", 30))
        self.max_candidates = int(strategy.get("maximum_total_candidates_before_deduplication", 180))
        self.max_evidence_clusters = int(strategy.get("maximum_evidence_clusters_for_llm", 35))
        self.near_duplicate_threshold = float(
            strategy.get("deduplication", {}).get("near_duplicate_text_similarity_threshold", 0.94)
        )
        self.context_config = profile.get("context_expansion", {})
        self.context_config["enabled"] = _env_bool("ENABLE_CONTEXT_EXPANSION", self.context_config.get("enabled", True))
        self.context_config["include_same_page_chunks"] = _env_bool("ENABLE_PAGE_CONTEXT", self.context_config.get("include_same_page_chunks", True))
        self.context_config["include_same_section"] = _env_bool("ENABLE_SECTION_CONTEXT", self.context_config.get("include_same_section", True))
        self.context_config["include_full_table_when_match_is_table_row"] = _env_bool("ENABLE_TABLE_CONTEXT", self.context_config.get("include_full_table_when_match_is_table_row", True))
        self.reranking_config = strategy.get("reranking", {})
        self.vector_mode = _env_value("QDRANT_VECTOR_MODE", "auto").lower()
        requested_mode = _env_value("QDRANT_RETRIEVAL_MODE", "AUTO").strip().lower()
        self.retrieval_mode = {"dense_only": "dense", "sparse_only": "sparse"}.get(
            requested_mode, requested_mode
        )
        self.dense_vector_name = _env_value("QDRANT_DENSE_VECTOR_NAME", self.dense_vector_name)
        self.sparse_vector_name = _env_value("QDRANT_SPARSE_VECTOR_NAME", self.sparse_vector_name)
        self.candidate_limit = _env_int("QDRANT_TOP_K", self.candidate_limit)
        self.max_per_anchor = _env_int("QDRANT_MAX_PER_ANCHOR", self.max_per_anchor)
        self.max_candidates = _env_int("QDRANT_MAX_TOTAL_CANDIDATES", self.max_candidates)
        self.near_duplicate_threshold = _env_float("NEAR_DUPLICATE_THRESHOLD", self.near_duplicate_threshold)
        self.enable_deduplication = _env_bool("ENABLE_DEDUPLICATION", True)
        self.enable_parallel = _env_bool("ENABLE_PARALLEL_SEARCH", True)
        self.max_query_workers = _env_int("MAX_QUERY_WORKERS", MAX_QUERY_WORKERS)
        self.enable_query_cache = _env_bool("ENABLE_QUERY_CACHE", False)
        self._query_cache: dict[str, list[Any]] = {}
        self._cache_lock = threading.Lock()
        self._validated = False
        self._validation_lock = threading.Lock()
        self._dense_using: Optional[str] = self.dense_vector_name
        self._dense_size: Optional[int] = None
        self._sparse_available = False
        self.startup_validation: dict[str, Any] = {}
        if _env_bool("VALIDATE_COLLECTION_ON_STARTUP", True):
            self._validate_collection()

    def _ensure_payload_indexes(self, collection_info: Any) -> list[str]:
        existing = set((collection_info.payload_schema or {}).keys())
        unavailable: list[str] = []
        for field_name, field_schema in REQUIRED_PAYLOAD_INDEXES.items():
            if field_name in existing:
                continue
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                    wait=True,
                )
                existing.add(field_name)
            except Exception as exc:
                unavailable.append(field_name)
                logging.warning("Could not create payload index %s: %s", field_name, exc)
        return unavailable

    def _inspect_payload_fields(self) -> tuple[list[str], list[str]]:
        counts = {field_name: 0 for field_name in REQUIRED_PAYLOAD_FIELDS}
        inspected = 0
        offset: Any = None
        while inspected < 1000:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=min(100, 1000 - inspected),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = safe_payload(point)
                for field_name in counts:
                    if field_name in payload and payload[field_name] is not None:
                        counts[field_name] += 1
            inspected += len(points)
            if offset is None or not points:
                break
        missing = [field_name for field_name, count in counts.items() if count == 0]
        incomplete = [
            field_name for field_name, count in counts.items()
            if inspected and 0 < count < inspected
        ]
        return missing, incomplete

    def _log_startup_validation(self) -> None:
        report = self.startup_validation
        logging.info("=" * 56)
        logging.info("Startup Validation")
        logging.info("✓ Collection: %s", self.collection_name)
        logging.info("✓ Payload: %s", "complete" if not report["missing_fields"] and not report["incomplete_fields"] else "validated with warnings")
        logging.info("✓ Payload Indexes: %s", "available" if not report["missing_indexes"] else "creation warning")
        logging.info("✓ Dense Vector: %s", report["dense_vector"])
        logging.info("✓ Sparse Vector: %s", report["sparse_vector"])
        logging.info("✓ Embedding Dimensions: %s", report["dimension"])
        logging.info("=" * 56)

    def _validate_collection(self) -> None:
        """Inspect vector schema, select named/default mode, and validate dimensions."""
        with self._validation_lock:
            if self._validated:
                return
            try:
                info = self.client.get_collection(self.collection_name)
                config = info.config.params
                vectors = config.vectors
                sparse_vectors = getattr(config, "sparse_vectors", None) or {}
            except Exception as exc:
                raise CollectionValidationError(
                    f"Unable to inspect Qdrant collection {self.collection_name!r}: {exc}"
                ) from exc
            is_named = isinstance(vectors, dict)
            if self.vector_mode not in {"auto", "default", "named"}:
                raise ConfigurationError("QDRANT_VECTOR_MODE must be auto, default, or named.")
            if self.vector_mode == "default" and is_named:
                raise VectorConfigurationError("QDRANT_VECTOR_MODE=default but collection uses named vectors.")
            if self.vector_mode == "named" and not is_named:
                raise VectorConfigurationError("QDRANT_VECTOR_MODE=named but collection uses the default vector.")
            if is_named:
                if self.dense_vector_name not in vectors:
                    raise VectorConfigurationError(
                        f"Dense vector {self.dense_vector_name!r} not found; available: {sorted(vectors)}"
                    )
                dense_config = vectors[self.dense_vector_name]
                self._dense_using = self.dense_vector_name
            else:
                dense_config = vectors
                self._dense_using = None
            self._dense_size = int(dense_config.size)
            self._sparse_available = self.sparse_vector_name in sparse_vectors
            missing_indexes = self._ensure_payload_indexes(info)
            missing_fields, incomplete_fields = self._inspect_payload_fields()
            if self.retrieval_mode not in {"auto", "dense", "sparse", "hybrid"}:
                raise ConfigurationError("QDRANT_RETRIEVAL_MODE must be auto, dense, sparse, or hybrid.")
            sparse_enabled = _env_bool("QDRANT_ENABLE_SPARSE", self.sparse_embedder is not None)
            hybrid_enabled = _env_bool("QDRANT_ENABLE_HYBRID", True)
            if not self._sparse_available or not sparse_enabled:
                self.sparse_embedder = None
            if self.retrieval_mode == "dense":
                self.sparse_embedder = None
            elif self.retrieval_mode == "auto":
                self.retrieval_mode = (
                    "hybrid"
                    if hybrid_enabled and self._sparse_available and self.sparse_embedder is not None
                    else "dense"
                )
            elif self.retrieval_mode == "sparse" and (not self._sparse_available or self.sparse_embedder is None):
                logging.warning("Sparse mode unavailable; falling back to dense retrieval.")
                self.retrieval_mode = "dense"
            elif self.retrieval_mode == "hybrid" and (not hybrid_enabled or self.sparse_embedder is None):
                logging.warning("Hybrid mode unavailable; falling back to dense retrieval.")
                self.retrieval_mode = "dense"
            probe = self.dense_embedder("Qdrant vector dimension validation")
            if _env_bool("VALIDATE_VECTOR_DIMENSIONS", True) and len(probe) != self._dense_size:
                raise CollectionValidationError(
                    f"Embedding dimension mismatch: provider returned {len(probe)}, "
                    f"collection expects {self._dense_size}."
                )
            self.startup_validation = {
                "collection": self.collection_name,
                "vector_mode": "named" if is_named else "default",
                "dense_vector": self._dense_using or "default",
                "sparse_vector": self.sparse_vector_name if self._sparse_available else "not available",
                "dimension": self._dense_size,
                "missing_indexes": missing_indexes,
                "missing_fields": missing_fields,
                "incomplete_fields": incomplete_fields,
            }
            self._validated = True
            logging.info("Collection validated | collection=%s | vector=%s | dimension=%s | mode=%s | sparse=%s",
                         self.collection_name, self._dense_using or "default", self._dense_size,
                         "named" if is_named else "default", bool(self.sparse_embedder))
            if missing_fields:
                logging.warning("Payload fields absent from collection: %s", ", ".join(missing_fields))
            if incomplete_fields:
                logging.warning("Payload fields incomplete across collection: %s", ", ".join(incomplete_fields))
            self._log_startup_validation()

    # ----- Semantic retrieval -------------------------------------------------

    def _query_one_variant(
        self,
        query_text: str,
        query_filter: models.Filter,
    ) -> list[Any]:
        """Run dense-only or dense+sparse RRF retrieval for one natural-language query."""
        if not self._validated:
            self._validate_collection()
        cache_key = f"{query_text}|{query_filter!r}|{self.retrieval_mode}"
        if self.enable_query_cache:
            with self._cache_lock:
                cached = self._query_cache.get(cache_key)
            if cached is not None:
                return list(cached)
        if self.retrieval_mode == "sparse" and self.sparse_embedder is not None:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=self.sparse_embedder(query_text),
                using=self.sparse_vector_name,
                query_filter=query_filter,
                limit=self.candidate_limit,
                with_payload=True,
                with_vectors=False,
            )
            points = qdrant_points(response)
            if self.enable_query_cache:
                with self._cache_lock:
                    self._query_cache[cache_key] = points
            return points

        dense_vector = self.dense_embedder(query_text)

        if self.sparse_embedder is None:
            kwargs: dict[str, Any] = dict(
                collection_name=self.collection_name,
                query=dense_vector,
                query_filter=query_filter,
                limit=self.candidate_limit,
                with_payload=True,
                with_vectors=False,
            )
            if self._dense_using is not None:
                kwargs["using"] = self._dense_using
            response = self.client.query_points(**kwargs)
            points = qdrant_points(response)
            if self.enable_query_cache:
                with self._cache_lock:
                    self._query_cache[cache_key] = points
            return points

        # Hybrid retrieval: dense semantic recall + sparse exact-term recall.
        sparse_vector = self.sparse_embedder(query_text)
        dense_prefetch_kwargs: dict[str, Any] = dict(
            query=dense_vector,
            filter=query_filter,
            limit=self.candidate_limit,
        )
        if self._dense_using is not None:
            dense_prefetch_kwargs["using"] = self._dense_using
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(**dense_prefetch_kwargs),
                models.Prefetch(
                    query=sparse_vector,
                    using=self.sparse_vector_name,
                    filter=query_filter,
                    limit=self.candidate_limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=self.candidate_limit,
            with_payload=True,
            with_vectors=False,
        )
        points = qdrant_points(response)
        if self.enable_query_cache:
            with self._cache_lock:
                self._query_cache[cache_key] = points
        return points

    def _anchor_queries(self, anchor: dict[str, Any]) -> list[str]:
        """Build unique queries from anchor_query, variants, and exact keywords."""
        queries: list[str] = []
        for query in [anchor.get("anchor_query", ""), *anchor.get("query_variants", [])]:
            cleaned = str(query).strip()
            if cleaned and cleaned not in queries:
                queries.append(cleaned)

        # Keyword-only retrieval provides an extra exact procurement-language
        # route. It is useful for wording such as pass/fail, MEAT, or 0-5.
        keywords = [str(x).strip() for x in anchor.get("lexical_keywords", []) if str(x).strip()]
        if keywords:
            lexical_query = " ; ".join(keywords)
            if lexical_query not in queries:
                queries.append(lexical_query)
        return queries

    def _search_anchor(
        self,
        anchor: dict[str, Any],
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """Search every query variant for one anchor and merge its own hits."""
        merged: dict[str, CandidateChunk] = {}
        queries = self._anchor_queries(anchor)
        anchor_id = str(anchor["anchor_id"])

        for query_text in queries:
            try:
                points = self._query_one_variant(query_text, base_filter)
            except Exception as exc:
                logging.error("Qdrant query failed | anchor=%s | query=%s | error=%s", anchor_id, query_text, exc)
                raise RetrieverError(f"Qdrant query failed for anchor {anchor_id}: {exc}") from exc

            # Qdrant scores from different variants are not directly comparable.
            # Reciprocal rank contribution is stable across all query variants.
            for rank, point in enumerate(points, start=1):
                payload = safe_payload(point)
                candidate = CandidateChunk(point_id=str(point.id), payload=payload)
                key = candidate.identity()
                rank_contribution = 1.0 / (60.0 + rank)

                if key not in merged:
                    candidate.raw_max_score = float(getattr(point, "score", 0.0) or 0.0)
                    candidate.rank_score = rank_contribution
                    candidate.matched_anchors.add(anchor_id)
                    candidate.matched_queries.add(query_text)
                    merged[key] = candidate
                else:
                    existing = merged[key]
                    existing.raw_max_score = max(
                        existing.raw_max_score,
                        float(getattr(point, "score", 0.0) or 0.0),
                    )
                    existing.rank_score += rank_contribution
                    existing.matched_anchors.add(anchor_id)
                    existing.matched_queries.add(query_text)

        # Apply boosts before retaining a bounded number of candidates per anchor.
        ranked = list(merged.values())
        for item in ranked:
            item.final_score = self._score_with_payload_boosts(item)
        ranked.sort(key=lambda item: item.final_score, reverse=True)
        retained = ranked[: self.max_per_anchor]
        logging.info("Anchor: %s | returned=%s chunks", anchor.get("display_name", anchor_id), len(retained))
        return retained

    # ----- Reranking and deduplication ---------------------------------------

    def _score_with_payload_boosts(self, candidate: CandidateChunk) -> float:
        """
        Apply the intent of the profile's reranking rules without assuming that
        snake-case fields exist in your current Qdrant payload.
        """
        payload = candidate.payload
        multiplier = 1.0

        document_type = str(payload.get(FIELDS.document_type, "") or "").lower()
        related_section = str(payload.get(FIELDS.related_section, "") or "").lower()
        chunk_type = str(payload.get("ChunkType", "") or "").lower()
        table_id = payload.get(FIELDS.table_id)

        preferred_types = {
            str(value).lower() for value in self.profile.get("preferred_document_types", [])
        }
        if document_type in preferred_types:
            multiplier += 0.15

        # Your current data stores RelatedSection rather than SectionHeading.
        important_heading_terms = {
            "evaluation", "award", "scoring", "weighting", "quality", "price", "commercial"
        }
        if any(term in related_section for term in important_heading_terms):
            multiplier += 0.20

        if chunk_type == "table" or table_id:
            multiplier += 0.25
        elif chunk_type == "table_row":
            multiplier += 0.20

        # Repetition across different query variants is a meaningful relevance signal.
        multiplier += min(0.20, 0.025 * max(0, len(candidate.matched_queries) - 1))
        return candidate.rank_score * multiplier

    def _deduplicate(self, candidates: Iterable[CandidateChunk]) -> list[CandidateChunk]:
        """
        Two-stage deduplication:
        1) exact logical identity: DocumentId + ChunkId
        2) near-identical text within the SAME document only

        We intentionally keep matching text from different documents because a
        clarification/addendum may supersede an earlier tender document.
        """
        exact: dict[str, CandidateChunk] = {}
        for item in candidates:
            key = item.identity()
            if key not in exact or item.final_score > exact[key].final_score:
                exact[key] = item

        candidates = list(candidates)
        if not self.enable_deduplication:
            return candidates
        result: list[CandidateChunk] = []
        hashes_by_document: dict[str, set[str]] = defaultdict(set)

        for candidate in sorted(exact.values(), key=lambda x: x.final_score, reverse=True):
            document_id = str(candidate.payload.get(FIELDS.document_id, ""))
            candidate_hash = text_hash(candidate.text())
            if candidate_hash in hashes_by_document[document_id]:
                continue

            duplicate = any(
                is_near_duplicate(candidate, existing, self.near_duplicate_threshold)
                for existing in result
                if existing.payload.get(FIELDS.document_id) == candidate.payload.get(FIELDS.document_id)
            )
            if duplicate:
                continue

            hashes_by_document[document_id].add(candidate_hash)
            result.append(candidate)

        return result

    # ----- Context expansion --------------------------------------------------

    def _scroll_all(
        self,
        query_filter: models.Filter,
        max_points: int,
    ) -> list[Any]:
        """Scroll all matching points up to a safety cap, handling pagination."""
        points: list[Any] = []
        offset: Any = None

        while len(points) < max_points:
            batch_limit = min(100, max_points - len(points))
            batch, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=batch_limit,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points.extend(batch)
            if offset is None or not batch:
                break
        return points

    def _fetch_exact_neighbours(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
        before: int,
        after: int,
    ) -> tuple[list[CandidateChunk], bool]:
        """
        Fetch ChunkIndex ± before/after in the same document.

        Returns (chunks, sequence_available). No approximation is made if
        ChunkIndex is absent: exact neighbours must be genuinely ordered.
        """
        payload = seed.payload
        raw_index = payload.get(FIELDS.chunk_index)
        if raw_index is None:
            return [], False

        try:
            chunk_index = int(raw_index)
        except (TypeError, ValueError):
            return [], False

        document_id = payload.get(FIELDS.document_id)
        if not document_id:
            return [], False

        context_filter = merge_filters(
            base_filter,
            models.Filter(
                must=[
                    match_value(FIELDS.document_id, document_id),
                    models.FieldCondition(
                        key=FIELDS.chunk_index,
                        range=models.Range(gte=chunk_index - before, lte=chunk_index + after),
                    ),
                ]
            ),
        )
        points = self._scroll_all(context_filter, before + after + 1)
        chunks = [CandidateChunk(point_id=str(point.id), payload=safe_payload(point)) for point in points]
        for item in chunks:
            item.is_context = True
            item.context_reasons.add("previous_or_next_chunk")
        return chunks, True

    def _fetch_same_page(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """
        Fetch all chunks from the seed's PageID.

        PageID must be the same for every chunk created from a single document
        page. This retrieves table headers/captions and paragraphs from the same
        page without trying to parse a page number from OCR text.
        """
        payload = seed.payload
        page_id = payload.get(FIELDS.page_id)
        document_id = payload.get(FIELDS.document_id)
        if page_id is None or not document_id:
            return []

        query_filter = merge_filters(
            base_filter,
            models.Filter(
                must=[
                    match_value(FIELDS.document_id, document_id),
                    match_value(FIELDS.page_id, page_id),
                ]
            ),
        )
        points = self._scroll_all(query_filter, MAX_SAME_PAGE_CHUNKS)
        chunks = [CandidateChunk(point_id=str(point.id), payload=safe_payload(point)) for point in points]
        for item in chunks:
            item.is_context = True
            item.context_reasons.add("same_page_id")
        return chunks

    def _fetch_same_section(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """Fetch related chunks sharing the same structured section heading."""
        payload = seed.payload
        document_id = payload.get(FIELDS.document_id)
        # Current data has RelatedSection, so use it as a fallback structured section key.
        section_value = payload.get(FIELDS.section_heading) or payload.get(FIELDS.related_section)
        if not document_id or not section_value:
            return []

        query_filter = merge_filters(
            base_filter,
            models.Filter(
                must=[
                    match_value(FIELDS.document_id, document_id),
                    match_value(
                        FIELDS.section_heading
                        if payload.get(FIELDS.section_heading)
                        else FIELDS.related_section,
                        section_value,
                    ),
                ]
            ),
        )
        points = self._scroll_all(query_filter, MAX_CONTEXT_CHUNKS_PER_SEED)
        chunks = [CandidateChunk(point_id=str(point.id), payload=safe_payload(point)) for point in points]
        for item in chunks:
            item.is_context = True
            item.context_reasons.add("same_section")
        return chunks

    def _fetch_full_table(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """Fetch all table rows/full-table chunks where TableId is present."""
        table_id = seed.payload.get(FIELDS.table_id)
        document_id = seed.payload.get(FIELDS.document_id)
        if not table_id or not document_id:
            return []

        query_filter = merge_filters(
            base_filter,
            models.Filter(
                must=[
                    match_value(FIELDS.document_id, document_id),
                    match_value(FIELDS.table_id, table_id),
                ]
            ),
        )
        points = self._scroll_all(query_filter, MAX_CONTEXT_CHUNKS_PER_SEED)
        chunks = [CandidateChunk(point_id=str(point.id), payload=safe_payload(point)) for point in points]
        for item in chunks:
            item.is_context = True
            item.context_reasons.add("full_table")
        return chunks

    def _fetch_adjacent_pages_when_continued(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """
        Retrieve the previous/next source page only where the same structured
        section or table continues across a page boundary.

        This is deliberately conservative. It does NOT pull all surrounding
        pages just because they are adjacent. The adjacent page must share the
        same TableId, SectionHeading, or (as a fallback) RelatedSection.
        """
        include_previous = bool(
            self.context_config.get("include_previous_page_when_heading_continues", True)
        )
        include_next = bool(
            self.context_config.get("include_next_page_when_table_continues", True)
        )
        if not include_previous and not include_next:
            return []

        payload = seed.payload
        document_id = payload.get(FIELDS.document_id)
        page_number = payload.get(FIELDS.page_number)
        if not document_id:
            return []
        try:
            current_page = int(page_number)
        except (TypeError, ValueError):
            # PageID is stable identity but not necessarily sortable. Exact
            # adjacent page retrieval needs a numeric PageNumber.
            return []

        lower = current_page - 1 if include_previous else current_page
        upper = current_page + 1 if include_next else current_page
        page_window_filter = merge_filters(
            base_filter,
            models.Filter(
                must=[
                    match_value(FIELDS.document_id, document_id),
                    models.FieldCondition(
                        key=FIELDS.page_number,
                        range=models.Range(gte=lower, lte=upper),
                    ),
                ]
            ),
        )
        points = self._scroll_all(page_window_filter, MAX_SAME_PAGE_CHUNKS * 3)

        table_id = payload.get(FIELDS.table_id)
        section_value = payload.get(FIELDS.section_heading) or payload.get(FIELDS.related_section)
        result: list[CandidateChunk] = []
        for point in points:
            candidate = CandidateChunk(point_id=str(point.id), payload=safe_payload(point))
            candidate_page = candidate.payload.get(FIELDS.page_number)
            try:
                candidate_page = int(candidate_page)
            except (TypeError, ValueError):
                continue
            if candidate_page == current_page:
                continue

            same_table = bool(table_id) and candidate.payload.get(FIELDS.table_id) == table_id
            candidate_section = (
                candidate.payload.get(FIELDS.section_heading)
                or candidate.payload.get(FIELDS.related_section)
            )
            same_section = bool(section_value) and candidate_section == section_value

            if not (same_table or same_section):
                continue

            candidate.is_context = True
            candidate.context_reasons.add("adjacent_page_continuation")
            result.append(candidate)

        return result

    def _fetch_document_fallback(
        self,
        seed: CandidateChunk,
        base_filter: models.Filter,
    ) -> list[CandidateChunk]:
        """
        Safety fallback for the legacy schema with no ChunkIndex.

        It retrieves all chunks from the matched document up to a cap. This is
        deliberately broader than exact neighbours: it protects recall until
        ChunkIndex is added at ingestion time.
        """
        document_id = seed.payload.get(FIELDS.document_id)
        if not document_id:
            return []

        query_filter = merge_filters(
            base_filter,
            models.Filter(must=[match_value(FIELDS.document_id, document_id)]),
        )
        points = self._scroll_all(query_filter, MAX_DOCUMENT_FALLBACK_CHUNKS)
        chunks = [CandidateChunk(point_id=str(point.id), payload=safe_payload(point)) for point in points]
        for item in chunks:
            item.is_context = True
            item.context_reasons.add("whole_document_fallback_missing_chunk_index")
        return chunks

    def _expand_context(
        self,
        seeds: list[CandidateChunk],
        base_filter: models.Filter,
    ) -> tuple[list[CandidateChunk], list[str]]:
        """Expand important seed hits into a complete, grounded evidence pack."""
        if not self.context_config.get("enabled", True):
            return seeds, []

        before = int(self.context_config.get("neighbour_chunks_before", 2))
        after = int(self.context_config.get("neighbour_chunks_after", 2))
        warnings: list[str] = []
        expanded: list[CandidateChunk] = list(seeds)
        fallback_documents: set[str] = set()

        # Use only the strongest seed clusters. Their contexts are then added.
        for seed in seeds[: self.max_evidence_clusters]:
            if _env_bool("ENABLE_PREVIOUS_NEXT_CHUNKS", True):
                neighbours, sequence_available = self._fetch_exact_neighbours(seed, base_filter, before, after)
            else:
                neighbours, sequence_available = [], True
            if sequence_available:
                expanded.extend(neighbours)
            else:
                document_id = str(seed.payload.get(FIELDS.document_id, ""))
                if (_env_bool("ENABLE_DOCUMENT_CONTEXT", True) and document_id
                        and document_id not in fallback_documents):
                    fallback_documents.add(document_id)
                    expanded.extend(self._fetch_document_fallback(seed, base_filter))
                    warnings.append(
                        f"Document {document_id} has no {FIELDS.chunk_index}. "
                        "Whole-document fallback was used; exact previous/next chunk order is unavailable."
                    )

            if self.context_config.get("include_same_page_chunks", True):
                expanded.extend(self._fetch_same_page(seed, base_filter))
            expanded.extend(self._fetch_adjacent_pages_when_continued(seed, base_filter))
            if self.context_config.get("include_same_section", True):
                expanded.extend(self._fetch_same_section(seed, base_filter))
            if self.context_config.get("include_full_table_when_match_is_table_row", True):
                expanded.extend(self._fetch_full_table(seed, base_filter))

        max_context = _env_int("MAX_CONTEXT_CHUNKS", len(expanded))
        return expanded[:max_context], warnings

    # ----- Public API ----------------------------------------------------------

    def retrieve(self, company_id: str, tender_id: str) -> dict[str, Any]:
        """Run the complete profile-driven retrieval pipeline."""
        started = time.perf_counter()
        base_filter = build_base_filter(company_id, tender_id)
        anchors = list(self.profile.get("anchor_groups", []))
        if not anchors:
            raise ValueError("The retrieval profile contains no anchor_groups.")

        # Priority 1 anchor groups are submitted first. All remain included;
        # priority controls task ordering, not whether a category is searched.
        anchors.sort(key=lambda item: int(item.get("priority", 999)))
        all_candidates: list[CandidateChunk] = []

        if self.enable_parallel and len(anchors) > 1:
            with ThreadPoolExecutor(max_workers=min(self.max_query_workers, len(anchors))) as executor:
                futures = {executor.submit(self._search_anchor, anchor, base_filter): anchor["anchor_id"] for anchor in anchors}
                for future in as_completed(futures):
                    anchor_id = futures[future]
                    try:
                        all_candidates.extend(future.result())
                    except Exception:
                        logging.error("Evaluation retrieval failed for anchor %s", anchor_id)
                        raise
        else:
            for anchor in anchors:
                all_candidates.extend(self._search_anchor(anchor, base_filter))

        # Global exact + near duplicate removal, then cap the seed evidence set.
        deduplicated = self._deduplicate(all_candidates)
        deduplicated.sort(key=lambda item: item.final_score, reverse=True)
        seeds = deduplicated[: self.max_candidates]

        expanded, context_warnings = self._expand_context(seeds, base_filter)
        evidence = self._deduplicate(expanded)

        # Keep ranking score for seed items; context chunks retain their source
        # relationship and are sorted in readable document/page/chunk order.
        seed_ids = {item.identity() for item in seeds}
        for item in evidence:
            if item.identity() in seed_ids:
                item.is_context = False

        evidence.sort(
            key=lambda item: (
                str(item.payload.get(FIELDS.document_name, "")),
                *page_sort_value(item.payload),
                _safe_int(item.payload.get(FIELDS.chunk_index)),
                item.identity(),
            )
        )

        query_count = sum(len(self._anchor_queries(anchor)) for anchor in anchors)
        elapsed = time.perf_counter() - started
        result = {
            "retrieval_profile_id": self.profile.get("profile_id"),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "company_id": company_id,
            "tender_id": tender_id,
            "collection_name": self.collection_name,
            "retrieval_mode": {"hybrid": "hybrid_rrf", "sparse": "sparse_only"}.get(self.retrieval_mode, "dense_only"),
            "seed_candidate_count_before_deduplication": len(all_candidates),
            "seed_candidate_count_after_deduplication": len(deduplicated),
            "evidence_chunk_count": len(evidence),
            "warnings": context_warnings,
            "seed_chunks": [self._serialise(item) for item in seeds],
            "evidence_chunks": [self._serialise(item) for item in evidence],
            "retrieval_statistics": {
                "number_of_anchors": len(anchors),
                "queries_executed": query_count,
                "candidates": len(all_candidates),
                "deduplicated": len(all_candidates) - len(deduplicated),
                "final_evidence": len(evidence),
                "execution_time_seconds": round(elapsed, 6),
            },
        }
        logging.info("Retrieval complete | anchors=%s | queries=%s | candidates=%s | deduplicated=%s | evidence=%s | seconds=%.3f",
                     len(anchors), query_count, len(all_candidates), len(all_candidates) - len(deduplicated), len(evidence), elapsed)
        return result

    @staticmethod
    def _serialise(item: CandidateChunk) -> dict[str, Any]:
        """Produce JSON-safe output while preserving original payload fields."""
        return {
            "point_id": item.point_id,
            "document_id": item.payload.get(FIELDS.document_id),
            "chunk_id": item.payload.get(FIELDS.chunk_id),
            "document_name": item.payload.get(FIELDS.document_name),
            "document_type": item.payload.get(FIELDS.document_type),
            "page_id": item.payload.get(FIELDS.page_id),
            "page_number": item.payload.get(FIELDS.page_number),
            "chunk_index": item.payload.get(FIELDS.chunk_index),
            "related_section": item.payload.get(FIELDS.related_section),
            "retrieval": {
                "raw_max_score": round(item.raw_max_score, 8),
                "rank_score": round(item.rank_score, 8),
                "final_score": round(item.final_score, 8),
                "matched_anchors": sorted(item.matched_anchors),
                "matched_queries": sorted(item.matched_queries),
                "is_context": item.is_context,
                "context_reasons": sorted(item.context_reasons),
            },
            "text": item.text(),
            "payload": item.payload,
        }


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 10**12


# -----------------------------------------------------------------------------
# 6. Application entry point.
# -----------------------------------------------------------------------------


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def main() -> None:
    """Execute retrieval only and write the intermediate evidence pack."""
    _load_environment()
    logging.basicConfig(
        level=getattr(logging, _env_value("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    parser = argparse.ArgumentParser(description="Retrieve evaluation evidence from Qdrant.")
    parser.add_argument("--company-id", default=_env_value("COMPANY_ID"))
    parser.add_argument("--tender-id", default=_env_value("TENDER_ID"))
    parser.add_argument(
        "--profile-path",
        default=_env_value(
            "RETRIEVAL_PROFILE_PATH",
            "evaluation_retrieval_profile_complete (1).json",
        ),
    )
    parser.add_argument(
        "--retrieval-output",
        default=_env_value("RETRIEVAL_OUTPUT_PATH", "evaluation_evidence_debug.json"),
    )
    args = parser.parse_args()
    if not args.company_id or not args.tender_id:
        raise ConfigurationError(
            "Provide --company-id and --tender-id, or set COMPANY_ID and TENDER_ID."
        )

    profile = load_json(args.profile_path)
    global FIELDS
    FIELDS = configure_payload_fields(profile)

    dense_embedder = OpenAIEmbeddingProvider(
        api_key=None,
        model=_env_value("EMBEDDING_MODEL", "text-embedding-3-small"),
    ).embed
    enable_sparse = _env_bool(
        "QDRANT_ENABLE_SPARSE",
        _env_bool("ENABLE_SPARSE", False),
    )
    sparse_embedder: Optional[Callable[[str], models.SparseVector]] = None
    if enable_sparse:
        sparse_embedder = build_fastembed_sparse_embedder(
            _env_value(
                "QDRANT_SPARSE_MODEL",
                _env_value("SPARSE_MODEL_NAME", "Qdrant/bm25"),
            )
        )

    client = QdrantClient(
        url=_env_value("QDRANT_URL", "http://localhost:6333"),
        api_key=_env_value("QDRANT_API_KEY") or None,
        timeout=_env_float("QDRANT_SEARCH_TIMEOUT", 60.0),
    )
    retriever = EvaluationCriteriaRetriever(
        client=client,
        collection_name=_env_value("QDRANT_COLLECTION_NAME", "tender_chunks"),
        profile=profile,
        dense_embedder=dense_embedder,
        sparse_embedder=sparse_embedder,
    )
    evidence_pack = retriever.retrieve(
        company_id=args.company_id,
        tender_id=args.tender_id,
    )
    write_json(args.retrieval_output, evidence_pack)
    logging.info(
        "Retrieved %s evidence chunks. Output written to %s",
        evidence_pack["evidence_chunk_count"],
        Path(args.retrieval_output).resolve(),
    )


if __name__ == "__main__":
    main()
