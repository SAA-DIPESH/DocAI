from fastapi import APIRouter

from app.api.routes.agent_get_requirements_route import router as agent_requirements_router
from app.api.routes.section_writer_router import router as section_writer_router
from app.api.routes.evaluation_criteria_route import router as evaluation_criteria_router
from app.api.routes.wintheam_extractor_route import router as wintheam_extractor_router
from app.api.routes.wintheam_generator_route import router as wintheam_generator_router
from app.agents.taxonomy_agent.app.api.routes.router import router as taxonomy_router
from app.agents.GrammerAI.app.api.router.routes import router as grammar_router

api_router = APIRouter()

 
# Section Writer Route
api_router.include_router(section_writer_router)

# Requirement Agent Routes
api_router.include_router(agent_requirements_router)

# Evaluation Criteria Agent Routes
api_router.include_router(evaluation_criteria_router)

# Taxonomy Agent Routes
api_router.include_router(taxonomy_router)

# Grammar AI Routes
api_router.include_router(grammar_router)

# Win Theme Extractor Routes
api_router.include_router(wintheam_extractor_router)

# Win Theme Generator Routes
api_router.include_router(wintheam_generator_router)
