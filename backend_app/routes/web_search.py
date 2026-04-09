"""
Web Search Module for KlimtechRAG
==================================
Endpoints for web searching, page fetching, and summarization.
Uses DuckDuckGo for search and trafilatura for HTML-to-text conversion.

Author: KlimtechRAG
"""

import ipaddress
import json
import logging
import socket
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

try:
    from duckduckgo_search import DDGS

    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    DUCKDUCKGO_AVAILABLE = False
    logging.warning("duckduckgo-search not installed")

try:
    import trafilatura

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logging.warning("trafilatura not installed")

from ..config import settings
from ..utils.dependencies import get_request_id, require_api_key
from ..utils.rate_limit import apply_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web", tags=["Web Search"])


class WebSearchRequest(BaseModel):
    query: str
    num_results: int = Field(5, ge=1, le=20)


class WebFetchRequest(BaseModel):
    url: str
    max_length: int = Field(50000, ge=1, le=500_000)


class WebSummarizeRequest(BaseModel):
    url: str
    max_chars: int = Field(4000, ge=1, le=50_000)


def _assert_public_url(url: str) -> None:
    """Blokuje SSRF — odrzuca adresy prywatne/lokalne."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    host = parsed.hostname or ""
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
    except (socket.gaierror, ValueError):
        raise HTTPException(status_code=400, detail="Cannot resolve host")
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise HTTPException(status_code=400, detail="Private/local addresses not allowed")


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    domain: str
    rank: int = 0


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc
    except Exception:
        return ""


@router.post("/search")
async def web_search(request: WebSearchRequest, req: Request, _=Depends(require_api_key)) -> JSONResponse:
    """
    Search the web using DuckDuckGo.

    Returns list of search results with title, URL, snippet, and domain.
    """
    request_id = await get_request_id(req)

    require_api_key(req)

    # Rate limiting
    client_id = req.client.host if req.client else "unknown"
    apply_rate_limit(client_id)

    if not DUCKDUCKGO_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="DuckDuckGo search not available. Install: pip install duckduckgo-search",
        )

    logger.info(
        f"Web search: '{request.query}' (num={request.num_results})",
        extra={"request_id": request_id},
    )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(request.query, max_results=request.num_results))

        search_results = []
        for i, result in enumerate(results):
            url = result.get("href", "")
            search_results.append(
                WebSearchResult(
                    title=result.get("title", ""),
                    url=url,
                    snippet=result.get("body", ""),
                    domain=_extract_domain(url),
                    rank=i,
                )
            )

        return JSONResponse(
            {
                "query": request.query,
                "num_results": len(search_results),
                "results": [r.model_dump() for r in search_results],
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Web search error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/fetch")
async def web_fetch(request: WebFetchRequest, req: Request, _=Depends(require_api_key)) -> JSONResponse:
    """
    Fetch a web page and extract text content.

    Uses trafilatura for HTML-to-text conversion.
    Returns title, text content, and metadata.
    """
    request_id = await get_request_id(req)

    require_api_key(req)

    # Rate limiting
    client_id = req.client.host if req.client else "unknown"
    apply_rate_limit(client_id)

    if not TRAFILATURA_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Trafilatura not available. Install: pip install trafilatura",
        )

    logger.info(f"Web fetch: {request.url}", extra={"request_id": request_id})

    _assert_public_url(request.url)

    try:
        # Download with timeout and size limit
        timeout = httpx.Timeout(10.0, connect=5.0)

        # Use a common browser-like user agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        with httpx.Client(timeout=timeout, headers=headers) as client:
            response = client.get(request.url)
            response.raise_for_status()

            # Check content length
            content_length = len(response.content)
            if content_length > request.max_length:
                logger.warning(
                    f"Content too large: {content_length} bytes, truncating to {request.max_length}",
                    extra={"request_id": request_id},
                )

            html_content = response.content[: request.max_length].decode(
                "utf-8", errors="ignore"
            )

        # Extract text using trafilatura
        extracted = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            output_format="json",
        )

        if extracted:
            result_data = json.loads(extracted)
            text_content = result_data.get("text", "")
            title = result_data.get("title", "") or result_data.get("hostname", "")
        else:
            # Fallback: basic text extraction
            text_content = (
                html_content[:5000] if len(html_content) > 5000 else html_content
            )
            title = ""

        return JSONResponse(
            {
                "url": request.url,
                "title": title,
                "text": text_content,
                "length": len(text_content),
                "fetched_at": datetime.now().isoformat(),
            }
        )

    except httpx.TimeoutException:
        logger.error(
            f"Timeout fetching {request.url}", extra={"request_id": request_id}
        )
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error fetching {request.url}: {e}", extra={"request_id": request_id}
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to fetch: {e.response.status_code}",
        )
    except Exception as e:
        logger.error(f"Fetch error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")


@router.post("/summarize")
async def web_summarize(request: WebSummarizeRequest, req: Request, _=Depends(require_api_key)) -> JSONResponse:
    """
    Fetch a web page and summarize it using the LLM.

    1. Downloads page content
    2. Truncates to max_chars
    3. Sends to LLM with summarize prompt
    4. Returns LLM-generated summary
    """
    request_id = await get_request_id(req)

    require_api_key(req)

    # Rate limiting
    client_id = req.client.host if req.client else "unknown"
    apply_rate_limit(client_id)

    _assert_public_url(request.url)
    logger.info(f"Web summarize: {request.url}", extra={"request_id": request_id})

    try:
        # Step 1: Fetch the page
        fetch_request = WebFetchRequest(url=request.url, max_length=50000)

        timeout = httpx.Timeout(10.0, connect=5.0)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        with httpx.Client(timeout=timeout, headers=headers) as client:
            response = client.get(request.url)
            response.raise_for_status()
            html_content = response.content[:50000].decode("utf-8", errors="ignore")

        # Extract text
        if TRAFILATURA_AVAILABLE:
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                output_format="json",
            )
            if extracted:
                result_data = json.loads(extracted)
                text_content = result_data.get("text", "")
            else:
                text_content = html_content[:10000]
        else:
            # Basic fallback
            import re

            # Remove script and style tags
            clean = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                html_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            clean = re.sub(
                r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE
            )
            # Get text
            text_content = re.sub(r"<[^>]+>", " ", clean)
            text_content = " ".join(text_content.split())
            text_content = text_content[:10000]

        # Step 2: Truncate to max_chars
        if len(text_content) > request.max_chars:
            text_content = text_content[: request.max_chars] + "..."

        # Step 3: Call LLM to summarize
        from ..services.llm import get_llm_component

        summarize_prompt = f"""Przeczytaj poniższy artykuł i napisz krótkie, zwięzłe podsumowanie w języku polskim (2-3 zdania).

Tytuł/źródło: {request.url}

Treść:
{text_content}

Podsumowanie:"""

        try:
            llm = get_llm_component()
            result = llm.run(prompt=summarize_prompt)
            summary = (
                result.get("replies", [""])[0]
                if isinstance(result, dict)
                else str(result)
            )
        except Exception as e:
            logger.error(f"LLM summarize error: {e}", extra={"request_id": request_id})
            summary = f"Błąd podsumowania przez LLM: {str(e)}"

        return JSONResponse(
            {
                "url": request.url,
                "summary": summary,
                "source_length": len(text_content),
                "summarized_at": datetime.now().isoformat(),
            }
        )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Summarize error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=f"Summarize failed: {str(e)}")


@router.get("/status")
async def web_status(req: Request, _=Depends(require_api_key)) -> JSONResponse:
    """Check availability of web search dependencies."""
    return JSONResponse(
        {
            "duckduckgo": DUCKDUCKGO_AVAILABLE,
            "trafilatura": TRAFILATURA_AVAILABLE,
            "endpoints": {
                "search": "/web/search",
                "fetch": "/web/fetch",
                "summarize": "/web/summarize",
            },
        }
    )
