from fastapi import FastAPI

from app.api.routes.router import router


app = FastAPI()

app.include_router(router)