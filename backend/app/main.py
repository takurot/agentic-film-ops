from fastapi import FastAPI

from app.api import router

app = FastAPI(title="Agentic FilmOps Orchestrator")
app.include_router(router)
