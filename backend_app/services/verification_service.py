import logging
import os

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# B5: Answer Verification — drugi pass LLM sprawdzający spójność z kontekstem
# Flaga: KLIMTECH_ANSWER_VERIFICATION=false (domyślnie wyłączone)
# Wynik: "high" | "low" — przy niskiej pewności odpowiedź dostaje ostrzeżenie
# ---------------------------------------------------------------------------

VERIFICATION_ENABLED: bool = (
    os.getenv("KLIMTECH_ANSWER_VERIFICATION", "false").lower() == "true"
)

_VERIFY_PROMPT = """Oceń, czy poniższa odpowiedź ASYSTENTA jest spójna i wynika bezpośrednio z podanego KONTEKSTU.

KONTEKST:
{context}

PYTANIE UŻYTKOWNIKA:
{question}

ODPOWIEDŹ ASYSTENTA:
{answer}

Odpowiedz TYLKO jednym słowem: TAK (odpowiedź wynika z kontekstu) lub NIE (odpowiedź może być halucynacją lub nie wynika z kontekstu).
Twoja odpowiedź:"""

_LOW_CONFIDENCE_SUFFIX = (
    "\n\n⚠️ *Weryfikacja: odpowiedź może nie wynikać bezpośrednio z dostępnego kontekstu "
    "(niska pewność).*"
)


def verify_answer(
    question: str,
    context: str,
    answer: str,
) -> str:
    """Weryfikuje spójność odpowiedzi z kontekstem przez drugi pass LLM.

    Zwraca "high" lub "low".
    Jeśli LLM jest niedostępny lub weryfikacja wyłączona → zwraca "high".
    """
    if not VERIFICATION_ENABLED:
        return "high"

    if not context or not context.strip():
        # Brak kontekstu RAG — nie ma czego weryfikować
        return "high"

    try:
        from . import get_llm_component

        prompt = _VERIFY_PROMPT.format(
            context=context[:3000],   # ogranicz kontekst do rozsądnej długości
            question=question[:500],
            answer=answer[:1000],
        )
        result = get_llm_component().run(prompt=prompt)
        verdict: str = result["replies"][0].strip().upper()

        # Szukamy TAK/NIE w pierwszych kilku znakach odpowiedzi
        if "NIE" in verdict[:20]:
            logger.info("[B5] Weryfikacja: NISKA pewność dla pytania: %s…", question[:60])
            return "low"
        logger.debug("[B5] Weryfikacja: wysoka pewność")
        return "high"

    except Exception as e:
        logger.warning("[B5] Weryfikacja niemożliwa (błąd LLM): %s", e)
        return "high"   # fail-open — nie blokuj odpowiedzi


def maybe_append_low_confidence(answer: str, confidence: str) -> str:
    """Jeśli confidence=='low', dołącza ostrzeżenie do odpowiedzi."""
    if confidence == "low":
        return answer + _LOW_CONFIDENCE_SUFFIX
    return answer
