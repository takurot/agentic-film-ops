from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.runtime import RuntimeSettings, build_runtime_container

load_dotenv()  # picks up GEMINI_API_KEY etc. from backend/.env, if present


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = build_runtime_container(RuntimeSettings.from_env())
    await runtime.start()
    app.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.close()


app = FastAPI(title="Agentic FilmOps Orchestrator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
