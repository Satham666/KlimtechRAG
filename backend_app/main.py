import logging
import os
import time
from .routes import model_switch
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .routes import (
    chat_router,
    ingest_router,
    filesystem_router,
    admin_router,
    ui_router,
    web_search_router,
)

from .services import doc_store
from .file_registry import init_db as init_file_registry

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

app = FastAPI()

app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(filesystem_router)
app.include_router(admin_router)
app.include_router(ui_router)
app.include_router(model_switch.router)
app.include_router(web_search_router)


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


@app.on_event("startup")
async def startup_event():
    init_file_registry()
    logger.info("File registry initialized")


if __name__ == "__main__":
    import uvicorn

    logger.info("Startowanie KlimtechRAG Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
