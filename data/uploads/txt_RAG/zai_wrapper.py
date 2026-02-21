#!/usr/bin/env python3
import sys
import os
from zai import ZaiClient

# Pobieramy zapytanie z argumentu linii poleceń
if len(sys.argv) < 2:
    print("Błąd: Brak zapytania. Użycie: python zai_wrapper.py 'Twoje pytanie'")
    sys.exit(1)

query = sys.argv[1]

# Pobieramy klucz API ze zmiennych środowiskowych (bezpieczniejsze niż wpisywanie w kodzie)
api_key = os.getenv("ZAI_API_KEY")

if not api_key:
    print("Błąd: Brak zmiennej środowiskowej ZAI_API_KEY.")
    print("Ustaw ją: export ZAI_API_KEY='twój-klucz'")
    sys.exit(1)

try:
    # Inicjalizacja klienta (zgodnie z dokumentacją)
    client = ZaiClient(api_key=api_key)

    # Wywołanie modelu (zgodnie z docs: glm-4.7)
    response = client.chat.completions.create(
        model="glm-4.7",
        messages=[
            {
                "role": "system",
                "content": "Jesteś pomocnym asystentem AI specjalizującym się w technologiach."
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )

    # Wypisanie czystego tekstu odpowiedzi
    print(response.choices[0].message.content)

except Exception as e:
    print(f"Błąd API: {e}")
