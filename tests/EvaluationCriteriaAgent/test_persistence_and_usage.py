from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.agents.EvaluationCriteriaAgent.services.output_service import (
    EvaluationCriteriaOutputService,
)
from app.infrastructure.token_usage import TokenUsageService


def test_output_is_upserted_to_evaluation_criteria_collection() -> None:
    output = {
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "ExtractionStatus": "COMPLETED",
    }
    store = Mock()
    store.upsert.return_value = "mongo-id"
    with patch(
        "app.agents.EvaluationCriteriaAgent.services.output_service.MongoDocumentStore",
        return_value=store,
    ) as store_class:
        result = EvaluationCriteriaOutputService.save(output)

    assert result == "mongo-id"
    store_class.assert_called_once_with("EvaluationCriteria")
    store.upsert.assert_called_once_with(
        {"CompanyId": "company-1", "TenderId": "tender-1"},
        output,
    )
    store.close.assert_called_once()


def test_openai_responses_usage_is_extracted() -> None:
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=120, output_tokens=30, total_tokens=150),
        response_metadata={"model": "gpt-4.1"},
    )
    assert TokenUsageService.extract_token_usage(response) == {
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
        "model": "gpt-4.1",
    }


def test_status_and_get_use_same_mongo_collection() -> None:
    store = Mock()
    store.set_status.return_value = True
    store.find_one.return_value = {"Status": "active"}
    with patch(
        "app.agents.EvaluationCriteriaAgent.services.output_service.MongoDocumentStore",
        return_value=store,
    ):
        assert EvaluationCriteriaOutputService.set_status(
            "company-1", "tender-1", "active"
        )
        assert EvaluationCriteriaOutputService.get("company-1", "tender-1") == {
            "Status": "active"
        }
