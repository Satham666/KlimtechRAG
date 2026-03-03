"""
KlimtechRAG File Router — OWUI Filter Function
===============================================
Wklejasz ten plik w: Open WebUI → Workspace → Functions → + New Function

Co robi:
  Gdy użytkownik dołącza plik do wiadomości w czacie OWUI:
  1. Pobiera plik z wewnętrznego storage OWUI
  2. Wysyła do KlimtechRAG /upload
  3. KlimtechRAG zapisuje do Nextcloud (odpowiedni podfolder) i indeksuje do Qdrant RAG
  4. Plik pojawia się w Nextcloud UI i jest dostępny w RAG

Mapowanie rozszerzeń → Nextcloud:
  .pdf         → RAG_Dane/pdf_RAG/
  .docx, .doc  → RAG_Dane/Doc_RAG/
  .txt, .md    → RAG_Dane/txt_RAG/
  .mp3, .wav   → RAG_Dane/Audio_RAG/
  .jpg, .png   → RAG_Dane/Images_RAG/
  .mp4, .mkv   → RAG_Dane/Video_RAG/
  .json        → RAG_Dane/json_RAG/

Konfiguracja (Valves w UI):
  KLIMTECH_URL      — adres KlimtechRAG backend (domyślnie http://localhost:8000)
  KLIMTECH_API_KEY  — jeśli ustawiłeś KLIMTECH_API_KEY w .env
  OWUI_URL          — adres OWUI (domyślnie http://localhost:3000)
  OWUI_API_KEY      — API key z OWUI → Settings → Account → API Keys
"""

from pydantic import BaseModel
from typing import Optional
import requests
import logging

logger = logging.getLogger("owui.file_router")


class Filter:
    class Valves(BaseModel):
        KLIMTECH_URL: str = "http://localhost:8000"
        KLIMTECH_API_KEY: str = ""
        OWUI_URL: str = "http://localhost:3000"
        OWUI_API_KEY: str = ""    # OWUI → Settings → Account → API Keys
        ENABLED: bool = True
        DEBUG: bool = False

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
    ) -> dict:
        """
        Przechwytuje wiadomości przed wysłaniem do LLM.
        Jeśli wiadomość zawiera pliki — zapisuje je do Nextcloud przez KlimtechRAG.
        """
        if not self.valves.ENABLED:
            return body

        files = body.get("files", [])
        if not files:
            return body

        for file_info in files:
            file_id = file_info.get("id")
            filename = file_info.get("filename") or file_info.get("name", "unknown")
            content_type = file_info.get("type", "application/octet-stream")

            if not file_id:
                if self.valves.DEBUG:
                    logger.debug("[FileRouter] Brak ID pliku w: %s", file_info)
                continue

            if self.valves.DEBUG:
                logger.debug("[FileRouter] Przetwarzam: %s (id=%s)", filename, file_id)

            try:
                # 1. Pobierz plik z OWUI internal storage
                file_content = self._download_from_owui(file_id, filename)
                if file_content is None:
                    continue

                # 2. Wyślij do KlimtechRAG /upload → Nextcloud + Qdrant
                result = self._upload_to_klimtech(file_content, filename, content_type)

                if result:
                    nc_folder = result.get("nextcloud_folder", "?")
                    indexing = result.get("indexing", False)
                    status = "✅ RAG + Nextcloud" if indexing else "✅ Nextcloud (nie indeksowalny format)"
                    logger.info("[FileRouter] %s → %s/%s | %s", filename, nc_folder, filename, status)
                    print(f"[KlimtechRAG] {filename} → {nc_folder} | {status}")

            except Exception as e:
                logger.error("[FileRouter] Błąd dla %s: %s", filename, e)

        return body

    async def outlet(
        self,
        body: dict,
        __user__: Optional[dict] = None,
    ) -> dict:
        return body

    # -----------------------------------------------------------------------
    # Metody pomocnicze
    # -----------------------------------------------------------------------

    def _download_from_owui(self, file_id: str, filename: str) -> Optional[bytes]:
        """Pobiera zawartość pliku z OWUI przez REST API."""
        url = f"{self.valves.OWUI_URL}/api/v1/files/{file_id}/content"
        headers = {}
        if self.valves.OWUI_API_KEY:
            headers["Authorization"] = f"Bearer {self.valves.OWUI_API_KEY}"

        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 200:
                if self.valves.DEBUG:
                    logger.debug("[FileRouter] Pobrano %s: %d bajtów", filename, len(resp.content))
                return resp.content
            elif resp.status_code == 401:
                logger.error(
                    "[FileRouter] Brak autoryzacji OWUI. Ustaw OWUI_API_KEY w Valves. "
                    "OWUI → Settings → Account → API Keys"
                )
                return None
            else:
                logger.error("[FileRouter] OWUI /files/%s/content → HTTP %d", file_id, resp.status_code)
                return None
        except requests.exceptions.ConnectionError:
            logger.error("[FileRouter] Nie można połączyć się z OWUI: %s", self.valves.OWUI_URL)
            return None
        except Exception as e:
            logger.error("[FileRouter] Błąd pobierania z OWUI: %s", e)
            return None

    def _upload_to_klimtech(
        self, file_content: bytes, filename: str, content_type: str
    ) -> Optional[dict]:
        """Wysyła plik do KlimtechRAG /upload."""
        url = f"{self.valves.KLIMTECH_URL}/upload"
        headers = {}
        if self.valves.KLIMTECH_API_KEY:
            headers["X-API-Key"] = self.valves.KLIMTECH_API_KEY

        try:
            resp = requests.post(
                url,
                files={"file": (filename, file_content, content_type)},
                headers=headers,
                timeout=300,   # duże pliki mogą trwać
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(
                    "[FileRouter] KlimtechRAG /upload → HTTP %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
        except requests.exceptions.ConnectionError:
            logger.error("[FileRouter] Nie można połączyć się z KlimtechRAG: %s", self.valves.KLIMTECH_URL)
            return None
        except Exception as e:
            logger.error("[FileRouter] Błąd uploadu do KlimtechRAG: %s", e)
            return None
