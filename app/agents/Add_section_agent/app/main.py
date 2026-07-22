from fastapi import FastAPI

from app.api.router.router import (
    router as add_section_router
)

app = FastAPI()

app.include_router(add_section_router)