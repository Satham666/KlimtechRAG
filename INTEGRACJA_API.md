# Integracja model_switch z backendem
# =====================================

## Plik 1: services/model_manager.py
# Skopiuj do: /media/lobo/BACKUP/KlimtechRAG/backend_app/services/model_manager.py

## Plik 2: routes/model_switch.py  
# Skopiuj do: /media/lobo/BACKUP/KlimtechRAG/backend_app/routes/model_switch.py

## Plik 3: Modyfikacja main.py
# Dodaj poniższe linie do backend_app/main.py

# ---------------------------------------------------------------------------
# W sekcji importów dodaj:
# ---------------------------------------------------------------------------

from routes import model_switch

# ---------------------------------------------------------------------------
# W sekcji rejestracji routerów dodaj:
# ---------------------------------------------------------------------------

app.include_router(model_switch.router)

# ---------------------------------------------------------------------------
# Przykładowy main.py po modyfikacji:
# ---------------------------------------------------------------------------

"""
backend_app/main.py - FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routerów
from routes import chat, ingest, filesystem, admin, ui, model_switch  # <-- DODAJ model_switch

# Import konfiguracji
from config import settings

# Tworzenie aplikacji
app = FastAPI(
    title="KlimtechRAG API",
    description="RAG System with LLM/VLM switching",
    version="7.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Rejestracja routerów
app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(filesystem.router)
app.include_router(admin.router)
app.include_router(ui.router)
app.include_router(model_switch.router)  # <-- DODAJ TE LINIĘ

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "version": "7.0"}

# ... reszta kodu ...
"""
