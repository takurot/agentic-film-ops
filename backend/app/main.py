from fastapi import FastAPI

app = FastAPI(title="Agentic FilmOps Orchestrator")


@app.get("/api/production/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
