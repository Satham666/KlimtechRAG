---
name: klimtech-git-release
description: Protokół zamknięcia sesji KlimtechRAG i tworzenia GitHub Release. Uruchom gdy użytkownik napisze "na dzisiaj koniec", "kończymy" lub "zamykamy sesję". Obejmuje podsumowanie zmian, weryfikację check_project.sh i komendę gh release create.
compatibility: opencode
metadata:
  project: KlimtechRAG
  phase: session-end
---

# klimtech-git-release — Zamknięcie Sesji i GitHub Release

## Trigger

Uruchom tę skill gdy użytkownik napisze:
- „na dzisiaj koniec"
- „kończymy"
- „zamykamy sesję"
- „zrób release"

---

## Checklist zamknięcia sesji — wykonaj w kolejności

### [ ] 1. Podsumowanie zmian sesji

Wygeneruj listę:
- Które pliki zostały zmienione i dlaczego
- Co zostało zrobione (ukończone funkcje, poprawki, refaktoring)
- Co pozostało nierozwiązane
- Rekomendacja dla następnej sesji

---

### [ ] 2. Weryfikacja git status

```bash
git status
git log --oneline -5
```

Upewnij się, że wszystkie zmiany są commitowane i spushowane.
Jeśli nie → przypomnij użytkownikowi o pushu (push wykonuje **użytkownik ręcznie**).

```bash
# Użytkownik wykonuje ręcznie w osobnym terminalu:
git add -A && git commit -m "feat: [opis zmian sesji]" && git push --force
```

---

### [ ] 3. Uruchom check_project.sh

```bash
bash scripts/check_project.sh
```

Zapisz wynik w formacie: `PASS: X | WARN: X | FAIL: X`
Ten wynik trafi do release notes.

---

### [ ] 4. Ustal numer wersji

```bash
git tag --sort=-v:refname | head -5
gh release list --limit 5
```

Format wersji: `vMAJOR.MINOR`
- MAJOR zmienia się przy przebudowie architektury lub dużym milestonie
- MINOR inkrementuj o 1 po każdej sesji z realnymi zmianami kodu

---

### [ ] 5. Utwórz GitHub Release

Przygotuj komendę do skopiowania przez użytkownika:

```bash
gh release create vX.Y \
  --title "vX.Y — [krótki opis sesji]" \
  --notes "## Zmiany w tej sesji

### Pliki zmienione
- [plik1] — [co zmieniono]
- [plik2] — [co zmieniono]

### Co zrobiono
- [punkt 1]
- [punkt 2]

### Nierozwiązane / następna sesja
- [punkt 1]

### Wynik check_project.sh
PASS: X | WARN: X | FAIL: X"
```

---

## Zasady numerowania wersji

| Sytuacja | Akcja |
|---|---|
| Przebudowa architektury, duży milestone | Bump MAJOR (np. v7 → v8) |
| Normalna sesja z realnymi zmianami kodu | Bump MINOR (np. v7.4 → v7.5) |
| Sesja bez zmian kodu (tylko planowanie) | Bez release |

---

## Czego NIE przechowywać w katalogu projektu

```
❌ Pliki logów sesji (.log z rozmów)   → tylko GitHub Release notes
❌ Notatki tymczasowe z analizy        → tylko GitHub Release notes
❌ Eksporty sesji jako .md w root      → tylko GitHub Release notes
✅ logs/ (wynik check_project.sh)      → .gitignore, nie trafia do repo
```

---

## Eksport z OpenCode przed release

Jeśli pracujesz w OpenCode:
```
/export
```
Skopiuj wygenerowaną treść do pola `--notes` w komendzie `gh release create`.

---

## Git Workflow — przypomnienie

```bash
# Checklist przed git push (użytkownik):
# [ ] bash scripts/check_project.sh — wszystkie PASS/WARN (nie pushuj gdy FAIL)
# [ ] Brak backticks (`) w JS osadzonym w Python strings
# [ ] Brak heredoc (cat << 'EOF') — fish shell nie obsługuje
# [ ] Brak hardcoded ścieżek /home/tamiel/
# [ ] .env nie jest w staged files
# [ ] Sensowny komunikat commita
```

**Zasada nadrzędna:** Kod edytowany ZAWSZE na laptopie (tamiel@hall8000).
Nigdy bezpośrednio na serwerze (lobo@hall9000).
