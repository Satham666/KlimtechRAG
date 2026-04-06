import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routes import (
    chat_router,
    ingest_router,
    filesystem_router,
    admin_router,
    ui_router,
    model_switch_router,
    web_search_router,
)
from .routes.whisper_stt import router as whisper_router
from .routes.gpu_status import router as gpu_router
from .routes.chunks import router as chunks_router
from .routes.workspaces import router as workspaces_router
from .routes.collections import router as collections_router
from .routes.sessions import router as sessions_router
from .routes.mcp import router as mcp_router

from .services import doc_store
from .file_registry import init_db as init_file_registry
from .services.session_service import init_sessions_db

logger = logging.getLogger("klimtechrag")

if not logger.handlers:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    log_dir = os.path.join(settings.base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "backend.log")

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logger.addFilter(RequestIdFilter())


# ---------------------------------------------------------------------------
# Lifespan — zastepuje deprecated @app.on_event("startup")
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    from .config import validate_config
    validate_config()
    init_file_registry()
    logger.info("File registry initialized")
    init_sessions_db()
    logger.info("Sessions DB initialized")
    yield
    # --- shutdown ---
    logger.info("KlimtechRAG Backend shutting down")


app = FastAPI(
    title="KlimtechRAG API",
    version="7.6",
    description=(
        "KlimtechRAG — lokalny system RAG z VLM, ColPali, streaming i zarzadzaniem dokumentow. "
        "OpenAI-compatible chat completions, hybrid search, reranking, workspaces."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — wymagane dla Nextcloud AI Assistant (cross-origin requests)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # HTTP
        "http://192.168.31.70:8081",  # Nextcloud
        "http://192.168.31.70:8000",  # Backend UI
        "http://localhost:8081",
        "http://localhost:8000",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8000",
        # HTTPS
        "https://192.168.31.70:8443",  # Backend HTTPS
        "https://192.168.31.70:8444",  # Nextcloud HTTPS
        "https://localhost:8443",
        "https://localhost:8444",
        "https://127.0.0.1:8443",
        "https://127.0.0.1:8444",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(filesystem_router)
app.include_router(admin_router)
app.include_router(ui_router)
app.include_router(model_switch_router)
app.include_router(web_search_router)
app.include_router(whisper_router)
app.include_router(gpu_router)
app.include_router(chunks_router)
app.include_router(workspaces_router)
app.include_router(collections_router)
app.include_router(sessions_router)
app.include_router(mcp_router)


@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(time.time_ns())
    request.state.request_id = request_id

    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled error", extra={"request_id": request_id})
        raise exc
    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "Request %s %s finished in %d ms",
        request.method,
        request.url.path,
        duration_ms,
        extra={"request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("Unhandled exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Startowanie KlimtechRAG Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
