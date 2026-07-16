from fastapi import FastAPI

from app.api.routes.router import router as taxonomy_router


app = FastAPI(title="Taxonomy Agent")
app.include_router(taxonomy_router)
