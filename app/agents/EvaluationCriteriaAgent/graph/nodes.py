"""
Evaluation Criteria Agent
=========================

End-to-end orchestration for evaluation criteria extraction:

1. Retrieve evidence chunks from Qdrant using the profile-driven retriever.
2. Normalise retrieved chunks into the extraction prompt input contract.
3. Ask OpenAI for schema-shaped JSON.
4. Run deterministic validation checks.
5. Write both the retrieval evidence pack and final Evaluation_Evidence.json.

Example:
    py evaluation_criteria_agent.py --company-id <id> --tender-id <id>

Dry run:
    py evaluation_criteria_agent.py --company-id <id> --tender-id <id> --dry-run
"""

# =============================================================================
# 1. Imports
# =============================================================================

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# =============================================================================
# 2. Constants
# =============================================================================

DEFAULT_PROFILE_PATH = "app/agents/EvaluationCriteriaAgent/retrievalProfile/evaluation_retrieval_profile_complete (1).json"
DEFAULT_SPEC_PATH = "app/agents/EvaluationCriteriaAgent/resources/specification.json"
DEFAULT_CONSTITUTION_PATH = "app/agents/EvaluationCriteriaAgent/resources/constitution.md"
DEFAULT_PROMPT_PATH = "app/agents/EvaluationCriteriaAgent/prompts/runtime_prompt.md"
DEFAULT_RETRIEVAL_OUTPUT_PATH = "evaluation_evidence_debug.json"
DEFAULT_FINAL_OUTPUT_PATH = "Evaluation_Evidence.json"
DEFAULT_QDRANT_URL = "https://b18a6879-f119-47c1-8a5e-17af45713616.eu-west-2-0.aws.cloud.qdrant.io"
DEFAULT_QDRANT_COLLECTION = "CPTenderDoc"
DEFAULT_DENSE_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_MODEL = "gpt-4.1"


def _ec_env(name: str, default: Any = None) -> Any:
    """Read an Evaluation Criteria-specific environment variable."""
    return os.environ.get(f"EC_{name}", default)


# =============================================================================
# 3. Dataclasses
# =============================================================================


@dataclass(frozen=True)
class AgentPaths:
    profile: Path
    specification: Path
    constitution: Path
    runtime_prompt: Path
    retrieval_output: Path
    final_output: Path


@dataclass(frozen=True)
class OpenAIUsageRecord:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    latency: float
    company_id: str | None
    tender_id: str | None
    agent_name: str
    success: bool


# =============================================================================
# 4. Configuration
# =============================================================================


class ConfigurationError(Exception):
    """Raised for missing or invalid environment configuration."""


def load_environment() -> None:
    """Load the project .env while preserving explicitly exported values."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name(".env")
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip():
            value = value.strip().strip("'\"")
            os.environ.setdefault(key.strip(), value)


load_environment()


class Configuration:
    load_environment = staticmethod(load_environment)

    @staticmethod
    def parse_args() -> argparse.Namespace:
        return parse_args()

    @staticmethod
    def require_args(args: argparse.Namespace) -> None:
        require_args(args)


# =============================================================================
# 5. Logging
# =============================================================================


class LoggerError(Exception):
    """Raised internally when usage telemetry cannot be delivered."""


def _separator(character: str = "=") -> None:
    print(character * 60)


def _print_header(args: argparse.Namespace) -> None:
    _separator()
    print(f"Evaluation Criteria Agent {_ec_env('AGENT_VERSION', 'v1.0')}")
    _separator()
    print(f"Company:        {args.company_id}")
    print(f"Tender:         {args.tender_id}")
    print(f"Collection:     {args.qdrant_collection}")
    print(f"Retrieval Mode: {_ec_env('QDRANT_RETRIEVAL_MODE', 'AUTO')}")
    print(f"Vector Mode:    {_ec_env('QDRANT_VECTOR_MODE', 'AUTO')}")
    print(f"Dense Model:    {os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')}")
    print(f"Sparse Model:   {args.sparse_model_name if args.enable_sparse else 'disabled'}")
    _separator()


class AgentLogging:
    separator = staticmethod(_separator)
    print_header = staticmethod(_print_header)


# =============================================================================
# 6. Usage Tracker
# =============================================================================


class OpenAIUsageLogger:
    """Best-effort client for the central .NET OpenAI usage API."""

    def __init__(self) -> None:
        self.url = _ec_env("OPENAI_USAGE_LOGGER_URL", "").strip()
        self.timeout = float(_ec_env("OPENAI_USAGE_LOGGER_TIMEOUT", "5"))

    def post(self, record: OpenAIUsageRecord) -> None:
        if not self.url:
            logging.warning("OPENAI_USAGE_LOGGER_URL is not configured; usage telemetry skipped.")
            return
        payload = json.dumps(record.__dict__).encode("utf-8")
        request = urllib.request.Request(self.url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if not 200 <= response.status < 300:
                    raise LoggerError(f"Usage logger returned HTTP {response.status}.")
        except Exception as exc:
            logging.warning("OpenAI usage telemetry unavailable: %s", exc)


# =============================================================================
# 7. File Loader
# =============================================================================


class FileLoader:
    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def load_text(path: Path) -> str:
        return path.read_text(encoding="utf-8")


load_json = FileLoader.load_json
load_text = FileLoader.load_text


# =============================================================================
# 8. Retriever Service
# =============================================================================


class RetrieverService:
    """Namespace for the existing retriever construction and execution API."""

    @staticmethod
    def build(*args: Any, **kwargs: Any) -> Any:
        return build_retriever(*args, **kwargs)

    @staticmethod
    def retrieve(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return run_retrieval(*args, **kwargs)


# =============================================================================
# 9. LLM Service
# =============================================================================


class OpenAIError(Exception):
    """Raised when the extraction request fails."""


def coerce_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def payload_alias(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def normalise_evidence_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a retriever chunk into the canonical EvidenceChunks contract.

    The retriever preserves original Qdrant payload under "payload"; prefer
    that for PascalCase fields and fall back to the serialised snake_case keys.
    """
    payload = dict(chunk.get("payload") or {})
    return {
        "DocumentId": first_present(
            payload_alias(payload, "DocumentId", "document_id"),
            chunk.get("document_id"),
        ),
        "ChunkId": first_present(
            payload_alias(payload, "ChunkId", "chunk_id"),
            chunk.get("chunk_id"),
        ),
        "DocumentName": first_present(
            payload_alias(payload, "DocumentName", "document_name"),
            chunk.get("document_name"),
        ),
        "DocumentType": first_present(
            payload_alias(payload, "DocumentType", "document_type"),
            chunk.get("document_type"),
        ),
        "PageID": first_present(
            payload_alias(payload, "PageID", "page_id"),
            chunk.get("page_id"),
        ),
        "PageNumber": coerce_int_or_none(
            first_present(payload_alias(payload, "PageNumber", "page_number"), chunk.get("page_number"))
        ),
        "ChunkIndex": coerce_int_or_none(
            first_present(payload_alias(payload, "ChunkIndex", "chunk_index"), chunk.get("chunk_index"))
        ),
        "RelatedSection": first_present(
            payload_alias(payload, "RelatedSection", "related_section", "SectionHeading", "section_heading"),
            chunk.get("related_section"),
        ),
        "TableId": payload_alias(payload, "TableId", "table_id"),
        "TableCaption": payload_alias(payload, "TableCaption", "table_caption"),
        "TableHeaders": payload_alias(payload, "TableHeaders", "table_headers"),
        "TableJson": payload_alias(payload, "TableJson", "table_json"),
        "Text": first_present(payload_alias(payload, "Text", "text"), chunk.get("text"), ""),
        "OriginalPayload": payload,
    }


def build_llm_input(
    evidence_pack: dict[str, Any],
    company_id: str | None,
    tender_id: str,
) -> dict[str, Any]:
    evidence_chunks = [
        normalise_evidence_chunk(chunk)
        for chunk in evidence_pack.get("evidence_chunks", [])
        if isinstance(chunk, dict)
    ]
    return {
        "TenderContext": {
            "CompanyId": company_id,
            "TenderId": tender_id,
            "RetrievalProfileId": evidence_pack.get("retrieval_profile_id"),
        },
        "EvidenceChunks": evidence_chunks,
    }


def full_not_found_output(company_id: str | None, tender_id: str) -> dict[str, Any]:
    return {
        "SchemaVersion": "1.0",
        "CompanyId": company_id,
        "TenderId": tender_id,
        "EvaluationModelDetected": False,
        "ExtractionStatus": "NOT_FOUND",
        "OverallScoring": {
            "AwardMethod": None,
            "QualityWeightPercent": None,
            "PriceWeightPercent": None,
            "OtherOverallWeightings": [],
            "ScoringScale": {
                "Minimum": None,
                "Maximum": None,
                "Description": None,
                "SourceEvidence": [],
            },
            "PriceScoringFormula": None,
            "SourceEvidence": [],
        },
        "Criteria": [],
        "MandatoryConditions": [],
        "Conflicts": [],
        "MissingInformation": [
            {
                "Field": "EvaluationCriteria",
                "Reason": (
                    "No explicit evaluation, award, weighting, scoring, threshold, "
                    "pass/fail, or price-scoring evidence was found in the supplied evidence chunks."
                ),
                "RelatedCriterionId": None,
                "SourceEvidence": [],
            }
        ],
        "Validation": {
            "SourceCoverage": {
                "Status": "NOT_APPLICABLE",
                "Explanation": "No criteria or conditions were extracted.",
            },
            "NumericValidity": {
                "Status": "NOT_APPLICABLE",
                "Explanation": "No numeric evaluation values were extracted.",
            },
            "OverallWeightingReconciliation": {
                "Status": "NOT_ASSESSABLE",
                "CalculatedTotalPercent": None,
                "ExpectedTotalPercent": None,
                "Explanation": "No complete explicit overall weighting allocation was found.",
            },
            "ParentChildReconciliation": [],
            "PassFailSeparation": {
                "Status": "NOT_APPLICABLE",
                "Explanation": "No criteria or conditions were extracted.",
            },
            "SupersessionControl": {
                "Status": "NOT_APPLICABLE",
                "Explanation": "No supersession evidence was found.",
            },
            "MissingDataDiscipline": {
                "Status": "VALID",
                "Explanation": "No unsupported evaluation facts were emitted.",
            },
        },
        "ReviewFlags": [],
        "RequiresHumanReview": False,
        "SourceDocuments": [],
    }


class LLMService:
    """Namespace for the existing LLM input and extraction functions."""

    normalise_evidence_chunk = staticmethod(normalise_evidence_chunk)
    build_llm_input = staticmethod(build_llm_input)
    full_not_found_output = staticmethod(full_not_found_output)

    @staticmethod
    def extract(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return create_openai_extraction(*args, **kwargs)


# =============================================================================
# 10. Validation
# =============================================================================


class AgentValidationError(RuntimeError):
    """Raised when the final extraction violates schema or grounding rules."""


def make_retrieved_source_index(llm_input: dict[str, Any]) -> set[tuple[str, str]]:
    source_index: set[tuple[str, str]] = set()
    for chunk in llm_input.get("EvidenceChunks", []):
        document_id = chunk.get("DocumentId")
        chunk_id = chunk.get("ChunkId")
        if document_id is not None and chunk_id is not None:
            source_index.add((str(document_id), str(chunk_id)))
    return source_index


def iter_source_evidence(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if set(("DocumentId", "ChunkId", "EvidenceExcerpt")).issubset(value.keys()):
            yield value
        for child in value.values():
            yield from iter_source_evidence(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_source_evidence(child)


def iter_percentage_fields(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    percentage_names = {
        "QualityWeightPercent",
        "PriceWeightPercent",
        "WeightPercent",
        "MinimumPercent",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = f"{path}.{key}" if path else key
            if key in percentage_names:
                yield next_path, child
            yield from iter_percentage_fields(child, next_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_percentage_fields(child, f"{path}[{index}]")


def run_json_schema_validation(output: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        required = schema.get("required", [])
        return [f"Missing required top-level field: {key}" for key in required if key not in output]

    validator = Draft202012Validator(schema)
    return [error.message for error in sorted(validator.iter_errors(output), key=str)]


def deterministic_post_checks(
    output: dict[str, Any],
    specification: dict[str, Any],
    llm_input: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    schema = specification["output_contract"]["schema"]

    errors.extend(run_json_schema_validation(output, schema))

    for field in specification["output_contract"].get("required_top_level_fields", []):
        if field not in output:
            errors.append(f"Missing required top-level field: {field}")

    for collection_name in ("Criteria", "MandatoryConditions"):
        for index, item in enumerate(output.get(collection_name, []) or []):
            if not item.get("SourceEvidence"):
                errors.append(f"{collection_name}[{index}] has empty SourceEvidence.")

    for index, item in enumerate(output.get("Criteria", []) or []):
        primary = item.get("PrimaryCategory")
        secondary = set(item.get("SecondaryCategories") or [])
        weighted_only = primary == "WEIGHTED_CRITERION" and not secondary
        if weighted_only and (item.get("PassFail") is True or item.get("Mandatory") is True):
            errors.append(
                "Criteria[%s] is a pass/fail or mandatory item represented only "
                "as WEIGHTED_CRITERION." % index
            )

    for path, value in iter_percentage_fields(output):
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path} must be numeric or null.")
        elif value < 0 or value > 100:
            errors.append(f"{path} must be between 0 and 100.")

    retrieved_sources = make_retrieved_source_index(llm_input)
    for evidence in iter_source_evidence(output):
        excerpt = evidence.get("EvidenceExcerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            errors.append("SourceEvidence contains an empty EvidenceExcerpt.")

        source_key = (str(evidence.get("DocumentId")), str(evidence.get("ChunkId")))
        if source_key not in retrieved_sources:
            errors.append(
                "SourceEvidence references a chunk that was not retrieved: "
                f"DocumentId={source_key[0]}, ChunkId={source_key[1]}"
            )

    if (output.get("Conflicts") or output.get("ReviewFlags")) and not output.get("RequiresHumanReview"):
        errors.append("RequiresHumanReview must be true when Conflicts or ReviewFlags are present.")

    return errors


def validate_or_raise(
    output: dict[str, Any],
    specification: dict[str, Any],
    llm_input: dict[str, Any],
) -> None:
    errors = deterministic_post_checks(output, specification, llm_input)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise AgentValidationError(f"Evaluation output failed validation:\n{joined}")


class ValidationService:
    make_retrieved_source_index = staticmethod(make_retrieved_source_index)
    iter_source_evidence = staticmethod(iter_source_evidence)
    iter_percentage_fields = staticmethod(iter_percentage_fields)
    run_json_schema_validation = staticmethod(run_json_schema_validation)
    deterministic_post_checks = staticmethod(deterministic_post_checks)
    validate_or_raise = staticmethod(validate_or_raise)


def create_openai_extraction(
    llm_input: dict[str, Any],
    specification: dict[str, Any],
    constitution_text: str,
    runtime_prompt_text: str,
    model: str,
    usage_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install OpenAI SDK first: py -m pip install openai") from exc

    from app.infrastructure.secrets import resolve_openai_api_key

    client = OpenAI(api_key=resolve_openai_api_key(), timeout=float(_ec_env("OPENAI_TIMEOUT", "120")))
    output_schema = copy.deepcopy(specification["output_contract"]["schema"])

    def make_structured_output_compatible(value: Any) -> None:
        if isinstance(value, dict):
            if "type" not in value and "const" in value:
                constant = value["const"]
                value["type"] = ("boolean" if isinstance(constant, bool) else
                                 "number" if isinstance(constant, (int, float)) else
                                 "null" if constant is None else "string")
            elif "type" not in value and "enum" in value and value["enum"]:
                non_null = [item for item in value["enum"] if item is not None]
                if non_null and all(isinstance(item, str) for item in non_null):
                    value["type"] = ["string", "null"] if len(non_null) != len(value["enum"]) else "string"
            for key, child in list(value.items()):
                if isinstance(child, dict) and not child:
                    value[key] = {"anyOf": [{"type": kind} for kind in ("string", "number", "boolean", "null")]}
                else:
                    make_structured_output_compatible(child)
        elif isinstance(value, list):
            for child in value:
                make_structured_output_compatible(child)

    make_structured_output_compatible(output_schema)

    system_content = "\n\n".join(
        [
            runtime_prompt_text,
            "Mandatory constitution:",
            constitution_text,
            "Return JSON only. Use only the supplied EvidenceChunks.",
        ]
    )
    user_content = json.dumps(llm_input, ensure_ascii=False)

    started = time.perf_counter()
    success = False
    response = None
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            text={"format": {"type": "json_schema", "name": "Evaluation_Evidence",
                             "schema": output_schema, "strict": True}},
        )
        success = True
    except Exception as exc:
        raise OpenAIError(f"OpenAI extraction request failed: {exc}") from exc
    finally:
        latency = time.perf_counter() - started
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        input_rate = float(_ec_env("OPENAI_INPUT_COST_PER_1M", "0"))
        output_rate = float(_ec_env("OPENAI_OUTPUT_COST_PER_1M", "0"))
        record = OpenAIUsageRecord(
            timestamp=datetime.now(timezone.utc).isoformat(), model=model,
            input_tokens=input_tokens, output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 8),
            latency=round(latency, 6),
            company_id=llm_input.get("TenderContext", {}).get("CompanyId"),
            tender_id=llm_input.get("TenderContext", {}).get("TenderId"),
            agent_name=_ec_env("AGENT_NAME", "Evaluation Criteria Agent"), success=success,
        )
        OpenAIUsageLogger().post(record)
        from app.infrastructure.token_usage import TokenUsageService

        usage_context = usage_context or {}
        shared_usage = {
            "applicationName": _ec_env("AI_USAGE_APPLICATION_NAME", "Tender"),
            "sourceIds": [
                {"sourceIdType": "CompanyId", "id": record.company_id},
                {"sourceIdType": "TenderId", "id": record.tender_id},
                {"sourceIdType": "ProjectId", "id": usage_context.get("project_id", "")},
            ],
            "runId": usage_context.get("run_id", ""),
            "userId": usage_context.get("user_id", ""),
            "purpose": "Evaluation Criteria extraction",
            "method": "OpenAI Responses API",
            "agentName": _ec_env("AGENT_NAME", "Evaluation Criteria Agent"),
            "usageType": "LLM",
            "inputToken": record.input_tokens,
            "outputToken": record.output_tokens,
            "totalTokens": record.total_tokens,
            "model": record.model,
            "duration": record.latency,
            "cost": {"currency": "USD", "value": record.estimated_cost},
            "companyId": record.company_id,
            "tenderId": record.tender_id,
            "projectId": usage_context.get("project_id", ""),
        }
        try:
            import asyncio

            jwt_token = usage_context.get("jwt_token")
            if jwt_token:
                logging.getLogger("uvicorn.error").info(
                    "[AIUsageLogger] submission started | run_id=%s",
                    usage_context.get("run_id", ""),
                )
                asyncio.run(
                    TokenUsageService.log_usage(
                        shared_usage,
                        bearer_token=jwt_token,
                    )
                )
            else:
                logging.getLogger("uvicorn.error").warning(
                    "[AIUsageLogger] skipped: JwtToken was not provided | run_id=%s",
                    usage_context.get("run_id", ""),
                )
        except Exception as exc:
            logging.warning("Shared token usage logging unavailable: %s", exc)
        logging.info("OpenAI usage | input=%s | output=%s | total=%s | cost=%.6f | latency=%.2fs",
                     record.input_tokens, record.output_tokens, record.total_tokens,
                     record.estimated_cost, record.latency)

    output_text = getattr(response, "output_text", None)
    if not output_text:
        raise RuntimeError("OpenAI response did not contain output_text.")
    output = json.loads(output_text)

    def remove_identical_evidence_within_objects(value: Any) -> None:
        if isinstance(value, dict):
            evidence = value.get("SourceEvidence")
            if isinstance(evidence, list):
                unique: list[Any] = []
                seen: set[str] = set()
                for item in evidence:
                    identity = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if identity not in seen:
                        seen.add(identity)
                        unique.append(item)
                value["SourceEvidence"] = unique
                object_name = value.get("Name")
                if isinstance(object_name, str) and object_name.strip():
                    for item in unique:
                        if not isinstance(item, dict):
                            continue
                        excerpt = item.get("EvidenceExcerpt")
                        if not isinstance(excerpt, str) or "\n|" not in excerpt:
                            continue
                        matching_rows = [
                            line.strip().strip("|").strip()
                            for line in excerpt.splitlines()
                            if object_name.lower() in line.lower()
                            and not set(line.strip()) <= {"|", "-", ":"}
                        ]
                        if matching_rows:
                            item["EvidenceExcerpt"] = matching_rows[0]
            for child in value.values():
                remove_identical_evidence_within_objects(child)
        elif isinstance(value, list):
            for child in value:
                remove_identical_evidence_within_objects(child)

    remove_identical_evidence_within_objects(output)
    return output


def build_retriever(
    profile: dict[str, Any],
    qdrant_url: str,
    qdrant_api_key: str | None,
    collection_name: str,
    dense_model_name: str,
    enable_sparse: bool,
    sparse_model_name: str,
) -> Any:
    from app.agents.EvaluationCriteriaAgent.services import retrieval_service as retriever_module

    retriever_module.FIELDS = retriever_module.configure_payload_fields(profile)
    dense_embedder = retriever_module.build_local_dense_embedder(dense_model_name)

    sparse_embedder = None
    if enable_sparse:
        sparse_embedder = retriever_module.build_fastembed_sparse_embedder(sparse_model_name)

    client = retriever_module.QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        timeout=float(_ec_env("QDRANT_SEARCH_TIMEOUT", "60")),
    )
    return retriever_module.EvaluationCriteriaRetriever(
        client=client,
        collection_name=collection_name,
        profile=profile,
        dense_embedder=dense_embedder,
        sparse_embedder=sparse_embedder,
    )


def run_retrieval(
    company_id: str,
    tender_id: str,
    profile: dict[str, Any],
    qdrant_url: str,
    qdrant_api_key: str | None,
    collection_name: str,
    dense_model_name: str,
    enable_sparse: bool,
    sparse_model_name: str,
) -> dict[str, Any]:
    retriever = build_retriever(
        profile=profile,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        collection_name=collection_name,
        dense_model_name=dense_model_name,
        enable_sparse=enable_sparse,
        sparse_model_name=sparse_model_name,
    )
    return retriever.retrieve(company_id=company_id, tender_id=tender_id)


# =============================================================================
# 11. Output Writer
# =============================================================================


class OutputWriter:
    @staticmethod
    def write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def write_compact_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")),
            encoding="utf-8",
        )


write_json = OutputWriter.write_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve and extract tender evaluation criteria.")
    parser.add_argument("--company-id", default=_ec_env("COMPANY_ID"))
    parser.add_argument("--tender-id", default=_ec_env("TENDER_ID"))
    parser.add_argument("--qdrant-url", default=os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL))
    parser.add_argument("--qdrant-api-key", default=_ec_env("QDRANT_API_KEY") or None)
    parser.add_argument(
        "--qdrant-collection",
        default=_ec_env("QDRANT_COLLECTION_NAME", DEFAULT_QDRANT_COLLECTION),
    )
    parser.add_argument(
        "--dense-model-name",
        default=os.environ.get("EMBEDDING_MODEL", DEFAULT_DENSE_MODEL),
    )
    parser.add_argument(
        "--enable-sparse",
        action="store_true",
        default=_ec_env("QDRANT_ENABLE_SPARSE", "false").strip().lower() in {"1", "true", "yes"},
    )
    parser.add_argument("--sparse-model-name", default=_ec_env("QDRANT_SPARSE_MODEL", "Qdrant/bm25"))
    parser.add_argument("--openai-model", default=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL))
    parser.add_argument("--profile-path", default=_ec_env("RETRIEVAL_PROFILE_PATH", DEFAULT_PROFILE_PATH))
    parser.add_argument("--spec-path", default=_ec_env("SPECIFICATION_PATH", DEFAULT_SPEC_PATH))
    parser.add_argument(
        "--constitution-path",
        default=_ec_env("CONSTITUTION_PATH", DEFAULT_CONSTITUTION_PATH),
    )
    parser.add_argument("--prompt-path", default=_ec_env("RUNTIME_PROMPT_PATH", DEFAULT_PROMPT_PATH))
    parser.add_argument(
        "--retrieval-output",
        default=_ec_env("RETRIEVAL_OUTPUT_PATH", DEFAULT_RETRIEVAL_OUTPUT_PATH),
    )
    parser.add_argument(
        "--final-output",
        default=_ec_env("FINAL_OUTPUT_PATH", DEFAULT_FINAL_OUTPUT_PATH),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Retrieve Qdrant evidence and write only evaluation_evidence.json.",
    )
    parser.add_argument(
        "--skip-llm-when-no-evidence",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Emit the schema-valid NOT_FOUND output without calling the LLM when retrieval returns no chunks.",
    )
    return parser.parse_args(argv)


def require_args(args: argparse.Namespace) -> None:
    missing = []
    if not args.company_id:
        missing.append("--company-id or COMPANY_ID")
    if not args.tender_id:
        missing.append("--tender-id or TENDER_ID")
    if missing:
        raise SystemExit("Missing required input: " + ", ".join(missing))


# =============================================================================
# 12. EvaluationCriteriaAgent class
# =============================================================================


def _execute(
    args: argparse.Namespace,
    usage_context: dict[str, Any] | None = None,
    persist: bool = True,
    is_regenerated: bool = False,
    created_by: str = "",
    run_id: str = "",
) -> dict[str, Any] | None:
    require_args(args)
    _print_header(args)
    total_started = time.perf_counter()

    debug_enabled = _ec_env("ENABLE_DEBUG_LOGS", "false").lower() in {"1", "true", "yes", "on"}
    artifact_dir = Path("app/agents/EvaluationCriteriaAgent/artifacts")
    paths = AgentPaths(
        profile=Path(args.profile_path),
        specification=Path(args.spec_path),
        constitution=Path(args.constitution_path),
        runtime_prompt=Path(args.prompt_path),
        retrieval_output=(artifact_dir / "retrieval_output.json") if debug_enabled else Path(args.retrieval_output),
        final_output=(artifact_dir / "Evaluation_Evidence.json") if debug_enabled else Path(args.final_output),
    )

    profile = load_json(paths.profile)
    specification = load_json(paths.specification)

    logging.info("Retrieving evaluation evidence...")
    evidence_pack = run_retrieval(
        company_id=args.company_id,
        tender_id=args.tender_id,
        profile=profile,
        qdrant_url=args.qdrant_url,
        qdrant_api_key=args.qdrant_api_key,
        collection_name=args.qdrant_collection,
        dense_model_name=args.dense_model_name,
        enable_sparse=args.enable_sparse,
        sparse_model_name=args.sparse_model_name,
    )
    logging.info("✓ Retrieved %s chunks", evidence_pack.get("evidence_chunk_count", 0))
    logging.info("✓ Expanded Context")
    logging.info("✓ Deduplicated")

    if args.dry_run:
        logging.info("Dry run requested; skipping LLM extraction.")
        return None

    llm_input = build_llm_input(evidence_pack, args.company_id, args.tender_id)
    if args.skip_llm_when_no_evidence and not llm_input["EvidenceChunks"]:
        final_output = full_not_found_output(args.company_id, args.tender_id)
    else:
        constitution_text = load_text(paths.constitution)
        runtime_prompt_text = load_text(paths.runtime_prompt)
        _separator()
        logging.info("Calling OpenAI | model=%s", args.openai_model)
        final_output = create_openai_extraction(
            llm_input=llm_input,
            specification=specification,
            constitution_text=constitution_text,
            runtime_prompt_text=runtime_prompt_text,
            model=args.openai_model,
            usage_context=usage_context,
        )
        logging.info("✓ Request Complete")

    logging.info("Running validation...")
    validate_or_raise(final_output, specification, llm_input)
    logging.info("✓ Validation Passed")
    if persist:
        from app.agents.EvaluationCriteriaAgent.services.output_service import (
            EvaluationCriteriaOutputService,
        )

        mongo_document_id = EvaluationCriteriaOutputService.save(
            output=final_output,
            is_regenerated=is_regenerated,
            created_by=created_by,
            run_id=run_id,
        )
        logging.info(
            "Saved evaluation output to MongoDB | "
            "collection=EvaluationCriteria | document_id=%s | status=%s",
            mongo_document_id,
            "Regenerating" if is_regenerated else "Active",
        )
    _separator()
    logging.info("Completed Successfully | total_time=%.2fs", time.perf_counter() - total_started)
    _separator()
    return final_output


def _run_main() -> dict[str, Any] | None:
    return _execute(parse_args())


class EvaluationCriteriaAgent:
    """Coordinates the existing configuration, retrieval, LLM, and validation flow."""

    run = staticmethod(_run_main)

    @staticmethod
    def execute(
        company_id: str,
        tender_id: str,
        is_regenerated: bool = False,
        created_by: str = "",
        run_id: str = "",
        usage_context: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        args = parse_args([])
        args.company_id = company_id
        args.tender_id = tender_id

        output = _execute(
            args=args,
            usage_context=usage_context,
            persist=persist,
            is_regenerated=is_regenerated,
            created_by=created_by,
            run_id=run_id,
        )

        if output is None:
            raise RuntimeError("Evaluation Criteria execution did not produce a final output.")
        return output


# =============================================================================
# 13. main()
# =============================================================================


def main() -> None:
    debug = _ec_env("ENABLE_DEBUG_LOGS", "false").lower() in {"1", "true", "yes", "on"}
    level_name = "DEBUG" if debug else _ec_env("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, level_name, logging.INFO), format="[%(levelname)s] %(message)s")
    try:
        EvaluationCriteriaAgent.run()
    except SystemExit:
        raise
    except Exception as exc:
        if debug:
            logging.exception("Evaluation Criteria Agent failed")
        else:
            logging.error("Evaluation Criteria Agent failed: %s", exc)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()