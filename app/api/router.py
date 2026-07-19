from fastapi import APIRouter

from app.api.routes.evaluation_criteria_route import router as evaluation_criteria_router
from app.agents.taxonomy_agent.app.api.routes.router import router as taxonomy_router
from app.agents.GrammerAI.app.api.router.routes import router as GrammerAI
from app.api.routes.agent_get_requirements_route import router as agent_requirements_router
from app.api.routes.section_writer_router import router as section_writer_router
api_router = APIRouter()
# api_router.include_router(evaluation_criteria_router)

# Requirement Generation Agent Route
# api_router.include_router(agent_requirements_router)

# # Evalution Criteria Agent Route
# api_router.include_router(evaluation_criteria_router)
# api_router.include_router(taxonomy_router)
# api_router.include_router(GrammerAI)

api_router.include_router(section_writer_router)

