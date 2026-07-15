from fastapi import APIRouter

from app.api.routes.evaluation_criteria_route import router as evaluation_criteria_router


api_router = APIRouter()
api_router.include_router(evaluation_criteria_router)


@api_router.get("/api/v1/agents", tags=["Agents"])
def list_agents() -> dict[str, list[str]]:
    return {"agents": ["EvaluationCriteriaAgent"]}
