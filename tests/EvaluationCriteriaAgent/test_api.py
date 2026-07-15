from unittest.mock import ANY, patch

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def request_json(is_regenerated: bool, company_id: str = "company-1", tender_id: str = "tender-1") -> dict:
    return {
        "CompanyId": company_id,
        "TenderId": tender_id,
        "IsRegenerated": is_regenerated,
        "UserName": "Jane Doe",
        "UserId": "user-1",
        "ProjectId": "project-1",
        "JwtToken": "jwt-token",
    }


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_agent_registered() -> None:
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert "EvaluationCriteriaAgent" in response.json()["agents"]


def test_regenerated_request_runs_agent() -> None:
    expected = {"ExtractionStatus": "COMPLETED"}
    with (
        patch("app.api.routes.evaluation_criteria_route.Logging") as logging_class,
        patch(
            "app.api.routes.evaluation_criteria_route.EvaluationCriteriaAgent.execute",
            return_value=expected,
        ) as execute,
        patch(
            "app.api.routes.evaluation_criteria_route.EvaluationCriteriaOutputService.insert_regenerated",
            return_value=("new-id", {**expected, "Status": "regenerating", "CreatedBy": "Jane Doe"}),
        ) as insert_regenerated,
    ):
        logging_class.return_value.start.return_value = {"token": "test"}
        response = client.post(
            "/api/v1/agents/evaluation-criteria/evaluate",
            json=request_json(True),
        )

    assert response.status_code == 200
    assert response.json()["Status"] == "regenerating"
    execute.assert_called_once_with(
        "company-1",
        "tender-1",
        usage_context={
            "run_id": ANY,
            "user_id": "user-1",
            "project_id": "project-1",
            "jwt_token": "jwt-token",
        },
        persist=False,
    )
    insert_regenerated.assert_called_once_with(
        expected,
        created_by="Jane Doe",
        run_id=ANY,
    )


def test_non_regenerated_request_returns_active_mongo_document() -> None:
    stored = {
        "_id": "mongo-id",
        "CompanyId": "company-1",
        "TenderId": "tender-1",
        "Status": "active",
    }
    with (
        patch("app.api.routes.evaluation_criteria_route.Logging") as logging_class,
        patch(
            "app.api.routes.evaluation_criteria_route.EvaluationCriteriaAgent.execute"
        ) as execute,
        patch(
            "app.api.routes.evaluation_criteria_route.EvaluationCriteriaOutputService.get_active",
            return_value=stored,
        ),
    ):
        logging_class.return_value.start.return_value = {"token": "test"}
        response = client.post(
            "/api/v1/agents/evaluation-criteria/evaluate",
            json=request_json(False),
        )

    assert response.status_code == 200
    assert response.json()["Status"] == "active"
    execute.assert_not_called()


def test_non_regenerated_missing_document_returns_404() -> None:
    with (
        patch("app.api.routes.evaluation_criteria_route.Logging") as logging_class,
        patch(
            "app.api.routes.evaluation_criteria_route.EvaluationCriteriaOutputService.get_active",
            return_value=None,
        ),
    ):
        logging_class.return_value.start.return_value = {"token": "test"}
        response = client.post(
            "/api/v1/agents/evaluation-criteria/evaluate",
            json=request_json(False, "missing", "missing"),
        )
    assert response.status_code == 404


def test_swagger_string_placeholders_are_rejected() -> None:
    response = client.post(
        "/api/v1/agents/evaluation-criteria/evaluate",
        json=request_json(False, "string", "string"),
    )
    assert response.status_code == 422
    assert "Replace the Swagger placeholder" in response.text
