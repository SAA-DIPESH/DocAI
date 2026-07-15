from fastapi import APIRouter

from app.api.routes.evaluation_criteria_route import router as evaluation_criteria_router
from app.api.routes.agent_get_requirements_route import router as agent_requirements_router

api_router = APIRouter()

# Requirement Generation Agent Route
api_router.include_router(agent_requirements_router)

# Evalution Criteria Agent Route
api_router.include_router(evaluation_criteria_router)

