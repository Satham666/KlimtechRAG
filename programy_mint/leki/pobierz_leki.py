#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt do pobierania informacji o lekach z rejestru e-Zdrowie

Funkcjonalności:
1. Pobieranie aktualnej bazy leków w formacie XLSX z API
2. Wyszukiwanie leków po nazwie
3. Pobieranie ulotek i charakterystyk w formacie PDF
4. Ekstrakcja tekstu z PDF do formatu JSONL przyjaznego dla LLM
"""

import os
import sys
import json
import re
import requests
import pandas as pd
import fitz  # PyMuPDF
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# Import biblioteki ekstrakcji parametrów z JSONL
try:
    from ekstrakcja_lekow import EkstraktorLekow, list_dostepne_parametry
except ImportError:
    EkstraktorLekow = None
    list_dostepne_parametry = None


# ============================================================================
# KONFIGURACJA
# ============================================================================

# URL do pobierania bazy leków (codziennie aktualizowany)
XLSX_DOWNLOAD_URL = "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/public-pl-report/get-xlsx"

# Bazowy URL do pobierania dokumentów PDF
API_BASE_URL = "https://rejestrymedyczne.ezdrowie.gov.pl/api/rpl/medicinal-products"

# Domyślna ścieżka do zapisu bazy leków (XLSX)
DEFAULT_OUTPUT_DIR = "/home/tamiel/Baza_leków"

# Domyślna ścieżka do zapisu plików PDF i JSONL
DEFAULT_PDF_DIR = "/home/tamiel/Baza_leków_pdf"

# Timeout dla requestów (sekundy)
REQUEST_TIMEOUT = 120

# Headers dla requestów
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/octet-stream, */*",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


# ============================================================================
# KLASY DANYCH
# ============================================================================

@dataclass
class LekInfo:
    """Informacje o leku z rejestru"""
    id: Optional[int] = None
    nazwa: str = ""
    nazowna_powszechnie_stosowana: str = ""
    postac: str = ""
    dawka: str = ""
    podmiot_odpowiedzialny: str = ""
    numer_pozwolenia: str = ""
    termin_waznosci: str = ""
    kod_atc: str = ""
    status: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DokumentPDF:
    """Dokument PDF z ekstrahowanym tekstem"""
    typ: str  # "ulotka" lub "charakterystyka"
    lek_id: int
    lek_nazwa: str
    url_zrodlo: str
    tekst: str
    data_pobrania: str
    liczba_stron: int = 0
    
    def to_jsonl(self) -> str:
        """Konwertuje do formatu JSONL przyjaznego dla LLM"""
        record = {
            "metadata": {
                "typ_dokumentu": self.typ,
                "lek_id": self.lek_id,
                "lek_nazwa": self.lek_nazwa,
                "url_zrodlo": self.url_zrodlo,
                "data_pobrania": self.data_pobrania,
                "liczba_stron": self.liczba_stron,
            },
            "content": self.tekst
        }
        return json.dumps(record, ensure_ascii=False)


# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def sanitize_filename(name: str) -> str:
    """Czyści nazwę pliku z niedozwolonych znaków"""
    # Usuń lub zamień niedozwolone znaki
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Ogranicz długość
    return cleaned[:100].strip()


def ensure_dir(path: str) -> Path:
    """Tworzy katalog jeśli nie istnieje"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def print_separator(char: str = "=", length: int = 60):
    """Drukuje separator"""
    print(char * length)


# ============================================================================
# POBIERANIE BAZY LEKÓW (XLSX)
# ============================================================================

def pobierz_baze_lekow(output_dir: str = None, force_download: bool = False) -> str:
    """
    Pobiera aktualną bazę leków w formacie XLSX z API e-Zdrowie
    
    Args:
        output_dir: Katalog do zapisu pliku (domyślnie DEFAULT_OUTPUT_DIR)
        force_download: Wymuś pobranie nawet jeśli plik już istnieje
    
    Returns:
        Ścieżka do pobranego pliku XLSX
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    ensure_dir(output_dir)
    
    # Sprawdź czy już istnieje dzisiejszy plik
    today = datetime.now().strftime("%Y%m%d")
    today_file = os.path.join(output_dir, f"rejestr_lekow_{today}.xlsx")
    
    if os.path.exists(today_file) and not force_download:
        print(f"✓ Plik z dzisiaj już istnieje: {today_file}")
        return today_file
    
    print(f"Pobieranie bazy leków z: {XLSX_DOWNLOAD_URL}")
    print("To może potrwać kilka minut...")
    
    try:
        response = requests.get(
            XLSX_DOWNLOAD_URL, 
            headers=HEADERS, 
            timeout=REQUEST_TIMEOUT,
            stream=True
        )
        response.raise_for_status()
        
        # Pobierz nazwę pliku z nagłówka Content-Disposition lub użyj domyślnej
        content_disp = response.headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disp)
        
        if filename_match:
            original_filename = filename_match.group(1).strip('\'"')
            # Zapisz z oryginalną nazwą
            output_path = os.path.join(output_dir, original_filename)
        else:
            output_path = today_file
        
        # Zapisz plik
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"\rPostęp: {percent:.1f}%", end="", flush=True)
        
        print(f"\n✓ Pobrano plik: {output_path}")
        return output_path
        
    except requests.exceptions.Timeout:
        raise Exception("Timeout podczas pobierania - serwer nie odpowiada")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Błąd podczas pobierania: {e}")


# ============================================================================
# WCZYTYWANIE I WYSZUKIWANIE W PLIKU XLSX
# ============================================================================

def wczytaj_baze_lekow(xlsx_path: str) -> pd.DataFrame:
    """
    Wczytuje bazę leków z pliku XLSX
    
    Args:
        xlsx_path: Ścieżka do pliku XLSX
    
    Returns:
        DataFrame z danymi o lekach
    """
    print(f"Wczytywanie bazy leków z: {xlsx_path}")
    
    try:
        df = pd.read_excel(xlsx_path)
        print(f"✓ Wczytano {len(df)} rekordów")
        print(f"  Dostępne kolumny: {list(df.columns)}")
        return df
    except Exception as e:
        raise Exception(f"Błąd podczas wczytywania pliku: {e}")


def mapuj_kolumny(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapuje nazwy kolumn z pliku na standardowe nazwy używane w programie
    
    Obsługuje różne warianty nazw kolumn w plikach z rejestru
    """
    # Mapowanie możliwych nazw kolumn (dokładne dopasowanie ma priorytet)
    column_mapping = {
        # ID leku - dokładne nazwy z pliku
        'Identyfikator Produktu Leczniczego': 'id',
        'Id': 'id',
        'ID': 'id',
        'id': 'id',
        'Identyfikator': 'id',
        
        # Nazwa produktu - dokładne nazwy z pliku
        'Nazwa Produktu Leczniczego': 'nazwa',
        'Nazwa produktu leczniczego': 'nazwa',
        'Nazwa': 'nazwa',
        'NazwaProduktu': 'nazwa',
        
        # Nazwa powszechnie stosowana - dokładna nazwa z pliku
        'Nazwa powszechnie stosowana': 'nazwa_powszechna',
        
        # Postać farmaceutyczna
        'Postać farmaceutyczna': 'postac',
        'Postać': 'postac',
        'Postac': 'postac',
        
        # Dawka/Moc
        'Moc': 'dawka',
        'Dawka': 'dawka',
        
        # Podmiot odpowiedzialny - dokładna nazwa z pliku
        'Podmiot odpowiedzialny': 'podmiot_odpowiedzialny',
        
        # Numer pozwolenia - dokładna nazwa z pliku
        'Numer pozwolenia': 'numer_pozwolenia',
        
        # Ważność pozwolenia
        'Ważność pozwolenia': 'termin_waznosci',
        
        # Kod ATC - dokładna nazwa z pliku
        'Kod ATC': 'kod_atc',
        
        # Substancja czynna
        'Substancja czynna': 'substancja_czynna',
        
        # Status (nie ma w aktualnym pliku, ale może być w innych)
        'Status': 'status',
        'Stan': 'status',
    }
    
    # Najpierw spróbuj dokładnego dopasowania
    renamed = {}
    for col in df.columns:
        if col in column_mapping:
            renamed[col] = column_mapping[col]
    
    # Jeśli nie znaleziono dokładnego dopasowania, spróbuj fuzzy
    if not renamed:
        for col in df.columns:
            for key, value in column_mapping.items():
                if key.lower() in col.lower() or col.lower() in key.lower():
                    renamed[col] = value
                    break
    
    if renamed:
        df = df.rename(columns=renamed)
    
    return df


def szukaj_lekow(df: pd.DataFrame, fraza: str, kolumna: str = None) -> pd.DataFrame:
    """
    Wyszukuje leki zawierające podaną frazę w nazwie
    
    Args:
        df: DataFrame z danymi o lekach
        fraza: Fraza do wyszukania
        kolumna: Konkretna kolumna do przeszukania (domyślnie wszystkie tekstowe)
    
    Returns:
        DataFrame z pasującymi lekami
    """
    fraza_lower = fraza.lower().strip()
    
    # Jeśli nie określono kolumny, szukaj we wszystkich tekstowych
    if kolumna is None:
        # Szukaj w kolumnach tekstowych - użyj select_dtypes dla bezpieczeństwa
        mask = pd.Series([False] * len(df), index=df.index)
        
        # Wybierz tylko kolumny tekstowe (object i string)
        tekstowe_kolumny = df.select_dtypes(include=['object', 'string']).columns
        
        for col in tekstowe_kolumny:
            try:
                col_mask = df[col].astype(str).str.lower().str.contains(fraza_lower, na=False)
                mask = mask | col_mask
            except Exception:
                continue  # Pomiń problematyczne kolumny
    else:
        # Szukaj w konkretnej kolumnie
        if kolumna in df.columns:
            mask = df[kolumna].astype(str).str.lower().str.contains(fraza_lower, na=False)
        else:
            print(f"⚠ Kolumna '{kolumna}' nie istnieje. Dostępne: {list(df.columns)}")
            return pd.DataFrame()
    
    wyniki = df[mask]
    
    return wyniki


# ============================================================================
# KONWERSJA ID LEKU
# ============================================================================

def konwertuj_id_leku(xlsx_id: int) -> int:
    """
    Konwertuje ID z pliku XLSX na ID używane w API e-Zdrowie
    
    ID w pliku XLSX ma format: 100XXXXXX (9 cyfr)
    ID dla API to środkowa część: znaki 3-7 (5 cyfr)
    
    Przykład: 100481636 → 48163
    
    Args:
        xlsx_id: ID z pliku XLSX
        
    Returns:
        ID do użycia w API
    """
    id_str = str(xlsx_id)
    
    # Jeśli ID ma 9 cyfr i zaczyna się od "100", wyciągnij środkową część
    if len(id_str) == 9 and id_str.startswith('100'):
        api_id = int(id_str[3:8])
        return api_id
    
    # Jeśli ID ma już 5 cyfr, prawdopodobnie jest to już ID API
    if len(id_str) == 5:
        return int(xlsx_id)
    
    # W przeciwnym razie zwróć oryginalne ID
    return int(xlsx_id)


def wyswietl_wyniki(df: pd.DataFrame, max_rows: int = 20):
    """
    Wyświetla wyniki wyszukiwania w czytelnej formie
    Zwraca listę indeksów w kolejności wyświetlania (1, 2, 3...)
    """
    if df.empty:
        print("Nie znaleziono pasujących leków.")
        return []
    
    print(f"\nZnaleziono {len(df)} pasujących leków:")
    print_separator("-")
    
    # Wybierz kolumny do wyświetlenia
    display_cols = ['id', 'nazwa', 'postac', 'dawka', 'podmiot_odpowiedzialny', 'numer_pozwolenia']
    available_cols = [col for col in display_cols if col in df.columns]
    
    if not available_cols:
        available_cols = df.columns[:6].tolist()
    
    # Lista indeksów w kolejności wyświetlania
    idx_list = []
    
    for display_num, (df_idx, row) in enumerate(df.head(max_rows).iterrows(), 1):
        idx_list.append(df_idx)
        print(f"\n{display_num}.")  # Numerujemy od 1
        for col in available_cols:
            val = row.get(col, 'N/A')
            if pd.notna(val):
                # Jeśli to kolumna ID, pokaż też ID dla API
                if col == 'id':
                    api_id = konwertuj_id_leku(int(val))
                    if api_id != int(val):
                        print(f"   ID: {val} (API: {api_id})")
                    else:
                        print(f"   ID: {val}")
                else:
                    print(f"   {col}: {val}")
    
    if len(df) > max_rows:
        print(f"\n... i kolejne {len(df) - max_rows} wyników")
    
    return idx_list


# ============================================================================
# POBIERANIE PDF Z API
# ============================================================================

def pobierz_pdf(lek_id: int, typ: str, xlsx_id: int, output_dir: str = None) -> Optional[str]:
    """
    Pobiera PDF (ulotkę lub charakterystykę) dla leku o podanym ID
    
    Args:
        lek_id: ID leku do API
        typ: Typ dokumentu - "ulotka" lub "charakterystyka"
        xlsx_id: ID leku z pliku XLSX (do nazwy pliku)
        output_dir: Katalog do zapisu PDF (nieużywane, zachowane dla kompatybilności)
    
    Returns:
        Ścieżka do pobranego pliku PDF lub None w przypadku błędu
    """
    # Użyj domyślnego folderu PDF
    pdf_dir = DEFAULT_PDF_DIR
    ensure_dir(pdf_dir)
    
    # Mapowanie typów na endpointy
    endpoint_map = {
        "ulotka": "leaflet",
        "charakterystyka": "characteristic",
        "leaflet": "leaflet",
        "characteristic": "characteristic"
    }
    
    endpoint = endpoint_map.get(typ.lower())
    if not endpoint:
        print(f"⚠ Nieznany typ dokumentu: {typ}")
        return None
    
    url = f"{API_BASE_URL}/{lek_id}/{endpoint}"
    print(f"Pobieranie {typ} z: {url}")
    
    try:
        response = requests.get(
            url, 
            headers=HEADERS, 
            timeout=REQUEST_TIMEOUT,
            stream=True
        )
        
        if response.status_code == 404:
            print(f"⚠ Dokument nie istnieje dla leku ID={lek_id}")
            return None
        
        response.raise_for_status()
        
        # Utwórz nazwę pliku: ID_typ.pdf (np. 100481636_ulotka.pdf)
        filename = f"{xlsx_id}_{typ}.pdf"
        
        output_path = os.path.join(pdf_dir, filename)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"✓ Pobrano: {output_path}")
        return output_path
        
    except requests.exceptions.Timeout:
        print(f"⚠ Timeout podczas pobierania PDF dla leku ID={lek_id}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠ Błąd podczas pobierania PDF: {e}")
        return None


# ============================================================================
# EKSTRAKCJA TEKSTU Z PDF
# ============================================================================

def ekstrahuj_tekst_z_pdf(pdf_path: str) -> tuple[str, int]:
    """
    Ekstrahuje tekst z pliku PDF
    
    Args:
        pdf_path: Ścieżka do pliku PDF
    
    Returns:
        Tuple (tekst, liczba_stron)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Plik nie istnieje: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
        tekst_calosc = []
        
        for page_num, page in enumerate(doc, 1):
            tekst_strony = page.get_text("text")
            if tekst_strony.strip():
                tekst_calosc.append(f"=== STRONA {page_num} ===\n{tekst_strony}")
        
        # Pobierz liczbę stron przed zamknięciem dokumentu
        liczba_stron = len(doc)
        doc.close()
        
        tekst = "\n\n".join(tekst_calosc)
        return tekst, liczba_stron
        
    except Exception as e:
        raise Exception(f"Błąd podczas ekstrakcji tekstu z PDF: {e}")


def przetworz_pdf_do_jsonl(
    pdf_path: str, 
    lek_id: int, 
    xlsx_id: int,
    lek_nazwa: str, 
    typ: str,
    output_dir: str = None
) -> Optional[str]:
    """
    Przetwarza plik PDF i zapisuje treść w formacie JSONL
    
    Args:
        pdf_path: Ścieżka do pliku PDF
        lek_id: ID leku do API
        xlsx_id: ID leku z pliku XLSX (do nazwy pliku)
        lek_nazwa: Nazwa leku
        typ: Typ dokumentu ("ulotka" lub "charakterystyka")
        output_dir: Katalog do zapisu pliku JSONL
    
    Returns:
        Ścieżka do pliku JSONL lub None w przypadku błędu
    """
    # Użyj domyślnego folderu PDF/JSONL
    jsonl_dir = DEFAULT_PDF_DIR
    ensure_dir(jsonl_dir)
    
    try:
        tekst, liczba_stron = ekstrahuj_tekst_z_pdf(pdf_path)
        
        dokument = DokumentPDF(
            typ=typ,
            lek_id=lek_id,
            lek_nazwa=lek_nazwa,
            url_zrodlo=f"{API_BASE_URL}/{lek_id}/{typ}",
            tekst=tekst,
            data_pobrania=datetime.now().isoformat(),
            liczba_stron=liczba_stron
        )
        
        # Nazwa pliku JSONL: ID_leku.jsonl (np. 100481636.jsonl)
        jsonl_path = os.path.join(jsonl_dir, f"{xlsx_id}.jsonl")
        
        # Jeśli plik już istnieje, dopisz nową treść
        if os.path.exists(jsonl_path):
            with open(jsonl_path, 'a', encoding='utf-8') as f:
                f.write(dokument.to_jsonl())
                f.write('\n')
            print(f"✓ Dopisano do JSONL: {jsonl_path}")
        else:
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                f.write(dokument.to_jsonl())
                f.write('\n')
            print(f"✓ Zapisano JSONL: {jsonl_path}")
        
        return jsonl_path
        
    except Exception as e:
        print(f"⚠ Błąd podczas przetwarzania PDF do JSONL: {e}")
        return None


# ============================================================================
# GŁÓWNE FUNKCJE OPERACYJNE
# ============================================================================

def pobierz_i_przetworz_dokument(
    api_id: int, 
    xlsx_id: int,
    lek_nazwa: str, 
    typ: str,
    output_dir: str = None,
    keep_pdf: bool = True
) -> Optional[str]:
    """
    Pobiera dokument PDF i przetwarza go do formatu JSONL
    
    Args:
        api_id: ID leku do API
        xlsx_id: ID leku z pliku XLSX
        lek_nazwa: Nazwa leku
        typ: Typ dokumentu ("ulotka" lub "charakterystyka")
        output_dir: Katalog do zapisu
        keep_pdf: Czy zachować plik PDF po przetworzeniu
    
    Returns:
        Ścieżka do pliku JSONL lub None w przypadku błędu
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    
    # Pobierz PDF
    pdf_path = pobierz_pdf(api_id, typ, xlsx_id, output_dir)
    
    if not pdf_path:
        return None
    
    # Przetwórz do JSONL
    jsonl_path = przetworz_pdf_do_jsonl(pdf_path, api_id, xlsx_id, lek_nazwa, typ, output_dir)
    
    # Opcjonalnie usuń PDF
    if not keep_pdf and pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)
        print(f"  Usunięto plik PDF: {pdf_path}")
    
    return jsonl_path


def proces_pobierania_leku(
    df: pd.DataFrame,
    lek_idx: int,
    output_dir: str = None,
    pobierz_ulotke: bool = True,
    pobierz_charakterystyke: bool = True
) -> Dict[str, Optional[str]]:
    """
    Pełny proces pobierania dokumentów dla wybranego leku
    
    Args:
        df: DataFrame z danymi o lekach
        lek_idx: Indeks leku w DataFrame
        output_dir: Katalog do zapisu
        pobierz_ulotke: Czy pobrać ulotkę
        pobierz_charakterystyke: Czy pobrać charakterystykę
    
    Returns:
        Słownik ze ścieżkami do utworzonych plików
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    wyniki = {}
    
    # Pobierz dane leku
    row = df.loc[lek_idx]
    
    # Znajdź ID leku - sprawdź różne możliwe nazwy kolumn
    xlsx_id = None
    id_columns = ['id', 'ID', 'Id', 'Identyfikator', 
                  'Identyfikator Produktu Leczniczego']
    for col in id_columns:
        if col in df.columns:
            xlsx_id = row.get(col)
            if xlsx_id is not None and not pd.isna(xlsx_id):
                break
    
    if xlsx_id is None or pd.isna(xlsx_id):
        print("⚠ Nie można znaleźć ID leku")
        print(f"  Dostępne kolumny: {list(df.columns)}")
        return wyniki
    
    xlsx_id = int(xlsx_id)
    
    # Konwertuj ID z formatu XLSX na format API
    api_id = konwertuj_id_leku(xlsx_id)
    
    # Znajdź nazwę leku
    lek_nazwa = ""
    nazwa_columns = ['nazwa', 'Nazwa', 'Nazwa produktu leczniczego',
                     'Nazwa Produktu Leczniczego']
    for col in nazwa_columns:
        if col in df.columns:
            lek_nazwa = str(row.get(col, ""))
            if lek_nazwa:
                break
    
    print(f"\nPrzetwarzanie leku: {lek_nazwa}")
    print(f"  ID w rejestrze: {xlsx_id}")
    print(f"  ID dla API: {api_id}")
    print_separator("-")
    
    # Pobierz ulotkę
    if pobierz_ulotke:
        print("\n[1/2] Pobieranie ulotki...")
        wyniki['ulotka'] = pobierz_i_przetworz_dokument(
            api_id, xlsx_id, lek_nazwa, "ulotka", output_dir
        )
    
    # Pobierz charakterystykę
    if pobierz_charakterystyke:
        print("\n[2/2] Pobieranie charakterystyki...")
        wyniki['charakterystyka'] = pobierz_i_przetworz_dokument(
            api_id, xlsx_id, lek_nazwa, "charakterystyka", output_dir
        )
    
    return wyniki


# ============================================================================
# INTERFEJS UŻYTKOWNIKA (CLI)
# ============================================================================

def menu_glowne():
    """Główne menu programu"""
    print_separator()
    print("  POBIERZ LEKI - Rejestr e-Zdrowie")
    print_separator()
    print("""
Opcje:
  1. Pobierz aktualną bazę leków (XLSX)
  2. Wyszukaj lek po nazwie
  3. Pobierz dokumenty dla leku (ulotka + charakterystyka)
  4. Zmień katalog wyjściowy
  5. Pomoc
  0. Wyjście
""")


def menu_wyszukiwania(df: pd.DataFrame, output_dir: str):
    """Menu wyszukiwania leków"""
    print_separator()
    print("  WYSZUKIWANIE LEKÓW")
    print_separator()
    
    nazwa = input("\nPodaj nazwę leku (lub część nazwy): ").strip()
    
    if not nazwa:
        print("⚠ Nazwa nie może być pusta")
        return None
    
    wyniki = szukaj_lekow(df, nazwa)
    idx_list = wyswietl_wyniki(wyniki)  # Zwraca listę indeksów
    
    if idx_list:
        wybor = input("\nWybierz numer leku (1-{}): ".format(len(idx_list))).strip()
        
        if wybor:
            try:
                num = int(wybor)
                if 1 <= num <= len(idx_list):
                    return idx_list[num - 1]  # Zwróć odpowiedni indeks DataFrame
                else:
                    print(f"⚠ Wybierz numer od 1 do {len(idx_list)}")
            except ValueError:
                print("⚠ Wprowadź liczbę")
    
    return None


def pomoc():
    """Wyświetla pomoc"""
    print_separator()
    print("  POMOC")
    print_separator()
    print("""
Ten program pozwala na:
1. Pobieranie aktualnej bazy leków z rejestru e-Zdrowie
2. Wyszukiwanie leków po nazwie lub jej fragmencie
3. Pobieranie ulotek i charakterystyk produktów leczniczych
4. Konwersję dokumentów PDF do formatu JSONL przyjaznego dla LLM

FORMAT JSONL:
{
  "metadata": {
    "typ_dokumentu": "ulotka/charakterystyka",
    "lek_id": <id>,
    "lek_nazwa": "<nazwa>",
    "url_zrodlo": "<url>",
    "data_pobrania": "<data>",
    "liczba_stron": <liczba>
  },
  "content": "<pełny tekst dokumentu>"
}

API e-Zdrowie:
- XLSX: https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/public-pl-report/get-xlsx
- Ulotka: https://rejestrymedyczne.ezdrowie.gov.pl/api/rpl/medicinal-products/{ID}/leaflet
- Charakterystyka: https://rejestrymedyczne.ezdrowie.gov.pl/api/rpl/medicinal-products/{ID}/characteristic
""")


def glowna_petla():
    """Główna pętla programu"""
    global DEFAULT_OUTPUT_DIR
    
    df = None
    xlsx_path = None
    
    while True:
        menu_glowne()
        print(f"Aktualny katalog wyjściowy: {DEFAULT_OUTPUT_DIR}")
        
        if df is not None:
            print(f"Baza leków wczytana: {len(df)} rekordów")
        elif xlsx_path:
            print(f"Plik XLSX: {xlsx_path}")
        
        wybor = input("\nWybierz opcję: ").strip()
        
        if wybor == "0":
            print("\nDo widzenia!")
            break
        
        elif wybor == "1":
            try:
                xlsx_path = pobierz_baze_lekow(DEFAULT_OUTPUT_DIR)
                df = wczytaj_baze_lekow(xlsx_path)
                df = mapuj_kolumny(df)
            except Exception as e:
                print(f"✗ Błąd: {e}")
        
        elif wybor == "2":
            if df is None:
                # Spróbuj wczytać ostatni plik
                try:
                    pliki = list(Path(DEFAULT_OUTPUT_DIR).glob("*.xlsx"))
                    if pliki:
                        najnowszy = max(pliki, key=os.path.getmtime)
                        print(f"Wczytywanie: {najnowszy}")
                        df = wczytaj_baze_lekow(str(najnowszy))
                        df = mapuj_kolumny(df)
                    else:
                        print("⚠ Najpierw pobierz bazę leków (opcja 1)")
                        continue
                except Exception as e:
                    print(f"✗ Błąd: {e}")
                    continue
            
            wybrany_idx = menu_wyszukiwania(df, DEFAULT_OUTPUT_DIR)
            
            if wybrany_idx is not None:
                proces_pobierania_leku(df, wybrany_idx, DEFAULT_OUTPUT_DIR)
        
        elif wybor == "3":
            if df is None:
                print("⚠ Najpierw wczytaj bazę leków (opcja 1 lub 2)")
                continue
            
            try:
                lek_id = int(input("Podaj ID leku: ").strip())
                
                # Znajdź lek po ID
                if 'id' in df.columns:
                    mask = df['id'] == lek_id
                    if mask.any():
                        idx = df[mask].index[0]
                        proces_pobierania_leku(df, idx, DEFAULT_OUTPUT_DIR)
                    else:
                        print(f"⚠ Nie znaleziono leku o ID={lek_id}")
                else:
                    print("⚠ Kolumna 'id' nie istnieje w danych")
            except ValueError:
                print("⚠ Wprowadź prawidłowy numer ID")
        
        elif wybor == "4":
            nowy_dir = input(f"Podaj nowy katalog [{DEFAULT_OUTPUT_DIR}]: ").strip()
            if nowy_dir:
                DEFAULT_OUTPUT_DIR = nowy_dir
                ensure_dir(DEFAULT_OUTPUT_DIR)
                print(f"✓ Zmieniono katalog na: {DEFAULT_OUTPUT_DIR}")
        
        elif wybor == "5":
            pomoc()
        
        else:
            print("⚠ Nieznana opcja")
        
        input("\nNaciśnij Enter aby kontynuować...")


# ============================================================================
# TRYB BEZPOŚREDNI (BEZ INTERAKCJI)
# ============================================================================

def tryb_bezposredni(
    nazwa_leku: str,
    output_dir: str = None,
    pobierz_ulotke: bool = True,
    pobierz_charakterystyke: bool = True
):
    """
    Tryb bezpośredni - wyszukuje lek i pobiera dokumenty bez interakcji
    
    Args:
        nazwa_leku: Nazwa leku do wyszukania
        output_dir: Katalog wyjściowy
        pobierz_ulotke: Czy pobrać ulotkę
        pobierz_charakterystyke: Czy pobrać charakterystykę
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    ensure_dir(output_dir)
    
    # Pobierz lub wczytaj bazę leków
    try:
        pliki = list(Path(output_dir).glob("*.xlsx"))
        if pliki:
            najnowszy = max(pliki, key=os.path.getmtime)
            print(f"Wczytywanie bazy: {najnowszy}")
            df = wczytaj_baze_lekow(str(najnowszy))
        else:
            print("Pobieranie bazy leków...")
            xlsx_path = pobierz_baze_lekow(output_dir)
            df = wczytaj_baze_lekow(xlsx_path)
        
        df = mapuj_kolumny(df)
    except Exception as e:
        print(f"✗ Błąd podczas wczytywania bazy: {e}")
        return
    
    # Wyszukaj lek
    wyniki = szukaj_lekow(df, nazwa_leku)
    
    if wyniki.empty:
        print(f"✗ Nie znaleziono leku: {nazwa_leku}")
        return
    
    # Jeśli tylko jeden wynik, pobierz automatycznie
    if len(wyniki) == 1:
        idx = wyniki.index[0]
        proces_pobierania_leku(df, idx, output_dir, pobierz_ulotke, pobierz_charakterystyke)
    else:
        # Wyświetl wyniki i pozwól wybrać
        idx_list = wyswietl_wyniki(wyniki)
        wybor = input(f"\nWybierz numer leku (1-{len(idx_list)}): ").strip()
        
        try:
            num = int(wybor)
            if 1 <= num <= len(idx_list):
                idx = idx_list[num - 1]
                proces_pobierania_leku(df, idx, output_dir, pobierz_ulotke, pobierz_charakterystyke)
            else:
                print(f"⚠ Wybierz numer od 1 do {len(idx_list)}")
        except ValueError:
            print("⚠ Wprowadź liczbę")


# ============================================================================
# PUNKT WEJŚCIA
# ============================================================================

def main():
    """Punkt wejścia programu"""
    global DEFAULT_OUTPUT_DIR
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Pobieranie informacji o lekach z rejestru e-Zdrowie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PRZYKŁADY UŻYCIA:

  Tryb interaktywny:
    python3 pobierz_leki.py

  Pobierz dokumenty dla leku:
    python3 pobierz_leki.py -n "ibuprom"
    python3 pobierz_leki.py -n "pyralgina" --tylko-ulotka

  Ekstrakcja parametrów z pliku JSONL:
    python3 pobierz_leki.py -f 100481636.jsonl --nazwa_produktu --dawka_dorosli
    python3 pobierz_leki.py -f 100481636.jsonl --wszystkie
    python3 pobierz_leki.py -f 100481636.jsonl --lek_id --wskazania --przeciwwskazania

DOSTĘPNE PARAMETRY EKSTRAKCJI:
  lek_id, nazwa_produktu, substancja_czynna, substancja_czynna_inn,
  droga_podania, moc, postac_farmaceutyczna, podmiot_odpowiedzialny,
  opakowanie, dawka_dorosli, dawka_dzieci, dawka_specjalna,
  wskazania, przeciwwskazania, dzialania_niepozadane, interakcje,
  ciaza_karmienie, prowadzenie_pojazdow, przedawkowanie,
  przechowywanie, okres_waznosci_otwarcie, sposob_przygotowania
"""
    )
    
    # Parametry podstawowe
    parser.add_argument(
        "-n", "--nazwa",
        help="Nazwa leku do wyszukania (tryb bezpośredni)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help=f"Katalog wyjściowy (domyślnie: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "-f", "--jsonl-file",
        help="Plik JSONL do ekstrakcji parametrów"
    )
    parser.add_argument(
        "--tylko-ulotka",
        action="store_true",
        help="Pobierz tylko ulotkę"
    )
    parser.add_argument(
        "--tylko-charakterystyka",
        action="store_true",
        help="Pobierz tylko charakterystykę"
    )
    parser.add_argument(
        "--pobierz-baze",
        action="store_true",
        help="Tylko pobierz bazę leków (bez wyszukiwania)"
    )
    parser.add_argument(
        "--wszystkie",
        action="store_true",
        help="Ekstrahuj wszystkie parametry z pliku JSONL"
    )
    
    # Parametry ekstrakcji
    parametry_ekstrakcji = [
        'lek_id', 'nazwa_produktu', 'substancja_czynna', 'substancja_czynna_inn',
        'droga_podania', 'moc', 'postac_farmaceutyczna', 'podmiot_odpowiedzialny',
        'opakowanie', 'dawka_dorosli', 'dawka_dzieci', 'dawka_specjalna',
        'wskazania', 'przeciwwskazania', 'dzialania_niepozadane', 'interakcje',
        'ciaza_karmienie', 'prowadzenie_pojazdow', 'przedawkowanie',
        'przechowywanie', 'okres_waznosci_otwarcie', 'sposob_przygotowania'
    ]
    
    for param in parametry_ekstrakcji:
        parser.add_argument(
            f"--{param}",
            action="store_true",
            help=f"Ekstrahuj parametr: {param}"
        )
    
    args = parser.parse_args()
    
    # Aktualizuj katalog wyjściowy
    if args.output:
        DEFAULT_OUTPUT_DIR = args.output
    
    # Tryb ekstrakcji z pliku JSONL (nie wymaga tworzenia katalogów)
    if args.jsonl_file:
        if EkstraktorLekow is None:
            print("✗ Błąd: Biblioteka ekstrakcja_lekow.py nie jest dostępna.")
            print("  Upewnij się, że plik ekstrakcja_lekow.py jest w tym samym katalogu.")
            return
        
        try:
            ekstraktor = EkstraktorLekow(args.jsonl_file)
            
            # Zbierz parametry do ekstrakcji
            parametry_do_ekstrakcji = []
            
            if args.wszystkie:
                parametry_do_ekstrakcji = parametry_ekstrakcji
            else:
                # Sprawdź które parametry zostały wybrane
                for param in parametry_ekstrakcji:
                    if getattr(args, param, False):
                        parametry_do_ekstrakcji.append(param)
            
            # Jeśli nie wybrano żadnych parametrów, pokaż dostępne
            if not parametry_do_ekstrakcji:
                print("Wybierz parametry do ekstrakcji lub użyj --wszystkie")
                print(f"\nDostępne parametry: {', '.join(parametry_ekstrakcji)}")
                return
            
            # Ekstrahuj i wyświetl wyniki
            print(f"Plik: {args.jsonl_file}")
            print("=" * 60)
            
            for parametr in parametry_do_ekstrakcji:
                wynik = ekstraktor.ekstrahuj(parametr)
                print(f"\n{wynik.parametr}:")
                if wynik.znaleziono:
                    print(f"  {wynik.wartosc}")
                    print(f"  [źródło: {wynik.zrodlo}]")
                else:
                    print("  Nie znaleziono")
            
        except FileNotFoundError:
            print(f"✗ Błąd: Plik nie istnieje: {args.jsonl_file}")
        except Exception as e:
            print(f"✗ Błąd podczas ekstrakcji: {e}")
        return
    
    # Dla pozostałych trybów - utwórz katalog wyjściowy
    ensure_dir(DEFAULT_OUTPUT_DIR)
    
    # Tryb tylko pobierania bazy
    if args.pobierz_baze:
        try:
            pobierz_baze_lekow(DEFAULT_OUTPUT_DIR)
        except Exception as e:
            print(f"✗ Błąd: {e}")
        return
    
    # Tryb bezpośredni z nazwą leku
    if args.nazwa:
        pobierz_ulotke = not args.tylko_charakterystyka
        pobierz_charakterystyke = not args.tylko_ulotka
        
        tryb_bezposredni(
            args.nazwa,
            DEFAULT_OUTPUT_DIR,
            pobierz_ulotke,
            pobierz_charakterystyke
        )
        return
    
    # Tryb interaktywny
    try:
        glowna_petla()
    except KeyboardInterrupt:
        print("\n\nPrzerwano przez użytkownika. Do widzenia!")


if __name__ == "__main__":
    main()

