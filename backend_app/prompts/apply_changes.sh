#!/bin/bash
# Plik docelowy
TARGET="vlm_prompts.py"

# Tworzenie nowej treści
cat > "$TARGET" << 'EOF'
# VLM Prompts for image description in KlimtechRAG
# Refaktoryzacja z image_handler.py - Sekcja 16

from dataclasses import dataclass
from typing import Optional

# VLM Parameters (dynamiczne, zamiast hardcoded w image_handler.py)
VLM_PARAMS = {
    "max_tokens": 512,
    "temperature": 0.1,
    "context_length": 4096,
    "gpu_layers": 99,  # -ngl 99 (wszystkie warstwy na GPU)
}

# Typy obrazów z wskazówkami dla heurystyki/klasyfikatora
# Uwaga: 'default' jest bezpiecznym wyborem, gdy typ nie jest pewny.
IMAGE_TYPES = [
    "default",     # Uniwersalny
    "diagram",     # Schematy blokowe, flowcharty, UML, sieci
    "chart",       # Wykresy (liniowe, słupkowe, kołowe), histogramy
    "table",       # Tabele danych, zestawienia, cenniki
    "photo",       # Zdjęcia obiektów, ludzi, miejsc, sprzętu
    "screenshot",  # Zrzuty ekranu UI, aplikacji, stron www, komunikaty błędów
    "technical",   # Schematy elektryczne, mechaniczne, CAD, rzuty techniczne
    "medical",     # RTG, MRI, USG, tomografia, obrazowanie medyczne
]

@dataclass
class VLMPrompt:
    name: str
    system: str
    user_template: str


# DEFAULT - uniwersalny, szczegółowy prompt
# Prompt domyślny – używany, gdy typ obrazu nie został rozpoznany lub nie ma dedykowanego promptu.
# System: rola eksperta uniwersalnego.
# User_template: szczegółowe instrukcje wymagające strukturyzacji opisu.
# UWAGA: Ten prompt jest bazą dla innych – jeśli go modyfikujesz, sprawdź, czy nie wpływa na dedykowane typy.
# Zasada bezpieczeństwa: nie dodawaj tutaj żadnych danych wrażliwych ani instrukcji do logowania.
DEFAULT_PROMPT = VLMPrompt(
    name="DEFAULT",
    system="Jesteś ekspertem w analizie obrazów. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz obraz w sposób szczegółowy i strukturalny.

INSTRUKCJE:
1. Co przedstawia obraz? (ogólny opis)
2. Główne elementy widoczne na obrazie
3. Tekst widoczny na obrazie (przepisz dokładnie, zachowując wielkość liter)
4. Liczby, dane numeryczne, etykiety (jeśli występują)
5. Kolory, proporcje, wymiary (jeśli widoczne)
6. Kontekst/zastosowanie (co to może być, do czego służy)
7. Język tekstu na obrazku (jeśli inny niż polski).

WAŻNE:
- Jeśli element jest nieczytelny, napisz "nieczytelne" zamiast zgadywać.
- Nie interpretuj, jeśli brak podstaw (opisz fakty).

FORMAT WYJŚCIA:
Strukturyzowany opis, maksymalnie 200 słów. Używaj punktów 1-7.

Obraz do analizy:""",
)

# DIAGRAM - dla schematów, flowchartów, algorytmów
# Prompt dla diagramów (schematy, flowchart, UML).
# Specjalizacja: ekspert od diagramów – wymaga precyzyjnego opisu elementów i relacji.
# Wskazówka: instrukcje kierują uwagę na typ diagramu, węzły, połączenia, etykiety i logikę.
# Jeśli rozszerzasz ten prompt, upewnij się, że nie traci on fokusu na strukturę.
# Zgodnie z AGENTS.md: każda zmiana promptu powinna być osobnym, atomowym krokiem z opisem diff.
DIAGRAM_PROMPT = VLMPrompt(
    name="DIAGRAM",
    system="Jesteś ekspertem w analizie diagramów i schematów. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz diagram/schemat w sposób szczegółowy.

INSTRUKCJE:
1. Typ diagramu (flowchart, UML, sieć, drzewo, etc.)
2. Główne elementy (węzły, bloki, kroki)
3. Połączenia między elementami (strzałki, linie, zależności)
4. Etykiety i tekst na diagramie (przepisz dokładnie)
5. Kierunek przepływu/informacji (np. góra-dół, lewo-prawo)
6. Logika działania (co diagram przedstawia krok po kroku)
7. Punkt startowy i końcowy (jeśli występują).

FORMAT WYJŚCIA:
Strukturyzowany opis diagramu, maksymalnie 200 słów. Jeśli to algorytm, opisz go sekwencyjnie.

Obraz do analizy:""",
)

# CHART - dla wykresów
# Prompt dla wykresów (liniowych, słupkowych, kołowych itp.).
# Nacisk na dokładność danych: typ wykresu, etykiety osi, wartości, trendy.
# Wymaga podawania konkretnych liczb – dlatego user_template zawiera instrukcję „Podaj konkretne wartości liczbowe”.
# Bezpieczeństwo: upewnij się, że model nie wymyśla danych – prompt wyraźnie prosi o te widoczne na obrazie.
CHART_PROMPT = VLMPrompt(
    name="CHART",
    system="Jesteś ekspertem w analizie wykresów i danych wizualnych. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz wykres w sposób szczegółowy i dokładny.

INSTRUKCJE:
1. Typ wykresu (liniowy, słupkowy, kołowy, punktowy, etc.)
2. Tytuł wykresu (jeśli widoczny)
3. Etykiety osi (X i Y) z jednostkami
4. Skala i zakres wartości (czy jest liniowa/logarytmiczna?)
5. Dane widoczne na wykresie (podaj konkretne wartości liczbowe dla punktów kluczowych/max/min)
6. Trendy (wzrost, spadek, stabilizacja)
7. Legenda (jeśli występuje – opisz co oznaczają kolory/ wzory)

FORMAT WYJŚCIA:
Strukturyzowany opis danych, maksymalnie 200 słów. 
Priorytet: przepisz dokładnie wartości liczbowe i daty.

Obraz do analizy:""",
)

# TABLE - dla tabel
# Prompt dla tabel – wymaga zachowania struktury danych.
# Instrukcja nakazuje przepisanie nagłówków i danych jak najdokładniej.
# Format wyjścia: opis + tabela w Markdown – to ułatwia dalsze przetwarzanie.
# Uwaga: jeśli tabela jest bardzo duża (>200 słów), prompt ogranicza długość – rozważ w przyszłości dodanie parametru do kontroli limitu.
TABLE_PROMPT = VLMPrompt(
    name="TABLE",
    system="Jesteś ekspertem w analizie tabel i danych tabelarycznych. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz tabelę w sposób precyzyjny, zachowując strukturę danych.

INSTRUKCJE:
1. Tytuł tabeli (jeśli widoczny)
2. Nagłówki kolumn (przepisz dokładnie)
3. Liczba wierszy i kolumn
4. Dane w tabeli (przepisz jak najdokładniej)
5. Scalanie komórek (jeśli występuje, opisz co to oznacza)
6. Jednostki i źródła danych (jeśli wskazane)

FORMAT WYJŚCIA:
1. Krótki opis słowny (maks. 50 słów).
2. Odtwórz tabelę w formacie Markdown poniżej.
Przykład: | Kolumna A | Kolumna B | ... |

Obraz do analizy:""",
)

# PHOTO - dla zdjęć
# Prompt dla zdjęć (fotografii) – koncentruje się na faktach, nie interpretacji.
# Instrukcja: „Opis faktyczny, bez interpretacji” – to ważne dla zachowania obiektywności.
# Wymienia elementy takie jak oświetlenie, kolory, kontekst, ale bez domysłów.
# Zgodnie z zasadą bezpieczeństwa: unikaj dodawania do promptu sugestii, które mogłyby prowadzić do błędnych wniosków.
PHOTO_PROMPT = VLMPrompt(
    name="PHOTO",
    system="Jesteś ekspertem w analizie zdjęć i fotografii. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz zdjęcie w sposób szczegółowy.

INSTRUKCJE:
1. Co przedstawia zdjęcie? (temat, scena)
2. Główne obiekty/elementy na zdjęciu (identyfikuj typ urządzenia/przedmiotu)
3. Marki, modele, numery seryjne (jeśli widoczne na obudowie/etykiecie)
4. Oświetlenie i warunki (jasne/ciemne, wewnątrz/na zewnątrz)
5. Kolory i ich znaczenie (np. kodowanie kabli)
6. Tekst widoczny na zdjęciu (napisy, szyldy, ekrany)
7. Stan obiektu (nowy/uszkodzony/zabrudzony)

FORMAT WYJŚCIA:
Opis faktyczny, bez interpretacji. Maksymalnie 200 słów.
Priorytet: identyfikacja konkretnych modeli i nazw własnych.

Obraz do analizy:""",
)

# SCREENSHOT - dla screenów UI
# Prompt dla zrzutów ekranu interfejsów użytkownika (UI).
# Specjalizacja: analiza UI – wymaga opisu elementów interfejsu, nawigacji, stanu.
# Instrukcja: tekst z ekranu podawaj w cudzysłowie – to wyróżnia go od opisu.
# Przydatne do testowania i dokumentacji UI. Jeśli modyfikujesz, pamiętaj o spójności z innymi promptami dotyczącymi tekstu.
SCREENSHOT_PROMPT = VLMPrompt(
    name="SCREENSHOT",
    system="Jesteś ekspertem w analizie interfejsów użytkownika i zrzutów ekranu. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz zrzut ekranu interfejsu użytkownika.

INSTRUKCJE:
1. Typ aplikacji/strony (desktop, mobile, web, system operacyjny)
2. Główne elementy interfejsu (menu, przyciski, panele, okna dialogowe)
3. Komunikaty błędów i ostrzeżenia (przepisz DOKŁADNIE treść komunikatu!)
4. Tekst widoczny na ekranie (przepisz istotne elementy)
5. Stan interfejsu (aktywne pola, zaznaczenia, paski postępu)
6. Nawigacja (gdzie aktualnie znajduje się użytkownik w strukturze aplikacji)

FORMAT WYJŚCIA:
Strukturyzowany opis UI, maksymalnie 200 słów.
Priorytet: dokładna treść komunikatów błędów (kluczowe dla RAG).

Obraz do analizy:""",
)

# TECHNICAL - dla schematów technicznych
# Prompt dla schematów technicznych (elektryczne, mechaniczne, budowlane).
# Wymaga precyzji: oznaczenia komponentów, wymiary, parametry, normy.
# Instrukcja: „Podawaj oznaczenia elementów” – to kluczowe dla inżynierów.
# Bezpieczeństwo: upewnij się, że prompt nie sugeruje żadnych niezgodnych z normami rozwiązań – model ma tylko opisywać, nie projektować.
TECHNICAL_PROMPT = VLMPrompt(
    name="TECHNICAL",
    system="Jesteś ekspertem w analizie schematów technicznych i inżynieryjnych. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz schemat techniczny w sposób precyzyjny.

INSTRUKCJE:
1. Typ schematu (elektryczny, hydrauliczny, mechaniczny, budowlany)
2. Główne komponenty i ich oznaczenia (R1, C2, Valve A, etc.)
3. Wymiary i parametry techniczne (jeśli widoczne)
4. Połączenia i sygnały (linie, przewody, strzałki przepływu)
5. Materiały i specyfikacje (jeśli wskazane w tabelce BOM)
6. Normy i standardy (np. PN-EN, ISO – jeśli widoczne w stopce)
7. Numer rysunku/strony (identyfikator dokumentacji)

FORMAT WYJŚCIA:
Techniczny opis, maksymalnie 200 słów.
Priorytet: oznaczenia elementów (symbol <-> nazwa) i numery części.

Obraz do analizy:""",
)

# MEDICAL - dla obrazów medycznych
# Prompt dla obrazów medycznych (RTG, USG, MRI itp.).
# Zastrzeżenie: „Unikaj diagnozowania” – to krytyczne ze względów etycznych i prawnych.
# Instrukcja nakazuje opis profesjonalny, ale bez stawiania diagnozy.
# Wymienia typ badania, region anatomiczny, struktury, nieprawidłowości (ale tylko opis, nie diagnoza).
# Zasada bezpieczeństwa: ten prompt musi być stosowany z najwyższą ostrożnością; w razie wątpliwości model powinien poprosić użytkownika o konsultację z lekarzem.
MEDICAL_PROMPT = VLMPrompt(
    name="MEDICAL",
    system="Jesteś ekspertem w analizie obrazów medycznych. Odpowiadasz wyłącznie w języku polskim.",
    user_template="""Opisz obraz medyczny w sposób profesjonalny i dokładny.

INSTRUKCJE:
1. Typ badania/obrazu (RTG, USG, MRI, tomografia, rezonans)
2. Region anatomiczny (co jest przedstawione – np. klatka piersiowa, kończyna)
3. Laterality (PRAWA/LEWA strona – kluczowe! Sprawdź znaczniki L/R na obrazie)
4. Główne struktury anatomiczne widoczne
5. Nieprawidłowości/zmiany patologiczne (zacienienia, pęknięcia, guzy)
6. Parametry techniczne (jeśli widoczne: ekspozycja, seria)
7. Dane pacjenta/ID badania (jeśli widoczne, uwaga na RODO – nie przepisuj nazwisk w opisie, tylko ID)

FORMAT WYJŚCIA:
Profesjonalny opis medyczny, maksymalnie 200 słów.
Zacznij od: "Badanie [typ] regionu [część ciała], [strona]".

Obraz do analizy:""",
)


# Słownik wszystkich promptów
PROMPTS = {
    "default": DEFAULT_PROMPT,
    "diagram": DIAGRAM_PROMPT,
    "chart": CHART_PROMPT,
    "table": TABLE_PROMPT,
    "photo": PHOTO_PROMPT,
    "screenshot": SCREENSHOT_PROMPT,
    "technical": TECHNICAL_PROMPT,
    "medical": MEDICAL_PROMPT,
}


def get_prompt(image_type: str) -> VLMPrompt:
    """
    Pobierz prompt na podstawie typu obrazu.
    
    Args:
        image_type: typ obrazu (z ExtractedImage.image_type)
    
    Returns:
        VLMPrompt dla danego typu, lub DEFAULT jeśli nieznany
    """
    return PROMPTS.get(image_type.lower(), DEFAULT_PROMPT)


def get_full_prompt(image_type: str) -> str:
    """
    Pobierz pełny prompt (system + user) dla danego typu obrazu.
    
    Args:
        image_type: typ obrazu
    
    Returns:
        Pełny prompt tekstowy
    """
    prompt = get_prompt(image_type)
    return f"{prompt.system}\n\n{prompt.user_template}"


def get_vlm_params() -> dict:
    """Pobierz parametry VLM."""
    return VLM_PARAMS.copy()
EOF

echo "Plik $TARGET został zastąpiony poprawną wersją."
