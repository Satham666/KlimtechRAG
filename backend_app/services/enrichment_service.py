import logging
import os
from typing import List

from haystack import Document as HaystackDocument

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Enrichment Service — Contextual Enrichment chunków (C4)
# Inspiracja: Anthropic Contextual Retrieval / LocalGPT
# Domyślnie OFF — wymaga działającego LLM przy ingeście.
# Włącz: KLIMTECH_CONTEXTUAL_ENRICHMENT=true
# ---------------------------------------------------------------------------

ENRICHMENT_ENABLED = (
    os.getenv("KLIMTECH_CONTEXTUAL_ENRICHMENT", "false").lower() == "true"
)

_ENRICHMENT_PROMPT = (
    "Opisz w jednym krótkim zdaniu (max 25 słów) kontekst tego fragmentu dokumentu. "
    "Skup się na temacie, a nie na treści dosłownej. Fragment:\n\n{chunk}"
)


def _call_llm(prompt: str) -> str:
    """Wywołuje lokalny LLM (llama-server) synchronicznie.

    Używa httpx jeśli dostępny, fallback na urllib.
    Zwraca pusty string przy błędzie — enrichment jest opcjonalny.
    """
    from ..config import settings

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 60,
        "temperature": 0.1,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}

    try:
        import httpx

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except ImportError:
        import json
        import urllib.request

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()


def enrich_chunks(
    docs: List[HaystackDocument],
) -> List[HaystackDocument]:
    """Wzbogaca chunki przez dołączenie krótkiego opisu kontekstu.

    Jeśli KLIMTECH_CONTEXTUAL_ENRICHMENT=false lub LLM niedostępny —
    zwraca oryginalne chunki bez zmian.

    Opis kontekstu jest dołączany na początku treści chunku:
    "[Kontekst: ...]\n\n{oryginalny chunk}"
    """
    if not ENRICHMENT_ENABLED or not docs:
        return docs

    enriched: List[HaystackDocument] = []
    for i, doc in enumerate(docs):
        original_content = doc.content or ""
        if not original_content.strip():
            enriched.append(doc)
            continue

        try:
            prompt = _ENRICHMENT_PROMPT.format(chunk=original_content[:800])
            context_desc = _call_llm(prompt)
            if context_desc:
                new_content = f"[Kontekst: {context_desc}]\n\n{original_content}"
                new_doc = HaystackDocument(content=new_content, meta=doc.meta)
                enriched.append(new_doc)
                logger.debug(
                    "[Enrichment] Chunk %d/%d: %s",
                    i + 1, len(docs), context_desc[:60],
                )
            else:
                enriched.append(doc)
        except Exception as e:
            logger.warning(
                "[Enrichment] Błąd LLM dla chunku %d: %s — używam oryginału", i + 1, e
            )
            enriched.append(doc)

    logger.info(
        "[Enrichment] Wzbogacono %d/%d chunków",
        sum(1 for d in enriched if d.content and d.content.startswith("[Kontekst:")),
        len(docs),
    )
    return enriched
