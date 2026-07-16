from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router.routes import router

app = FastAPI(
    title="Grammar & Sentence Rephraser API",
    description="API for Grammar Correction and Sentence Rephrasing for Tender Documents",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(router)


@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "Grammar & Sentence Rephraser API",
        "version": "1.0.0",
    }