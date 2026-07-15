from __future__ import annotations

import os
from unittest.mock import patch

from app.agents.EvaluationCriteriaAgent.graph.nodes import parse_args
from app.agents.EvaluationCriteriaAgent.services.retrieval_service import _env_value


def test_common_environment_variables_remain_unprefixed() -> None:
    environment = {
        "QDRANT_URL": "http://common-qdrant:6333",
        "QDRANT_COLLECTION_NAME": "CPDocuments",
        "EC_QDRANT_COLLECTION_NAME": "CPTenderDoc",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "OPENAI_MODEL": "gpt-4.1",
        "EC_QDRANT_RETRIEVAL_MODE": "dense",
    }
    with patch.dict(os.environ, environment, clear=True):
        args = parse_args([])
        assert args.qdrant_url == "http://common-qdrant:6333"
        assert args.qdrant_collection == "CPTenderDoc"
        assert args.dense_model_name == "text-embedding-3-small"
        assert args.openai_model == "gpt-4.1"
        assert _env_value("QDRANT_RETRIEVAL_MODE") == "dense"
        assert _env_value("QDRANT_COLLECTION_NAME") == "CPTenderDoc"


def test_agent_specific_unprefixed_variable_is_ignored() -> None:
    environment = {
        "QDRANT_TOP_K": "999",
        "EC_QDRANT_TOP_K": "15",
    }
    with patch.dict(os.environ, environment, clear=True):
        assert _env_value("QDRANT_TOP_K") == "15"
