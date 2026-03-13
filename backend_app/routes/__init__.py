from .chat import router as chat_router
from .ingest import router as ingest_router
from .filesystem import router as filesystem_router
from .admin import router as admin_router
from .ui import router as ui_router
from .model_switch import router as model_switch_router

__all__ = [
    "chat_router", "ingest_router", "filesystem_router",
    "admin_router", "ui_router", "model_switch_router",
]
