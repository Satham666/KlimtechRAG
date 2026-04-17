#!/usr/bin/env python3
"""
KlimtechRAG Desktop GUI – WERSJA DEMO / TESTOWA
=================================================
Standalone UI bez backendu. Wszystkie odpowiedzi są symulowane.
Służy do oceny layoutu, UX i kolorów przed podpięciem do FastAPI.

Uruchomienie:
    python3 klimtech_gui_demo.py

Wymagania:
    pip install ttkbootstrap
"""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# ─────────────────────────────────────────────────────────────
#  MOCK BACKEND  (zastąp prawdziwym APIClient docelowo)
# ─────────────────────────────────────────────────────────────
MOCK_ANSWERS = [
    "Ciśnienie robocze sprężarki powinno wynosić **6–8 bar** przy pracy ciągłej. "
    "Wartości powyżej 10 bar wymagają zaworu bezpieczeństwa klasy A.",
    "Zgodnie z dokumentacją, wymiana filtra powietrza powinna odbywać się co **500 mth** "
    "lub co 6 miesięcy – w zależności co nastąpi wcześniej.",
    "Kod błędu **E-04** oznacza przekroczenie temperatury oleju. "
    "Sprawdź poziom oleju, drożność chłodnicy i temperaturę otoczenia.",
    "Moment dokręcenia śrub głowicy: **M10 → 45 Nm**, **M12 → 75 Nm** wg tabeli 3.2 w instrukcji.",
]
_answer_idx = 0

MOCK_HEALTH = {
    "status":     "ok",
    "version":    "v6.0-demo",
    "uptime":     "2h 17m",
    "llm_loaded": "Bielik-4.5B-Instruct (Q5_K_M)",
}
MOCK_VRAM = {
    "vram_used_mb":  6240,
    "vram_total_mb": 16384,
}
MOCK_MODELS = {
    "llm":       "Bielik-4.5B-v3.0-Instruct-Q5_K_M.gguf",
    "embedding": "multilingual-e5-large",
    "colpali":   "vidore/colqwen2-v1.0",
    "vlm":       "LFM2.5-VL-3B (Q4_K_M)",
}


def mock_stream(question: str, pipeline: str, on_chunk, on_done, on_error):
    """Symuluje SSE streaming z backendu – token po tokenie."""
    global _answer_idx
    answer = MOCK_ANSWERS[_answer_idx % len(MOCK_ANSWERS)]
    _answer_idx += 1

    prefix = f"[Pipeline: {pipeline}] "
    for char in prefix:
        on_chunk(char)
        time.sleep(0.01)

    words = answer.split(" ")
    for word in words:
        on_chunk(word + " ")
        time.sleep(0.04)

    on_done()


def mock_upload(filepath: str, pipeline: str, on_progress, on_done, on_error):
    """Symuluje upload + ingestię z paskiem postępu."""
    steps = [
        (10,  "Wczytywanie pliku…"),
        (25,  "Parsowanie dokumentu…"),
        (45,  "Generowanie embeddingów…"),
        (70,  "Zapis do Qdrant…"),
        (90,  "Indeksowanie…"),
        (100, "Gotowe!"),
    ]
    for pct, msg in steps:
        time.sleep(0.6)
        on_progress(pct, msg)
    on_done()


# ─────────────────────────────────────────────────────────────
#  KOLORY (Catppuccin Mocha)
# ─────────────────────────────────────────────────────────────
CLR_BG      = "#1e1e2e"
CLR_SURFACE = "#181825"
CLR_TEXT    = "#cdd6f4"
CLR_USER    = "#89b4fa"   # niebieski
CLR_BOT     = "#a6e3a1"   # zielony
CLR_ERROR   = "#f38ba8"   # czerwony
CLR_INFO    = "#fab387"   # pomarańczowy
CLR_DIM     = "#45475a"   # szary


# ─────────────────────────────────────────────────────────────
#  TAB: CHAT
# ─────────────────────────────────────────────────────────────
class ChatTab(ttk.Frame):
    PIPELINES = ["text", "colpali", "vlm"]

    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var    = status_var
        self._chunk_queue  = queue.Queue()
        self._is_streaming = False
        self._build_ui()
        self._poll()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Górny pasek ──────────────────────────────────────
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=EW, padx=10, pady=(10, 4))

        ttk.Label(top, text="Pipeline:", font=("Consolas", 10)).pack(side=LEFT)
        self.pipe_var = tk.StringVar(value="text")
        ttk.Combobox(
            top, textvariable=self.pipe_var,
            values=self.PIPELINES, state="readonly",
            width=10, bootstyle=INFO,
        ).pack(side=LEFT, padx=(4, 20))

        ttk.Button(
            top, text="🗑  Wyczyść",
            bootstyle="secondary-outline",
            command=self._clear, width=12,
        ).pack(side=RIGHT)

        # ── Obszar rozmowy ────────────────────────────────────
        self.display = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, state="disabled",
            font=("Consolas", 10),
            bg=CLR_BG, fg=CLR_TEXT,
            insertbackground=CLR_TEXT,
            relief="flat", padx=12, pady=8,
        )
        self.display.grid(row=1, column=0, sticky=NSEW, padx=10, pady=4)

        for tag, fg, bold in [
            ("user",      CLR_USER,  True),
            ("bot",       CLR_BOT,   False),
            ("error",     CLR_ERROR, False),
            ("info",      CLR_INFO,  False),
            ("separator", CLR_DIM,   False),
        ]:
            font = ("Consolas", 10, "bold") if bold else ("Consolas", 10)
            self.display.tag_config(tag, foreground=fg, font=font)

        # ── Pasek wejściowy ───────────────────────────────────
        inp = ttk.Frame(self)
        inp.grid(row=2, column=0, sticky=EW, padx=10, pady=(4, 10))
        inp.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(
            inp, textvariable=self.input_var,
            font=("Consolas", 11), bootstyle=INFO,
        )
        self.entry.grid(row=0, column=0, sticky=EW, ipady=6)
        self.entry.bind("<Return>", lambda _: self._send())
        self.entry.focus_set()

        self.btn_send = ttk.Button(
            inp, text="Wyślij  ➤",
            bootstyle=SUCCESS, command=self._send, width=12,
        )
        self.btn_send.grid(row=0, column=1, padx=(6, 0))

        self.btn_stop = ttk.Button(
            inp, text="⏹  Stop",
            bootstyle="danger-outline", command=self._stop,
            width=10, state=DISABLED,
        )
        self.btn_stop.grid(row=0, column=2, padx=(4, 0))

        # ── Wiadomość powitalna ───────────────────────────────
        self._append("info",
            "╔══════════════════════════════════════════════╗\n"
            "║   KlimtechRAG – wersja DEMO / testowa UI    ║\n"
            "╚══════════════════════════════════════════════╝\n\n"
            "Wpisz dowolne pytanie – odpowiedzi są symulowane.\n"
            "Możesz testować layout, kolory i UX przed podpięciem do backendu.\n\n"
        )

    # ── Logika ────────────────────────────────────────────────
    def _send(self):
        q = self.input_var.get().strip()
        if not q or self._is_streaming:
            return
        self.input_var.set("")
        self._is_streaming = True
        self.btn_send.config(state=DISABLED)
        self.btn_stop.config(state=NORMAL)
        self._append("separator", "─" * 58 + "\n")
        self._append("user", f"👤 Ty: {q}\n\n")
        self._append("info", "🤖 KlimtechRAG: ")
        self.status_var.set(f"Zapytanie [{self.pipe_var.get()}] w toku…")
        threading.Thread(
            target=mock_stream,
            args=(
                q, self.pipe_var.get(),
                lambda c: self._chunk_queue.put(("chunk", c)),
                lambda:   self._chunk_queue.put(("done",  "")),
                lambda e: self._chunk_queue.put(("error", e)),
            ),
            daemon=True,
        ).start()

    def _stop(self):
        self._chunk_queue.put(("stop", ""))

    def _clear(self):
        self.display.config(state=NORMAL)
        self.display.delete("1.0", tk.END)
        self.display.config(state=DISABLED)

    def _poll(self):
        try:
            while True:
                ev, data = self._chunk_queue.get_nowait()
                if ev == "chunk":
                    self._append("bot", data)
                elif ev in ("done", "stop"):
                    self._append("bot", "\n\n")
                    self._end_stream()
                elif ev == "error":
                    self._append("error", f"\n\n⚠️  {data}\n\n")
                    self._end_stream()
        except queue.Empty:
            pass
        self.after(40, self._poll)   # 40ms → płynny token-by-token

    def _end_stream(self):
        self._is_streaming = False
        self.btn_send.config(state=NORMAL)
        self.btn_stop.config(state=DISABLED)
        self.status_var.set("Gotowe.")

    def _append(self, tag, text):
        self.display.config(state=NORMAL)
        self.display.insert(tk.END, text, tag)
        self.display.see(tk.END)
        self.display.config(state=DISABLED)


# ─────────────────────────────────────────────────────────────
#  TAB: INGESTIA
# ─────────────────────────────────────────────────────────────
class IngestTab(ttk.Frame):
    PIPELINES = [
        ("text  –  e5-large (teksty, .txt, .docx, .md)", "text"),
        ("colpali  –  PDF / skany (bez OCR)",             "colpali"),
        ("vlm  –  LFM2.5-VL (obrazy w PDF)",              "vlm"),
    ]

    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var    = status_var
        self._file_var     = tk.StringVar()
        self._progress_var = tk.DoubleVar(value=0)
        self._pipe_var     = tk.StringVar(value="text")
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ── Wybór pliku ──
        lf1 = ttk.LabelFrame(self, text=" 📁  Plik do ingestii ")
        lf1.grid(row=0, column=0, sticky=EW, padx=12, pady=(14, 6))
        lf1.columnconfigure(0, weight=1)

        ttk.Entry(lf1, textvariable=self._file_var, state="readonly",
                  font=("Consolas", 10)).grid(row=0, column=0, sticky=EW, ipady=4)
        ttk.Button(
            lf1, text="Przeglądaj…", bootstyle="info-outline",
            command=self._pick, width=12,
        ).grid(row=0, column=1, padx=(8, 0))

        # ── Pipeline ──
        lf2 = ttk.LabelFrame(self, text=" ⚙️  Pipeline ")
        lf2.grid(row=1, column=0, sticky=EW, padx=12, pady=6)

        for label, val in self.PIPELINES:
            ttk.Radiobutton(
                lf2, text=label, variable=self._pipe_var, value=val,
                bootstyle="info-toolbutton",
            ).pack(anchor=W, padx=4, pady=2)

        # ── Start ──
        self.btn_start = ttk.Button(
            self, text="▶   Rozpocznij Ingestię",
            bootstyle=SUCCESS, command=self._start,
        )
        self.btn_start.grid(row=2, column=0, pady=10, ipadx=24, ipady=6)

        # ── Progress ──
        lf3 = ttk.LabelFrame(self, text=" Postęp ")
        lf3.grid(row=3, column=0, sticky=EW, padx=12, pady=6)
        lf3.columnconfigure(0, weight=1)

        self.pbar = ttk.Progressbar(
            lf3, variable=self._progress_var,
            maximum=100, bootstyle="success-striped",
        )
        self.pbar.grid(row=0, column=0, sticky=EW, ipady=5)

        self.pct_lbl = ttk.Label(lf3, text="0 %", bootstyle=INFO, width=6)
        self.pct_lbl.grid(row=0, column=1, padx=(10, 0))

        # ── Log ──
        lf4 = ttk.LabelFrame(self, text=" Log ")
        lf4.grid(row=4, column=0, sticky=NSEW, padx=12, pady=(6, 12))
        self.rowconfigure(4, weight=1)
        lf4.columnconfigure(0, weight=1)
        lf4.rowconfigure(0, weight=1)

        self.log = scrolledtext.ScrolledText(
            lf4, height=8, state="disabled",
            font=("Consolas", 9),
            bg=CLR_SURFACE, fg="#a6adc8", relief="flat",
        )
        self.log.grid(row=0, column=0, sticky=NSEW)

    def _pick(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik",
            filetypes=[
                ("Dokumenty", "*.pdf *.txt *.docx *.md *.png *.jpg *.jpeg"),
                ("Wszystkie", "*.*"),
            ],
        )
        if path:
            self._file_var.set(path)

    def _start(self):
        fp = self._file_var.get()
        if not fp:
            from tkinter import messagebox
            messagebox.showwarning("Brak pliku", "Najpierw wybierz plik do ingestii.")
            return
        self._progress_var.set(0)
        self.pct_lbl.config(text="0 %")
        self.btn_start.config(state=DISABLED)
        self.status_var.set("Ingestia w toku…")
        self._log(f"▶ Start: {Path(fp).name}  [{self._pipe_var.get()}]\n")

        threading.Thread(
            target=mock_upload,
            args=(
                fp, self._pipe_var.get(),
                lambda p, m: self.after(0, lambda: self._on_progress(p, m)),
                lambda:      self.after(0, self._on_done),
                lambda e:    self.after(0, lambda: self._log(f"❌ {e}\n")),
            ),
            daemon=True,
        ).start()

    def _on_progress(self, pct, msg):
        self._progress_var.set(pct)
        self.pct_lbl.config(text=f"{int(pct)} %")
        self._log(f"  [{int(pct):3d}%]  {msg}\n")

    def _on_done(self):
        self._progress_var.set(100)
        self.pct_lbl.config(text="100 %")
        self._log("🏁 Ingestia zakończona.\n")
        self.btn_start.config(state=NORMAL)
        self.status_var.set("Ingestia zakończona.")

    def _log(self, text):
        self.log.config(state=NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.config(state=DISABLED)


# ─────────────────────────────────────────────────────────────
#  TAB: STATUS SYSTEMU
# ─────────────────────────────────────────────────────────────
class StatusTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var   = status_var
        self._auto        = tk.BooleanVar(value=True)
        self._vram_target = 0
        self._vram_current = 0
        self._build_ui()
        self._schedule()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ── Health ──
        lf_h = ttk.LabelFrame(self, text=" 🟢  Backend Health ")
        lf_h.grid(row=0, column=0, sticky=NSEW, padx=(12, 6), pady=12)
        lf_h.columnconfigure(1, weight=1)

        self._hlabels = {}
        for i, (key, val) in enumerate(MOCK_HEALTH.items()):
            ttk.Label(lf_h, text=f"{key}:", bootstyle=SECONDARY,
                      font=("Consolas", 9)).grid(row=i, column=0, sticky=W, pady=3)
            lbl = ttk.Label(lf_h, text=val, bootstyle=INFO, font=("Consolas", 9))
            lbl.grid(row=i, column=1, sticky=W, padx=(10, 0))
            self._hlabels[key] = lbl

        # ── VRAM ──
        lf_v = ttk.LabelFrame(self, text=" 🔥  VRAM  (AMD Instinct 16 GB) ")
        lf_v.grid(row=0, column=1, sticky=NSEW, padx=(6, 12), pady=12)
        lf_v.columnconfigure(0, weight=1)

        self.meter = ttk.Meter(
            lf_v,
            metersize=170,
            amounttotal=16384,
            amountused=0,
            subtext="MB zajęte",
            bootstyle=WARNING,
            interactive=False,
        )
        self.meter.grid(row=0, column=0)

        self.vram_lbl = ttk.Label(lf_v, text="Ładowanie…", bootstyle=SECONDARY,
                                   font=("Consolas", 9))
        self.vram_lbl.grid(row=1, column=0, pady=(4, 0))

        # ── Modele ──
        lf_m = ttk.LabelFrame(self, text=" 🤖  Załadowane Modele ")
        lf_m.grid(row=1, column=0, columnspan=2, sticky=NSEW, padx=12, pady=(0, 8))
        lf_m.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        for i, (role, name) in enumerate(MOCK_MODELS.items()):
            ttk.Label(lf_m, text=f"{role}:", bootstyle=SECONDARY,
                      font=("Consolas", 9, "bold")).grid(row=i, column=0, sticky=W, pady=3, padx=(4, 0))
            ttk.Label(lf_m, text=name, bootstyle=INFO,
                      font=("Consolas", 9)).grid(row=i, column=1, sticky=W, padx=(12, 0))

        # ── Przyciski ──
        bf = ttk.Frame(self)
        bf.grid(row=2, column=0, columnspan=2, pady=(4, 14))

        ttk.Button(bf, text="🔄  Odśwież teraz", bootstyle=INFO,
                   command=self._refresh, width=18).pack(side=LEFT, padx=8)

        ttk.Checkbutton(bf, text="Auto (5s)", variable=self._auto,
                        bootstyle="info-round-toggle").pack(side=LEFT)

    def _refresh(self):
        # Symulacja zmiany VRAM (losowo ±300 MB)
        import random
        used  = MOCK_VRAM["vram_used_mb"] + random.randint(-300, 300)
        used  = max(1000, min(used, 15800))
        total = MOCK_VRAM["vram_total_mb"]
        self._vram_target = used
        self._animate_meter(used, total)
        self.status_var.set("Status odświeżony  (DEMO).")

    def _animate_meter(self, target, total):
        current = self._vram_current
        step = (target - current) / 20
        def _tick(i=0):
            if i >= 20:
                self._vram_current = target
                self._set_meter(target, total)
                return
            val = int(current + step * i)
            self._set_meter(val, total)
            self.after(30, lambda: _tick(i + 1))
        _tick()

    def _set_meter(self, used, total):
        pct = used / total * 100
        style = SUCCESS if pct < 50 else (WARNING if pct < 80 else DANGER)
        self.meter.configure(amountused=used, bootstyle=style)
        self.vram_lbl.config(text=f"{used} MB / {total} MB  ({pct:.1f}%)")

    def _schedule(self):
        if self._auto.get():
            self._refresh()
        self.after(5000, self._schedule)


# ─────────────────────────────────────────────────────────────
#  TAB: USTAWIENIA
# ─────────────────────────────────────────────────────────────
class SettingsTab(ttk.Frame):
    def __init__(self, parent, status_var: tk.StringVar):
        super().__init__(parent)
        self.status_var = status_var
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ── Połączenie ──
        lf1 = ttk.LabelFrame(self, text=" 🔌  Połączenie z backendem ")
        lf1.grid(row=0, column=0, sticky=EW, padx=16, pady=20)
        lf1.columnconfigure(1, weight=1)

        ttk.Label(lf1, text="URL:", font=("Consolas", 10)).grid(row=0, column=0, sticky=W)
        self.url_var = tk.StringVar(value="http://localhost:8000")
        ttk.Entry(lf1, textvariable=self.url_var,
                  font=("Consolas", 11)).grid(row=0, column=1, sticky=EW, padx=(10, 0), ipady=4)

        self.test_lbl = ttk.Label(lf1, text="⚠️  Tryb DEMO – backend niesymulowany",
                                   bootstyle=WARNING, font=("Consolas", 9))
        self.test_lbl.grid(row=1, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(
            lf1, text="💾  Zastosuj i testuj połączenie",
            bootstyle=SUCCESS, command=self._test, width=30,
        ).grid(row=2, column=0, columnspan=2, pady=(12, 0), ipady=4)

        # ── Tematy ──
        lf2 = ttk.LabelFrame(self, text=" 🎨  Temat (podgląd) ")
        lf2.grid(row=1, column=0, sticky=EW, padx=16, pady=6)

        themes = ["darkly", "superhero", "cyborg", "vapor", "solar", "cosmo", "flatly"]
        self.theme_var = tk.StringVar(value="darkly")
        ttk.Label(lf2, text="Wybierz temat:", font=("Consolas", 10)).pack(side=LEFT)
        cb = ttk.Combobox(lf2, textvariable=self.theme_var, values=themes,
                           state="readonly", width=14, bootstyle=INFO)
        cb.pack(side=LEFT, padx=(8, 12))
        ttk.Button(lf2, text="Zastosuj", bootstyle="info-outline",
                   command=self._apply_theme).pack(side=LEFT)

        # ── Info ──
        lf3 = ttk.LabelFrame(self, text=" ℹ️  O aplikacji ")
        lf3.grid(row=2, column=0, sticky=EW, padx=16, pady=6)

        info = (
            "KlimtechRAG Desktop GUI  –  wersja DEMO\n"
            "────────────────────────────────────────────────\n"
            "Ta wersja działa STANDALONE (bez backendu).\n"
            "Odpowiedzi, VRAM i status są symulowane.\n\n"
            "Aby podłączyć do backendu:\n"
            "  1. Podmień klasę MockAPIClient → APIClient\n"
            "  2. Ustaw URL w zakładce Ustawienia\n"
            "  3. Uruchom backend:  python3 app.py\n\n"
            "Stack docelowy:\n"
            "  FastAPI + Haystack 2.x + Qdrant + llama.cpp\n"
            "  LLM:  Bielik-4.5B-v3.0-Instruct (ROCm)\n"
        )
        ttk.Label(lf3, text=info, font=("Consolas", 9),
                  justify=LEFT, bootstyle=SECONDARY).pack(anchor=W)

    def _test(self):
        self.test_lbl.config(
            text="⚠️  Tryb DEMO – kliknięcie nie łączy z backendem",
            bootstyle=WARNING,
        )

    def _apply_theme(self):
        style = ttk.Style.instance
        if style:
            try:
                style.theme_use(self.theme_var.get())
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
#  GŁÓWNE OKNO
# ─────────────────────────────────────────────────────────────
class KlimtechApp(ttk.Window):
    def __init__(self):
        super().__init__(
            title="KlimtechRAG Desktop  [DEMO]",
            themename="darkly",
            size=(1060, 730),
            minsize=(820, 560),
        )
        self.status_var = tk.StringVar(value="Tryb DEMO – backend niesymulowany")
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        nb = ttk.Notebook(self, bootstyle=INFO)
        nb.grid(row=0, column=0, sticky=NSEW)

        tabs = [
            ("  💬  Chat  ",        ChatTab(nb,     self.status_var)),
            ("  📤  Ingestia  ",    IngestTab(nb,   self.status_var)),
            ("  📊  System  ",      StatusTab(nb,   self.status_var)),
            ("  ⚙️   Ustawienia  ", SettingsTab(nb, self.status_var)),
        ]
        for label, tab in tabs:
            nb.add(tab, text=label)

        # ── Status bar ──
        ttk.Label(
            self,
            textvariable=self.status_var,
            bootstyle=SECONDARY,
            font=("Consolas", 8),
            anchor=W,
            padding=(8, 3),
        ).grid(row=1, column=0, sticky=EW)


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    KlimtechApp().mainloop()
