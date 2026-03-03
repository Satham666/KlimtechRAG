#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Biblioteka do ekstrakcji parametrów z plików JSONL zawierających dane o lekach.

Parametry do ekstrakcji:
- lek_id, nazwa_produktu, substancja_czynna_inn, droga_podania, moc
- postac_farmaceutyczna, podmiot_odpowiedzialny, opakowanie, substancja_czynna
- dawka_dorosli, dawka_dzieci, dawka_specjalna, wskazania, przeciwwskazania
- dzialania_niepozadane, interakcje, ciaza_karmienie, prowadzenie_pojazdow
- przedawkowanie, przechowywanie, okres_waznosci_otwarcie, sposob_przygotowania

Użycie:
    from ekstrakcja_lekow import EkstraktorLekow
    
    ekstraktor = EkstraktorLekow("/path/to/100481636.jsonl")
    nazwa = ekstraktor.nazwa_produktu()
    dawka = ekstraktor.dawka_dorosli()
"""

import os
import json
import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class WynikEkstrakcji:
    """Wynik ekstrakcji pojedynczego parametru"""
    parametr: str
    wartosc: Any
    znaleziono: bool
    zrodlo: str  # "ulotka", "charakterystyka", "metadane", "brak"


class EkstraktorLekow:
    """
    Klasa do ekstrakcji parametrów z plików JSONL zawierających dane o lekach.
    """
    
    # Mapowanie nazw sekcji w Charakterystyce (ChPL)
    SEKCJE_CHPL = {
        "nazwa": ["1. NAZWA PRODUKTU LECZNICZEGO", "1. NAZWA", "NAZWA PRODUKTU LECZNICZEGO"],
        "sklad": ["2. SKŁAD JAKOŚCIOWY I ILOŚCIOWY", "2. SKŁAD", "SKŁAD JAKOŚCIOWY I ILOŚCIOWY"],
        "postac": ["3. POSTAĆ FARMACEUTYCZNA", "3. POSTAĆ", "POSTAĆ FARMACEUTYCZNA"],
        "wskazania": ["4.1 WSKAZANIA DO STOSOWANIA", "4.1 WSKAZANIA", "WSKAZANIA DO STOSOWANIA"],
        "dawkowanie": ["4.2 DAWKOWANIE I SPOSÓB PODANIA", "4.2 DAWKOWANIE", "DAWKOWANIE I SPOSÓB PODANIA"],
        "przeciwwskazania": ["4.3 PRZECIWWSKAZANIA", "PRZECIWWSKAZANIA"],
        "ostrzezenia": ["4.4 SPECJALNE OSTRZEŻENIA I ŚRODKI OSTROŻNOŚCI", "4.4 SPECJALNE OSTRZEŻENIA"],
        "interakcje": ["4.5 INTERAKCJE Z INNYMI PRODUKTAMI LECZNICZYMI", "4.5 INTERAKCJE", "INTERAKCJE"],
        "ciaza": ["4.6 PŁODNOŚĆ, CIĄŻA I LAKTACJA", "4.6 PŁODNOŚĆ", "CIĄŻA I LAKTACJA", "CIĄŻA I KARMIENIE PIERSIĄ"],
        "pojazdy": ["4.7 WPŁYW NA ZDOLNOŚĆ PROWADZENIA POJAZDÓW", "4.7 WPŁYW NA ZDOLNOŚĆ", "WPŁYW NA ZDOLNOŚĆ PROWADZENIA"],
        "niepozadane": ["4.8 DZIAŁANIA NIEPOŻĄDANE", "DZIAŁANIA NIEPOŻĄDANE", "MOŻLIWE DZIAŁANIA NIEPOŻĄDANE"],
        "przedawkowanie": ["4.9 PRZEDAWKOWANIE", "PRZEDAWKOWANIE", "CO ZROBIĆ W PRZYPADKU PRZEDAWKOWANIA"],
        "przechowywanie": ["6.4 SPECJALNE ŚRODKI OSTROŻNOŚCI PRZY PRZECHOWYWANIU", "6.4 SPECJALNE ŚRODKI", "JAK PRZECHOWYWAĆ LEK", "PRZECHOWYWANIE"],
        "okres_waznosci": ["6.3 OKRES WAŻNOŚCI", "OKRES WAŻNOŚCI"],
        "opakowanie_chpl": ["6.5 RODZAJ I ZAWARTOŚĆ OPAKOWANIA", "6.5 RODZAJ I ZAWARTOŚĆ", "ZAWARTOŚĆ OPAKOWANIA"],
    }
    
    def __init__(self, jsonl_path: str):
        """
        Inicjalizacja ekstraktora.
        
        Args:
            jsonl_path: Ścieżka do pliku JSONL
        """
        self.jsonl_path = jsonl_path
        self.dokumenty = []
        self.metadata = {}
        self._wczytaj_jsonl()
    
    def _wczytaj_jsonl(self):
        """Wczytuje plik JSONL i parsuje dokumenty"""
        if not os.path.exists(self.jsonl_path):
            raise FileNotFoundError(f"Plik nie istnieje: {self.jsonl_path}")
        
        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                        self.dokumenty.append(doc)
                    except json.JSONDecodeError:
                        continue
        
        # Wyciągnij metadane z pierwszego dokumentu
        if self.dokumenty:
            self.metadata = self.dokumenty[0].get('metadata', {})
    
    def _znajdz_sekcje(self, tekst: str, nazwy_sekcji: List[str]) -> Optional[str]:
        """
        Znajduje treść sekcji na podstawie listy możliwych nazw.
        """
        for nazwa in nazwy_sekcji:
            # Szukaj sekcji w różnych formatach
            wzorce = [
                rf"{re.escape(nazwa)}\s*\n(.+?)(?=\n\d+\.\s|[A-Z][A-Z\s]+:?\n|$)",
                rf"{re.escape(nazwa)}[:\s]*\n(.+?)(?=\n\d+\.\s|[A-Z][A-Z\s]+:?\n|$)",
            ]
            for wzorzec in wzorce:
                match = re.search(wzorzec, tekst, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None
    
    def _czysc_tekst(self, tekst: str) -> str:
        """Czyści tekst z nadmiarowych białych znaków"""
        if not tekst:
            return ""
        # Usuń wielokrotne spacje i nowe linie
        tekst = re.sub(r'\s+', ' ', tekst)
        return tekst.strip()
    
    def _pobierz_tekst_typ(self, typ: str) -> Optional[str]:
        """Pobiera tekst dokumentu określonego typu (ulotka/charakterystyka)"""
        for doc in self.dokumenty:
            meta = doc.get('metadata', {})
            if meta.get('typ_dokumentu', '').lower() == typ.lower():
                return doc.get('content', '')
        return None
    
    # =========================================================================
    # PARAMETRY Z METADANYCH
    # =========================================================================
    
    def lek_id(self) -> WynikEkstrakcji:
        """Zwraca ID leku z metadanych"""
        lek_id = self.metadata.get('lek_id')
        if lek_id:
            return WynikEkstrakcji("lek_id", lek_id, True, "metadane")
        return WynikEkstrakcji("lek_id", None, False, "brak")
    
    # =========================================================================
    # PARAMETRY Z TEKSTU - NAZWA PRODUKTU
    # =========================================================================
    
    def nazwa_produktu(self) -> WynikEkstrakcji:
        """Ekstrahuje nazwę produktu leczniczego"""
        # Najpierw z metadanych
        nazwa = self.metadata.get('lek_nazwa')
        if nazwa:
            return WynikEkstrakcji("nazwa_produktu", nazwa, True, "metadane")
        
        # Z tekstu ulotki
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            # Szukaj w nagłówku ulotki
            match = re.search(r'ULOTKA DLA PACJENTA.*?\n([A-Z][A-Za-z0-9\s\-]+),', ulotka, re.DOTALL)
            if match:
                return WynikEkstrakcji("nazwa_produktu", match.group(1).strip(), True, "ulotka")
        
        # Z ChPL
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['nazwa'])
            if sekcja:
                # Pierwsza linia to zazwyczaj nazwa
                linia = sekcja.split('\n')[0].strip()
                return WynikEkstrakcji("nazwa_produktu", linia, True, "charakterystyka")
        
        return WynikEkstrakcji("nazwa_produktu", None, False, "brak")
    
    # =========================================================================
    # SUBSTANCJA CZYNNA
    # =========================================================================
    
    def substancja_czynna(self) -> WynikEkstrakcji:
        """Ekstrahuje nazwę substancji czynnej"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['sklad'])
            if sekcja:
                # Szukaj wzorca "Każda tabletka zawiera X mg substancji czynnej – Y"
                wzorce = [
                    r'substancj[ay]\s+czynn[ae]\s*[–\-:]?\s*([A-Za-ząćęłńóśźż\s]+)',
                    r'Każda[^.]+zawiera[^.]+–\s*([A-Za-ząćęłńóśźż\s]+)',
                    r'zawiera\s+(\d+\s*(?:mg|µg|mcg|g)\s*)\s*([A-Za-ząćęłńóśźż\s]+)',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, sekcja, re.IGNORECASE)
                    if match:
                        substancja = match.group(1) if match.lastindex == 1 else match.group(2)
                        return WynikEkstrakcji("substancja_czynna", self._czysc_tekst(substancja), True, "charakterystyka")
        
        # Z ulotki
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'Skład[^\n]*\n[^\n]*substancj[ay]\s+czynn[ae]\s*[–\-:]?\s*([A-Za-ząćęłńóśźż\s]+)', ulotka, re.IGNORECASE)
            if match:
                return WynikEkstrakcji("substancja_czynna", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("substancja_czynna", None, False, "brak")
    
    def substancja_czynna_inn(self) -> WynikEkstrakcji:
        """Ekstrahuje nazwę międzynarodową (INN) substancji czynnej"""
        # Podobne do substancja_czynna, ale szuka konkretnie INN
        wynik = self.substancja_czynna()
        if wynik.znaleziono:
            wynik.parametr = "substancja_czynna_inn"
        return wynik
    
    # =========================================================================
    # DROGA PODANIA
    # =========================================================================
    
    def droga_podania(self) -> WynikEkstrakcji:
        """Ekstrahuje drogę podania leku"""
        drogi = [
            "doustnie", "doustna", "doustny",
            "dożylnie", "dożylna", "dożylny", "dożylnie (i.v.)",
            "domięśniowo", "domięśniowa", "domięśniowy", "domięśniowo (i.m.)",
            "podskórnie", "podskórna", "podskórny", "podskórnie (s.c.)",
            "doodbytniczo", "doodbytnicza", " doodbytniczy", "rektalnie",
            "dopochwowo", "dopochwowa", "dopochwowy", "waginalnie",
            "zewnętrznie", "zewnętrzna", "zewnętrzny", "na skórę",
            "do oka", "doocznie", "dooczna",
            "do ucha", "douchnie",
            "donosowo", "donosowa", "donosowy", "do nosa",
            "wziewnie", "wziewna", "wziewny", "inhalacyjnie",
            "podjęzykowo", "podjęzykowa", "podjęzykowy",
            "transdermalnie", "przezskórnie", "na skórę w postaci plastra",
            "śródskórnie", " śródskórna",
            "doszczelinowo", "doszczelinowa",
            "dostawowo", "dostawowa",
            "zewnątrzoponowo", "zewnątrzoponowa",
            "dokanałowo", "dokanałowa",
        ]
        
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if ulotka:
            teksty.append(('ulotka', ulotka.lower()))
        if chpl:
            teksty.append(('charakterystyka', chpl.lower()))
        
        for zrodlo, tekst in teksty:
            for droga in drogi:
                if droga.lower() in tekst:
                    # Normalizuj nazwę
                    droga_norm = droga.lower().replace("a", "e").replace("y", "e")
                    if "doustn" in droga_norm or "doustn" in droga:
                        return WynikEkstrakcji("droga_podania", "doustnie", True, zrodlo)
                    if "dożyln" in droga_norm:
                        return WynikEkstrakcji("droga_podania", "dożylnie", True, zrodlo)
                    if "domięśni" in droga_norm:
                        return WynikEkstrakcji("droga_podania", "domięśniowo", True, zrodlo)
                    if "podskór" in droga_norm:
                        return WynikEkstrakcji("droga_podania", "podskórnie", True, zrodlo)
                    return WynikEkstrakcji("droga_podania", droga, True, zrodlo)
        
        return WynikEkstrakcji("droga_podania", None, False, "brak")
    
    # =========================================================================
    # MOC (DAWKA)
    # =========================================================================
    
    def moc(self) -> WynikEkstrakcji:
        """Ekstrahuje moc/dawkę leku (np. 500 mg, 1000 mg)"""
        # Z metadanych (jeśli były w nazwie)
        nazwa_wynik = self.nazwa_produktu()
        if nazwa_wynik.znaleziono:
            match = re.search(r'(\d+(?:[,.]\d+)?)\s*(mg|g|µg|mcg|ml|%|IU)', nazwa_wynik.wartosc, re.IGNORECASE)
            if match:
                return WynikEkstrakcji("moc", f"{match.group(1)} {match.group(2)}", True, "metadane")
        
        # Z tekstu
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                # Szukaj wzorca mocy w nagłówku lub składzie
                wzorce = [
                    r'(\d+(?:[,.]\d+)?)\s*(mg|g|µg|mcg|ml)%?\s*(?:tabletk[ai]|kapsułk[ai]|roztwór|żel|maść)',
                    r'Każda[^.]+zawiera\s+(\d+(?:[,.]\d+)?)\s*(mg|g|µg|mcg|ml)',
                    r'moc[^\d]*(\d+(?:[,.]\d+)?)\s*(mg|g|µg|mcg|ml)',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE)
                    if match:
                        return WynikEkstrakcji("moc", f"{match.group(1)} {match.group(2)}", True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("moc", None, False, "brak")
    
    # =========================================================================
    # POSTAĆ FARMACEUTYCZNA
    # =========================================================================
    
    def postac_farmaceutyczna(self) -> WynikEkstrakcji:
        """Ekstrahuje postać farmaceutyczną leku"""
        postacie = [
            ("tabletka", ["tabletka", "tabletki", "tabletkach"]),
            ("tabletka powlekana", ["tabletka powlekana", "tabletki powlekane"]),
            ("tabletka drażowana", ["tabletka drażowana", "tabletki drażowane"]),
            ("kapsułka twarda", ["kapsułka twarda", "kapsułki twarde"]),
            ("kapsułka miękka", ["kapsułka miękka", "kapsułki miękkie"]),
            ("żel", ["żel", "żelem"]),
            ("maść", ["maść", "maścią", "maści"]),
            ("krem", ["krem", "kremem"]),
            ("roztwór", ["roztwór", "roztworem", "roztworu"]),
            ("zawiesina", ["zawiesina", "zawiesiną", "zawiesiny"]),
            ("syrop", ["syrop", "syropem"]),
            ("czopek", ["czopek", "czopki", "czopków"]),
            ("aerozol", ["aerozol", "aerozolem"]),
            ("spray", ["spray", "sprayem"]),
            ("plaster", ["plaster", "plastry", "plastrem"]),
            ("krople", ["krople", "kroplami"]),
            ("granulat", ["granulat", "granulatem"]),
            ("proszek", ["proszek", "proszkiem", "proszku"]),
            ("ampułka", ["ampułka", "ampułki"]),
        ]
        
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if ulotka:
            teksty.append(('ulotka', ulotka.lower()))
        if chpl:
            teksty.append(('charakterystyka', chpl.lower()))
        
        for zrodlo, tekst in teksty:
            for postac_norm, warianty in postacie:
                for wariant in warianty:
                    if wariant in tekst:
                        return WynikEkstrakcji("postac_farmaceutyczna", postac_norm, True, zrodlo)
        
        return WynikEkstrakcji("postac_farmaceutyczna", None, False, "brak")
    
    # =========================================================================
    # PODMIOT ODPOWIEDZIALNY
    # =========================================================================
    
    def podmiot_odpowiedzialny(self) -> WynikEkstrakcji:
        """Ekstrahuje nazwę podmiotu odpowiedzialnego"""
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                # Szukaj sekcji podmiot odpowiedzialny
                wzorce = [
                    r'Podmiot odpowiedzialny[:\s]+([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9\s\-\.]+?)(?:\n|$|Wytwórca)',
                    r'PODMIOT ODPOWIEDZIALNY[:\s]+([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9\s\-\.]+?)(?:\n|$)',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE)
                    if match:
                        nazwa = self._czysc_tekst(match.group(1))
                        if len(nazwa) > 3:
                            return WynikEkstrakcji("podmiot_odpowiedzialny", nazwa, True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("podmiot_odpowiedzialny", None, False, "brak")
    
    # =========================================================================
    # OPAKOWANIE
    # =========================================================================
    
    def opakowanie(self) -> WynikEkstrakcji:
        """Ekstrahuje informację o opakowaniu"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['opakowanie_chpl'])
            if sekcja:
                return WynikEkstrakcji("opakowanie", self._czysc_tekst(sekcja[:200]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'ZAWARTOŚĆ OPAKOWANIA[^\n]*\n(.{20,200})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("opakowanie", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("opakowanie", None, False, "brak")
    
    # =========================================================================
    # DAWKOWANIE DLA DOROSŁYCH
    # =========================================================================
    
    def dawka_dorosli(self) -> WynikEkstrakcji:
        """Ekstrahuje dawkowanie dla dorosłych"""
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                # Szukaj sekcji dawkowanie
                wzorce = [
                    r'(?:Dorośli|Dorosli)[^.]*(?::\s*|–\s*|-{1,2}\s*)([^.]{10,300})',
                    r'Dawkowanie[^.]*Dorośli[^.]*[.:]\s*([^.]{10,300})',
                    r'JAK STOSOWAĆ[^.]*Dorośli[^.]*[.:]\s*([^.]{10,300})',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE | re.DOTALL)
                    if match:
                        return WynikEkstrakcji("dawka_dorosli", self._czysc_tekst(match.group(1)), True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("dawka_dorosli", None, False, "brak")
    
    # =========================================================================
    # DAWKOWANIE DLA DZIECI
    # =========================================================================
    
    def dawka_dzieci(self) -> WynikEkstrakcji:
        """Ekstrahuje dawkowanie dla dzieci"""
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                # Szukaj sekcji dla dzieci
                wzorce = [
                    r'(?:Dzieci|Dziecka|Dzieciom)[^.]*(?::\s*|–\s*|-{1,2}\s*)([^.]{10,400})',
                    r'Stosowanie u dzieci[^.]*[.:]\s*([^.]{10,400})',
                    r'Populacja pediatryczna[^.]*[.:]\s*([^.]{10,400})',
                    r'(\d+[\s,-]*(?:mg|µg|mcg)/kg[^.]{10,200})',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE | re.DOTALL)
                    if match:
                        return WynikEkstrakcji("dawka_dzieci", self._czysc_tekst(match.group(1)), True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("dawka_dzieci", None, False, "brak")
    
    # =========================================================================
    # DAWKOWANIE SPECJALNE
    # =========================================================================
    
    def dawka_specjalna(self) -> WynikEkstrakcji:
        """Ekstrahuje dawkowanie dla grup specjalnych (niewydolność nerek/wątroby, osoby starsze)"""
        wyniki = []
        
        chpl = self._pobierz_tekst_typ('charakterystyka')
        ulotka = self._pobierz_tekst_typ('ulotka')
        
        for tekst in [chpl, ulotka]:
            if tekst:
                # Szukaj informacji o grupach specjalnych
                wzorce = [
                    (r'(?:Osoby w podeszłym wieku|Pacjenci w podeszłym wieku)[^.]*[.:]\s*([^.]{10,300})', "osoby_starsze"),
                    (r'(?:Niewydolność nerek|Zaburzenia nerek)[^.]*[.:]\s*([^.]{10,300})', "niewydolnosc_nerek"),
                    (r'(?:Niewydolność wątroby|Zaburzenia wątroby)[^.]*[.:]\s*([^.]{10,300})', "niewydolnosc_watroby"),
                ]
                for wzorzec, typ in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE | re.DOTALL)
                    if match:
                        wyniki.append(f"{typ}: {self._czysc_tekst(match.group(1))}")
        
        if wyniki:
            return WynikEkstrakcji("dawka_specjalna", "; ".join(wyniki), True, "charakterystyka")
        
        return WynikEkstrakcji("dawka_specjalna", None, False, "brak")
    
    # =========================================================================
    # WSKAZANIA
    # =========================================================================
    
    def wskazania(self) -> WynikEkstrakcji:
        """Ekstrahuje wskazania do stosowania"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['wskazania'])
            if sekcja:
                return WynikEkstrakcji("wskazania", self._czysc_tekst(sekcja[:500]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'WSKAZANIA DO STOSOWANIA[^\n]*\n(.{20,500})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("wskazania", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("wskazania", None, False, "brak")
    
    # =========================================================================
    # PRZECIWWSKAZANIA
    # =========================================================================
    
    def przeciwwskazania(self) -> WynikEkstrakcji:
        """Ekstrahuje przeciwwskazania"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['przeciwwskazania'])
            if sekcja:
                return WynikEkstrakcji("przeciwwskazania", self._czysc_tekst(sekcja[:500]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'KIEDY NIE STOSOWAĆ[^\n]*\n(.{20,500})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("przeciwwskazania", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("przeciwwskazania", None, False, "brak")
    
    # =========================================================================
    # DZIAŁANIA NIEPOŻĄDANE
    # =========================================================================
    
    def dzialania_niepozadane(self) -> WynikEkstrakcji:
        """Ekstrahuje informacje o działaniach niepożądanych"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['niepozadane'])
            if sekcja:
                return WynikEkstrakcji("dzialania_niepozadane", self._czysc_tekst(sekcja[:800]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'MOŻLIWE DZIAŁANIA NIEPOŻĄDANE[^\n]*\n(.{20,800})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("dzialania_niepozadane", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("dzialania_niepozadane", None, False, "brak")
    
    # =========================================================================
    # INTERAKCJE
    # =========================================================================
    
    def interakcje(self) -> WynikEkstrakcji:
        """Ekstrahuje informacje o interakcjach z innymi lekami"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['interakcje'])
            if sekcja:
                return WynikEkstrakcji("interakcje", self._czysc_tekst(sekcja[:500]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'STOSOWANIE LEKU.*?INNYMI LEKAMI[^\n]*\n(.{20,500})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("interakcje", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("interakcje", None, False, "brak")
    
    # =========================================================================
    # CIĄŻA I KARMIENIE
    # =========================================================================
    
    def ciaza_karmienie(self) -> WynikEkstrakcji:
        """Ekstrahuje informacje dotyczące ciąży i karmienia piersią"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['ciaza'])
            if sekcja:
                return WynikEkstrakcji("ciaza_karmienie", self._czysc_tekst(sekcja[:500]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'CIĄŻA.*?KARMIENIE[^\n]*\n(.{20,500})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("ciaza_karmienie", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("ciaza_karmienie", None, False, "brak")
    
    # =========================================================================
    # PROWADZENIE POJAZDÓW
    # =========================================================================
    
    def prowadzenie_pojazdow(self) -> WynikEkstrakcji:
        """Ekstrahuje informacje o wpływie na prowadzenie pojazdów"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['pojazdy'])
            if sekcja:
                return WynikEkstrakcji("prowadzenie_pojazdow", self._czysc_tekst(sekcja[:300]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'Wpływ na zdolność prowadzenia[^\n]*\n(.{20,300})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("prowadzenie_pojazdow", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("prowadzenie_pojazdow", None, False, "brak")
    
    # =========================================================================
    # PRZEDAWKOWANIE
    # =========================================================================
    
    def przedawkowanie(self) -> WynikEkstrakcji:
        """Ekstrahuje informacje o przedawkowaniu"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['przedawkowanie'])
            if sekcja:
                return WynikEkstrakcji("przedawkowanie", self._czysc_tekst(sekcja[:500]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'CO ZROBIĆ W PRZYPADKU PRZEDAWKOWANIA[^\n]*\n(.{20,500})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("przedawkowanie", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("przedawkowanie", None, False, "brak")
    
    # =========================================================================
    # PRZECHOWYWANIE
    # =========================================================================
    
    def przechowywanie(self) -> WynikEkstrakcji:
        """Ekstrahuje warunki przechowywania"""
        chpl = self._pobierz_tekst_typ('charakterystyka')
        if chpl:
            sekcja = self._znajdz_sekcje(chpl, self.SEKCJE_CHPL['przechowywanie'])
            if sekcja:
                return WynikEkstrakcji("przechowywanie", self._czysc_tekst(sekcja[:300]), True, "charakterystyka")
        
        ulotka = self._pobierz_tekst_typ('ulotka')
        if ulotka:
            match = re.search(r'JAK PRZECHOWYWAĆ[^\n]*\n(.{20,300})', ulotka, re.IGNORECASE | re.DOTALL)
            if match:
                return WynikEkstrakcji("przechowywanie", self._czysc_tekst(match.group(1)), True, "ulotka")
        
        return WynikEkstrakcji("przechowywanie", None, False, "brak")
    
    # =========================================================================
    # OKRES WAŻNOŚCI PO OTWARCIU
    # =========================================================================
    
    def okres_waznosci_otwarcie(self) -> WynikEkstrakcji:
        """Ekstrahuje okres ważności po otwarciu opakowania"""
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                wzorce = [
                    r'po otwarciu[^.]{5,100}(?:dni|miesiący|tygodnie)',
                    r'zużyć w ciągu[^.]{5,100}(?:dni|miesiący|tygodnie)',
                    r'okres ważności[^.]*otwarci[^.]{10,150}',
                    r'po pierwszym otwarciu[^.]{10,150}',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE)
                    if match:
                        return WynikEkstrakcji("okres_waznosci_otwarcie", self._czysc_tekst(match.group(0)), True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("okres_waznosci_otwarcie", None, False, "brak")
    
    # =========================================================================
    # SPOSÓB PRZYGOTOWANIA
    # =========================================================================
    
    def sposob_przygotowania(self) -> WynikEkstrakcji:
        """Ekstrahuje sposób przygotowania leku (dla proszków, granulatów itp.)"""
        teksty = []
        ulotka = self._pobierz_tekst_typ('ulotka')
        chpl = self._pobierz_tekst_typ('charakterystyka')
        
        for tekst in [ulotka, chpl]:
            if tekst:
                wzorce = [
                    r'Sposób przygotowania[^.]*[.:]\s*([^.]{20,300})',
                    r'Przygotowanie[^.]*roztworu[^.]*[.:]\s*([^.]{20,300})',
                    r'rozpuścić[^.]{10,200}(?:wodzie|wodzie|wodzie)',
                    r'rozpuszcz[^.]{10,200}',
                ]
                for wzorzec in wzorce:
                    match = re.search(wzorzec, tekst, re.IGNORECASE | re.DOTALL)
                    if match:
                        return WynikEkstrakcji("sposob_przygotowania", self._czysc_tekst(match.group(1) if match.lastindex else match.group(0)), True, "ulotka" if tekst == ulotka else "charakterystyka")
        
        return WynikEkstrakcji("sposob_przygotowania", None, False, "brak")
    
    # =========================================================================
    # METODA UNIWERSALNA
    # =========================================================================
    
    def ekstrahuj(self, parametr: str) -> WynikEkstrakcji:
        """
        Uniwersalna metoda do ekstrakcji parametru po nazwie.
        
        Args:
            parametr: Nazwa parametru do ekstrakcji
            
        Returns:
            WynikEkstrakcji z wynikiem
        """
        metody = {
            'lek_id': self.lek_id,
            'nazwa_produktu': self.nazwa_produktu,
            'substancja_czynna': self.substancja_czynna,
            'substancja_czynna_inn': self.substancja_czynna_inn,
            'droga_podania': self.droga_podania,
            'moc': self.moc,
            'postac_farmaceutyczna': self.postac_farmaceutyczna,
            'podmiot_odpowiedzialny': self.podmiot_odpowiedzialny,
            'opakowanie': self.opakowanie,
            'dawka_dorosli': self.dawka_dorosli,
            'dawka_dzieci': self.dawka_dzieci,
            'dawka_specjalna': self.dawka_specjalna,
            'wskazania': self.wskazania,
            'przeciwwskazania': self.przeciwwskazania,
            'dzialania_niepozadane': self.dzialania_niepozadane,
            'interakcje': self.interakcje,
            'ciaza_karmienie': self.ciaza_karmienie,
            'prowadzenie_pojazdow': self.prowadzenie_pojazdow,
            'przedawkowanie': self.przedawkowanie,
            'przechowywanie': self.przechowywanie,
            'okres_waznosci_otwarcie': self.okres_waznosci_otwarcie,
            'sposob_przygotowania': self.sposob_przygotowania,
        }
        
        metoda = metody.get(parametr.lower())
        if metoda:
            return metoda()
        
        return WynikEkstrakcji(parametr, None, False, "brak")


# =============================================================================
# FUNKCJA POMOCNICZA
# =============================================================================

def list_dostepne_parametry() -> List[str]:
    """Zwraca listę wszystkich dostępnych parametrów do ekstrakcji"""
    return [
        'lek_id',
        'nazwa_produktu',
        'substancja_czynna',
        'substancja_czynna_inn',
        'droga_podania',
        'moc',
        'postac_farmaceutyczna',
        'podmiot_odpowiedzialny',
        'opakowanie',
        'dawka_dorosli',
        'dawka_dzieci',
        'dawka_specjalna',
        'wskazania',
        'przeciwwskazania',
        'dzialania_niepozadane',
        'interakcje',
        'ciaza_karmienie',
        'prowadzenie_pojazdow',
        'przedawkowanie',
        'przechowywanie',
        'okres_waznosci_otwarcie',
        'sposob_przygotowania',
    ]


if __name__ == "__main__":
    # Test biblioteki
    import sys
    
    if len(sys.argv) < 2:
        print("Użycie: python ekstrakcja_lekow.py <plik.jsonl> [parametr1] [parametr2] ...")
        print(f"\nDostępne parametry: {', '.join(list_dostepne_parametry())}")
        sys.exit(1)
    
    jsonl_path = sys.argv[1]
    parametry = sys.argv[2:] if len(sys.argv) > 2 else list_dostepne_parametry()
    
    try:
        ekstraktor = EkstraktorLekow(jsonl_path)
        
        for parametr in parametry:
            wynik = ekstraktor.ekstrahuj(parametr)
            if wynik.znaleziono:
                print(f"\n{wynik.parametr}:")
                print(f"  {wynik.wartosc}")
                print(f"  [źródło: {wynik.zrodlo}]")
            else:
                print(f"\n{wynik.parametr}: Nie znaleziono")
    
    except FileNotFoundError as e:
        print(f"Błąd: {e}")
    except Exception as e:
        print(f"Błąd: {e}")

