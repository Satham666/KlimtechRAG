"""
routes/ui.py — KlimtechRAG Interface v5
Serwuje statyczny plik HTML ze static/index.html
"""
import os
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

# Ścieżka do pliku HTML
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
HTML_FILE = os.path.join(STATIC_DIR, "index.html")

def get_html_content():
    """Czyta plik HTML ze static katalogu"""
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"""<!DOCTYPE html>
<html><head><title>Error</title></head><body>
<h1>Błąd</h1><p>Nie znaleziono pliku {HTML_FILE}</p>
</body></html>"""



@router.get("/", response_class=HTMLResponse)
async def main_ui():
    return HTMLResponse(content=get_html_content())
