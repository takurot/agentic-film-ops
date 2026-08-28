import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analysis_runner import recover_stale_analyses
from app.api import router
from app.runtime import RuntimeSettings, build_runtime_container
from app.security import (
    RequestBodySizeLimitASGIMiddleware,
    SecurityConfig,
    SecurityHeadersASGIMiddleware,
    redact_secrets,
)

load_dotenv()  # picks up GEMINI_API_KEY etc. from backend/.env, if present

logger = logging.getLogger("filmops.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    security_config = getattr(app.state, "security_config", None) or SecurityConfig.from_env()
    app.state.security_config = security_config

    runtime = build_runtime_container(RuntimeSettings.from_env())
    if runtime.analysis_runner and hasattr(runtime.analysis_runner, "bind"):
        recover_stale_analyses(runtime.analysis_runner.bind)
    await runtime.start()
    app.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.close()


def create_app(security_config: SecurityConfig | None = None) -> FastAPI:
    config = security_config or SecurityConfig.from_env()

    app = FastAPI(title="Agentic FilmOps Orchestrator", lifespan=lifespan)
    app.state.security_config = config

    # 1. Attach Request Body Size Limiter (Outer ASGI Middleware)
    app.add_middleware(
        RequestBodySizeLimitASGIMiddleware,
        max_body_bytes=config.max_request_body_bytes,
    )

    # 2. Attach Security Headers Middleware
    app.add_middleware(SecurityHeadersASGIMiddleware)

    # 3. Attach CORS Middleware with Strict Allowed Origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )

    # 4. Global Unhandled Exception Redaction Handler
    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        sanitized_error = redact_secrets(str(exc))
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {sanitized_error}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "INTERNAL_SERVER_ERROR",
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Raw traces and credentials have been redacted.",
            },
        )

    # 5. Include API Router
    app.include_router(router)

    return app


app = create_app()
