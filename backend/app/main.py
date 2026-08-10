from dotenv import load_dotenv
from fastapi import FastAPI

from app.api import router

load_dotenv()  # picks up GEMINI_API_KEY etc. from backend/.env, if present

app = FastAPI(title="Agentic FilmOps Orchestrator")
app.include_router(router)
