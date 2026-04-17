#!/usr/bin/env python3
"""
KlimtechRAG Desktop GUI
=======================
TTKBootstrap klient dla backendu KlimtechRAG (FastAPI).
Komunikuje się z backendem przez lokalne API - backend działa niezależnie.

Uruchomienie:
    source venv/bin/activate.fish
    python3 klimtech_gui.py

Wymagania:
    pip install ttkbootstrap requests
"""

import json
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
import tkinter as tk

import requests
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# ─────────────────────────────────────────────────────────────
#  KONFIGURACJA DOMYŚLNA
# ─────────────────────────────────────────────────────────────
DEFAULT_API_URL = "http://localhost:8000"
POLL_INTERVAL_MS = 1500   # co ile ms sprawdzamy kolejkę zdarzeń
STREAM_TIMEOUT   = 120    # timeout streamingu (s)
VRAM_REFRESH_MS  = 5000   # co ile ms odświeżamy VRAM


# ─────────────────────────────────────────────────────────────
#  KLIENT API
# ─────────────────────────────────────────────────────────────
class APIClient:
    """
    Wrapper HTTP dla KlimtechRAG Backend.
    Wszystkie metody są blokujące – wywoływane z osobnych wątków.
    """

    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ── Zdrowie / status ──────────────────────────────────────
    def health(self) -> dict:
        r = self.session.get(self._url("/health"), timeout=5)
        r.raise_for_status()
        return r.json()

    def vram_status(self) -> dict:
        """Próbuje kilka typowych endpointów VRAM."""
        for path in ("/vram", "/api/vram", "/status/vram", "/status"):
            try:
                r = self.session.get(self._url(path), timeout=5)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                continue
        return {}

    def models_info(self) -> dict:
        for path in ("/models", "/api/models", "/info"):
            try:
                r = self.session.get(self._url(path), timeout=5)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                continue
        return {}

    # ── Zapytanie (streaming SSE) ─────────────────────────────
    def query_stream(self, question: str, pipeline: str, on_chunk, on_done, on_error):
        """
        Wysyła zapytanie RAG. Backend może zwracać:
          - text/event-stream  (SSE)
          - application/json   (jednorazowa odpowiedź)
        Callback on_chunk(text) wywoływany dla każdego fragmentu.
        """
        payload = {"question": question, "query": question, "pipeline": pipeline}
        headers = {"Accept": "text/event-stream, application/json"}
        try:
            with self.session.post(
                self._url("/query"),
                json=payload,
                headers=headers,
                stream=True,
                timeout=STREAM_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "")

                if "event-stream" in ct:
                    # ── SSE streaming ──
                    for raw in resp.iter_lines():
                        if raw:
                            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                            if line.startswith("data:"):
                                data = line[5:].strip()
                                if data == "[DONE]":
                                    break
                                try:
                                    obj = json.loads(data)
                                    chunk = (
                                        obj.get("answer")
                                        or obj.get("text")
                                        or obj.get("chunk")
                                        or data
                                    )
                                    on_chunk(chunk)
                                except json.JSONDecodeError:
                                    on_chunk(data)
                else:
                    # ── Jednorazowy JSON ──
                    obj = resp.json()
                    answer = (
                        obj.get("answer")
                        or obj.get("response")
                        or obj.get("text")
                        or str(obj)
                    )
                    on_chunk(answer)

            on_done()
        except Exception as exc:
            on_error(str(exc))

    # ── Ingestia pliku ────────────────────────────────────────
    def upload_file(self, filepath: str, pipeline: str) -> dict:
        path = Path(filepath)
        with open(path, "rb") as f:
            files = {"file": (path.name, f, "application/octet-stream")}
            data  = {"pipeline": pipeline}
            r = self.session.post(
                self._url("/upload"),
                files=files,
                data=data,
                timeout=300,
            )
            r.raise_for_status()
            return r.json()

    def ingest_progress(self, task_id: str = "") -> dict:
        for path in (f"/progress/{task_id}", "/progress", "/ingest/status"):
            try:
                r = self.session.get(self._url(path), timeout=5)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                continue
        return {}


# ─────────────────────────────────────────────────────────────
#  TAB: CHAT
# ─────────────────────────────────────────────────────────────
class ChatTab(ttk.Frame):
    PIPELINES = ["text", "colpali", "vlm"]

    def __init__(self, parent, client: APIClient, status_bar_var: tk.StringVar):
        super().__init__(parent)
        self.client         = client
        self.status_bar_var = status_bar_var
        self._chunk_queue: queue.Queue = queue.Queue()
        self._is_streaming  = False
        self._build_ui()
        self._poll_queue()

    # ── Budowanie UI ──────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Górny pasek opcji ──
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=EW, padx=10, pady=(10, 4))

        ttk.Label(top, text="Pipeline:").pack(side=LEFT)
        self.pipeline_var = tk.StringVar(value="text")
        pipe_cb = ttk.Combobox(
            top,
            textvariable=self.pipeline_var,
            values=self.PIPELINES,
            state="readonly",
            width=10,
            bootstyle=INFO,
        )
        pipe_cb.pack(side=LEFT, padx=(4, 20))

        self.btn_clear = ttk.Button(
            top, text="🗑 Wyczyść", bootstyle="secondary-outline",
            command=self._clear_chat, width=12
        )
        self.btn_clear.pack(side=RIGHT)

        # ── Obszar konwersacji ──
        chat_frame = ttk.Frame(self, bootstyle=DARK)
        chat_frame.grid(row=1, column=0, sticky=NSEW, padx=10, pady=4)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            state="disabled",
            font=("Consolas", 10),
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            relief="flat",
            padx=12,
            pady=8,
        )
        self.chat_display.grid(row=0, column=0, sticky=NSEW)

        # Tagi kolorów
        self.chat_display.tag_config("user",      foreground="#89b4fa", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="#a6e3a1")
        self.chat_display.tag_config("error",     foreground="#f38ba8")
        self.chat_display.tag_config("info",      foreground="#fab387")
        self.chat_display.tag_config("separator", foreground="#45475a")

        # ── Pasek wejściowy ──
        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky=EW, padx=10, pady=(4, 10))
        input_frame.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(
            input_frame,
            textvariable=self.input_var,
            font=("Consolas", 11),
            bootstyle=INFO,
        )
        self.entry.grid(row=0, column=0, sticky=EW, ipady=6)
        self.entry.bind("<Return>",       lambda e: self._send_query())
        self.entry.bind("<Shift-Return>", lambda e: self._insert_newline())

        self.btn_send = ttk.Button(
            input_frame,
            text="Wyślij ➤",
            bootstyle=SUCCESS,
            command=self._send_query,
            width=12,
        )
        self.btn_send.grid(row=0, column=1, padx=(6, 0))

        self.btn_stop = ttk.Button(
            input_frame,
            text="⏹ Stop",
            bootstyle="danger-outline",
            command=self._stop_stream,
            width=10,
            state=DISABLED,
        )
        self.btn_stop.grid(row=0, column=2, padx=(4, 0))

    # ── Logika wysyłania ──────────────────────────────────────
    def _send_query(self):
        question = self.input_var.get().strip()
        if not question or self._is_streaming:
            return

        self.input_var.set("")
        self._is_streaming = True
        self.btn_send.config(state=DISABLED)
        self.btn_stop.config(state=NORMAL)

        self._append("separator", "─" * 60 + "\n")
        self._append("user", f"👤 Ty: {question}\n\n")
        self._append("info", "🤖 KlimtechRAG: ")

        pipeline = self.pipeline_var.get()
        self.status_bar_var.set(f"Wysyłanie zapytania [{pipeline}]...")

        t = threading.Thread(
            target=self.client.query_stream,
            args=(
                question, pipeline,
                lambda chunk: self._chunk_queue.put(("chunk", chunk)),
                lambda:       self._chunk_queue.put(("done",  "")),
                lambda err:   self._chunk_queue.put(("error", err)),
            ),
            daemon=True,
        )
        t.start()

    def _stop_stream(self):
        self._chunk_queue.put(("stop", ""))

    def _insert_newline(self):
        self.entry.insert(tk.INSERT, "\n")

    def _clear_chat(self):
        self.chat_display.config(state=NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=DISABLED)

    # ── Thread-safe polling kolejki ───────────────────────────
    def _poll_queue(self):
        try:
            while True:
                event, payload = self._chunk_queue.get_nowait()
                if event == "chunk":
                    self._append("assistant", payload)
                elif event in ("done", "stop"):
                    self._append("assistant", "\n\n")
                    self._stream_ended()
                elif event == "error":
                    self._append("error", f"\n\n⚠️  Błąd: {payload}\n\n")
                    self._stream_ended()
        except queue.Empty:
            pass
        self.after(POLL_INTERVAL_MS // 5, self._poll_queue)

    def _stream_ended(self):
        self._is_streaming = False
        self.btn_send.config(state=NORMAL)
        self.btn_stop.config(state=DISABLED)
        self.status_bar_var.set("Gotowe.")

    def _append(self, tag: str, text: str):
        self.chat_display.config(state=NORMAL)
        self.chat_display.insert(tk.END, text, tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=DISABLED)


# ─────────────────────────────────────────────────────────────
#  TAB: INGESTIA PLIKÓW
# ─────────────────────────────────────────────────────────────
class IngestTab(ttk.Frame):
    PIPELINES = ["text (e5-large)", "colpali (PDF/skany)", "vlm (obrazy w PDF)"]
    PIPE_MAP  = {"text (e5-large)": "text", "colpali (PDF/skany)": "colpali", "vlm (obrazy w PDF)": "vlm"}

    def __init__(self, parent, client: APIClient, status_bar_var: tk.StringVar):
        super().__init__(parent)
        self.client         = client
        self.status_bar_var = status_bar_var
        self._selected_file = tk.StringVar()
        self._progress_var  = tk.DoubleVar(value=0)
        self._task_id       = ""
        self._polling       = False
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ── Wybór pliku ──
        file_lf = ttk.LabelFrame(self, text=" 📁 Plik do ingestii ", bootstyle=INFO, padding=10)
        file_lf.grid(row=0, column=0, sticky=EW, padx=12, pady=(14, 6))
        file_lf.columnconfigure(0, weight=1)

        ttk.Entry(file_lf, textvariable=self._selected_file, state="readonly").grid(
            row=0, column=0, sticky=EW, ipady=4
        )
        ttk.Button(
            file_lf, text="Przeglądaj…", bootstyle="info-outline",
            command=self._pick_file, width=12
        ).grid(row=0, column=1, padx=(8, 0))

        # ── Wybór pipeline ──
        pipe_lf = ttk.LabelFrame(self, text=" ⚙️  Pipeline ", bootstyle=INFO, padding=10)
        pipe_lf.grid(row=1, column=0, sticky=EW, padx=12, pady=6)

        self.pipe_var = tk.StringVar(value=self.PIPELINES[0])
        for p in self.PIPELINES:
            ttk.Radiobutton(
                pipe_lf, text=p, variable=self.pipe_var, value=p, bootstyle="info-toolbutton"
            ).pack(side=LEFT, padx=6)

        # ── Przycisk startu ──
        self.btn_ingest = ttk.Button(
            self, text="▶  Rozpocznij Ingestię",
            bootstyle=SUCCESS, command=self._start_ingest
        )
        self.btn_ingest.grid(row=2, column=0, pady=10, ipadx=20, ipady=6)

        # ── Pasek postępu ──
        prog_lf = ttk.LabelFrame(self, text=" Postęp ", bootstyle=INFO, padding=10)
        prog_lf.grid(row=3, column=0, sticky=EW, padx=12, pady=6)
        prog_lf.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            prog_lf,
            variable=self._progress_var,
            maximum=100,
            bootstyle="success-striped",
            mode="determinate",
        )
        self.progress_bar.grid(row=0, column=0, sticky=EW, ipady=4)

        self.progress_label = ttk.Label(prog_lf, text="0 %", bootstyle=INFO)
        self.progress_label.grid(row=0, column=1, padx=(10, 0))

        # ── Log ──
        log_lf = ttk.LabelFrame(self, text=" Log ", bootstyle=SECONDARY, padding=6)
        log_lf.grid(row=4, column=0, sticky=NSEW, padx=12, pady=(6, 12))
        self.rowconfigure(4, weight=1)
        log_lf.columnconfigure(0, weight=1)
        log_lf.rowconfigure(0, weight=1)

        self.log = scrolledtext.ScrolledText(
            log_lf, height=10, state="disabled",
            font=("Consolas", 9), bg="#181825", fg="#a6adc8",
            relief="flat"
        )
        self.log.grid(row=0, column=0, sticky=NSEW)

    # ── Logika ───────────────────────────────────────────────
    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz plik do ingestii",
            filetypes=[("Dokumenty", "*.pdf *.txt *.docx *.md *.png *.jpg *.jpeg"), ("Wszystkie", "*.*")]
        )
        if path:
            self._selected_file.set(path)

    def _start_ingest(self):
        filepath = self._selected_file.get()
        if not filepath:
            messagebox.showwarning("Brak pliku", "Najpierw wybierz plik.")
            return

        pipeline = self.PIPE_MAP.get(self.pipe_var.get(), "text")
        self._log(f"▶ Start ingestii: {Path(filepath).name} [{pipeline}]\n")
        self._progress_var.set(0)
        self.btn_ingest.config(state=DISABLED)
        self.status_bar_var.set("Ingestia w toku…")

        threading.Thread(
            target=self._upload_thread,
            args=(filepath, pipeline),
            daemon=True,
        ).start()

    def _upload_thread(self, filepath, pipeline):
        try:
            result = self.client.upload_file(filepath, pipeline)
            self._task_id = result.get("task_id", "")
            self.after(0, lambda: self._log(f"✅ Upload OK – task_id: {self._task_id}\n"))
            if self._task_id:
                self.after(0, self._start_progress_polling)
            else:
                # Backend bez task_id – symuluj 100%
                self.after(0, lambda: self._set_progress(100))
                self.after(0, self._ingest_done)
        except Exception as e:
            self.after(0, lambda: self._log(f"❌ Błąd uploadu: {e}\n"))
            self.after(0, self._ingest_done)

    def _start_progress_polling(self):
        self._polling = True
        self._poll_progress()

    def _poll_progress(self):
        if not self._polling:
            return
        threading.Thread(target=self._check_progress, daemon=True).start()

    def _check_progress(self):
        try:
            data = self.client.ingest_progress(self._task_id)
            pct  = data.get("progress", data.get("percent", 0))
            done = data.get("done", data.get("finished", pct >= 100))
            msg  = data.get("message", data.get("status", ""))
            self.after(0, lambda: self._set_progress(pct))
            if msg:
                self.after(0, lambda: self._log(f"  {msg}\n"))
            if done:
                self._polling = False
                self.after(0, self._ingest_done)
            else:
                self.after(POLL_INTERVAL_MS, self._poll_progress)
        except Exception as e:
            self.after(0, lambda: self._log(f"⚠️ Poll error: {e}\n"))
            self.after(POLL_INTERVAL_MS, self._poll_progress)

    def _set_progress(self, pct: float):
        self._progress_var.set(pct)
        self.progress_label.config(text=f"{int(pct)} %")

    def _ingest_done(self):
        self._set_progress(100)
        self._log("🏁 Ingestia zakończona.\n")
        self.btn_ingest.config(state=NORMAL)
        self.status_bar_var.set("Ingestia zakończona.")

    def _log(self, text: str):
        self.log.config(state=NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.config(state=DISABLED)


# ─────────────────────────────────────────────────────────────
#  TAB: STATUS SYSTEMU
# ─────────────────────────────────────────────────────────────
class StatusTab(ttk.Frame):
    def __init__(self, parent, client: APIClient, status_bar_var: tk.StringVar):
        super().__init__(parent)
        self.client         = client
        self.status_bar_var = status_bar_var
        self._auto_refresh  = tk.BooleanVar(value=True)
        self._build_ui()
        self._schedule_refresh()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ── Backend health ──
        health_lf = ttk.LabelFrame(self, text=" 🟢 Backend Health ", bootstyle=SUCCESS, padding=12)
        health_lf.grid(row=0, column=0, sticky=NSEW, padx=(12, 6), pady=12)
        health_lf.columnconfigure(1, weight=1)

        self._health_labels = {}
        for i, key in enumerate(["status", "version", "uptime", "llm_loaded"]):
            ttk.Label(health_lf, text=f"{key}:", bootstyle=SECONDARY).grid(
                row=i, column=0, sticky=W, pady=2
            )
            lbl = ttk.Label(health_lf, text="—", bootstyle=INFO)
            lbl.grid(row=i, column=1, sticky=W, padx=(8, 0))
            self._health_labels[key] = lbl

        # ── VRAM ──
        vram_lf = ttk.LabelFrame(self, text=" 🔥 VRAM (AMD Instinct) ", bootstyle=WARNING, padding=12)
        vram_lf.grid(row=0, column=1, sticky=NSEW, padx=(6, 12), pady=12)
        vram_lf.columnconfigure(0, weight=1)

        self.vram_meter = ttk.Meter(
            vram_lf,
            metersize=160,
            amounttotal=16384,  # 16 GB AMD Instinct w MB
            amountused=0,
            subtext="VRAM MB",
            bootstyle=WARNING,
            interactive=False,
        )
        self.vram_meter.grid(row=0, column=0, pady=4)

        self._vram_detail = ttk.Label(vram_lf, text="Ładowanie…", bootstyle=SECONDARY)
        self._vram_detail.grid(row=1, column=0)

        # ── Modele ──
        models_lf = ttk.LabelFrame(self, text=" 🤖 Załadowane Modele ", bootstyle=INFO, padding=10)
        models_lf.grid(row=1, column=0, columnspan=2, sticky=NSEW, padx=12, pady=(0, 8))
        models_lf.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.models_text = scrolledtext.ScrolledText(
            models_lf, height=8, state="disabled",
            font=("Consolas", 9), bg="#181825", fg="#a6adc8", relief="flat"
        )
        self.models_text.grid(row=0, column=0, sticky=NSEW)

        # ── Przyciski ──
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(4, 12))

        ttk.Button(
            btn_frame, text="🔄 Odśwież teraz",
            bootstyle=INFO, command=self._refresh_all, width=18
        ).pack(side=LEFT, padx=6)

        ttk.Checkbutton(
            btn_frame, text="Auto-odświeżanie (5s)",
            variable=self._auto_refresh, bootstyle="info-round-toggle"
        ).pack(side=LEFT, padx=6)

    # ── Refresh logic ─────────────────────────────────────────
    def _refresh_all(self):
        self.status_bar_var.set("Odświeżanie statusu…")
        threading.Thread(target=self._fetch_all, daemon=True).start()

    def _fetch_all(self):
        self._fetch_health()
        self._fetch_vram()
        self._fetch_models()
        self.after(0, lambda: self.status_bar_var.set("Status odświeżony."))

    def _fetch_health(self):
        try:
            data = self.client.health()
            self.after(0, lambda: self._update_health(data))
        except Exception as e:
            self.after(0, lambda: self._update_health({"status": f"❌ {e}"}))

    def _update_health(self, data: dict):
        defaults = {"status": "—", "version": "—", "uptime": "—", "llm_loaded": "—"}
        merged   = {**defaults, **data}
        for key, lbl in self._health_labels.items():
            val = merged.get(key, "—")
            lbl.config(text=str(val))
            if key == "status":
                lbl.config(bootstyle=SUCCESS if "ok" in str(val).lower() else DANGER)

    def _fetch_vram(self):
        try:
            data = self.client.vram_status()
            self.after(0, lambda: self._update_vram(data))
        except Exception:
            pass

    def _update_vram(self, data: dict):
        used = int(
            data.get("vram_used_mb",
            data.get("used_mb",
            data.get("used", 0)))
        )
        total = int(
            data.get("vram_total_mb",
            data.get("total_mb",
            data.get("total", 16384)))
        )
        self.vram_meter.configure(amountused=used, amounttotal=max(total, 1))
        pct = round(used / max(total, 1) * 100, 1)
        self._vram_detail.config(text=f"{used} MB / {total} MB  ({pct}%)")
        style = SUCCESS if pct < 50 else (WARNING if pct < 80 else DANGER)
        self.vram_meter.configure(bootstyle=style)

    def _fetch_models(self):
        try:
            data = self.client.models_info()
            self.after(0, lambda: self._update_models(data))
        except Exception:
            pass

    def _update_models(self, data: dict):
        self.models_text.config(state=NORMAL)
        self.models_text.delete("1.0", tk.END)
        self.models_text.insert(tk.END, json.dumps(data, indent=2, ensure_ascii=False))
        self.models_text.config(state=DISABLED)

    def _schedule_refresh(self):
        if self._auto_refresh.get():
            self._refresh_all()
        self.after(VRAM_REFRESH_MS, self._schedule_refresh)


# ─────────────────────────────────────────────────────────────
#  TAB: USTAWIENIA
# ─────────────────────────────────────────────────────────────
class SettingsTab(ttk.Frame):
    def __init__(self, parent, client: APIClient, status_bar_var: tk.StringVar):
        super().__init__(parent)
        self.client         = client
        self.status_bar_var = status_bar_var
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        conn_lf = ttk.LabelFrame(self, text=" 🔌 Połączenie z backendem ", bootstyle=INFO, padding=14)
        conn_lf.grid(row=0, column=0, sticky=EW, padx=16, pady=20)
        conn_lf.columnconfigure(1, weight=1)

        ttk.Label(conn_lf, text="URL backendu:").grid(row=0, column=0, sticky=W)
        self.url_var = tk.StringVar(value=self.client.base_url)
        ttk.Entry(conn_lf, textvariable=self.url_var, font=("Consolas", 11)).grid(
            row=0, column=1, sticky=EW, padx=(10, 0), ipady=4
        )

        ttk.Button(
            conn_lf, text="💾 Zastosuj i testuj połączenie",
            bootstyle=SUCCESS, command=self._apply_url
        ).grid(row=1, column=0, columnspan=2, pady=(12, 0), ipadx=10, ipady=4)

        self.test_result = ttk.Label(conn_lf, text="", bootstyle=SECONDARY)
        self.test_result.grid(row=2, column=0, columnspan=2, pady=(8, 0))

        # ── Informacja ──
        info_lf = ttk.LabelFrame(self, text=" ℹ️  O aplikacji ", bootstyle=SECONDARY, padding=14)
        info_lf.grid(row=1, column=0, sticky=EW, padx=16, pady=6)

        info_text = (
            "KlimtechRAG Desktop GUI\n"
            "─────────────────────────────────────────\n"
            "Klient TTKBootstrap dla systemu KlimtechRAG.\n"
            "Backend działa niezależnie jako serwis FastAPI.\n\n"
            "Stack: FastAPI + Haystack 2.x + Qdrant + llama.cpp\n"
            "LLM:   Bielik-4.5B-v3.0-Instruct\n"
            "GPU:   AMD Instinct (ROCm)\n\n"
            "Pipelines:\n"
            "  • text    – e5-large (teksty, dokumenty)\n"
            "  • colpali – PDF/skany (bez OCR)\n"
            "  • vlm     – LFM2.5-VL (obrazy w PDF)\n"
        )
        ttk.Label(info_lf, text=info_text, font=("Consolas", 9), justify=LEFT, bootstyle=SECONDARY).pack(
            anchor=W
        )

    def _apply_url(self):
        new_url = self.url_var.get().strip().rstrip("/")
        self.client.base_url = new_url
        self.test_result.config(text="Testowanie…", bootstyle=INFO)
        threading.Thread(target=self._test_connection, daemon=True).start()

    def _test_connection(self):
        try:
            data = self.client.health()
            status = data.get("status", "ok")
            self.after(0, lambda: self.test_result.config(
                text=f"✅ Połączono! Status: {status}", bootstyle=SUCCESS
            ))
            self.after(0, lambda: self.status_bar_var.set(f"Backend: {self.client.base_url}"))
        except Exception as e:
            self.after(0, lambda: self.test_result.config(
                text=f"❌ Błąd: {e}", bootstyle=DANGER
            ))


# ─────────────────────────────────────────────────────────────
#  GŁÓWNE OKNO APLIKACJI
# ─────────────────────────────────────────────────────────────
class KlimtechApp(ttk.Window):
    def __init__(self):
        super().__init__(
            title="KlimtechRAG Desktop",
            themename="darkly",
            size=(1050, 720),
            minsize=(800, 560),
        )

        self.client          = APIClient(DEFAULT_API_URL)
        self.status_bar_var  = tk.StringVar(value="Gotowe.")
        self._build_ui()
        self._initial_health_check()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Notebook (taby) ──
        nb = ttk.Notebook(self, bootstyle=INFO)
        nb.grid(row=0, column=0, sticky=NSEW, padx=0, pady=0)

        self.chat_tab     = ChatTab(nb,     self.client, self.status_bar_var)
        self.ingest_tab   = IngestTab(nb,   self.client, self.status_bar_var)
        self.status_tab   = StatusTab(nb,   self.client, self.status_bar_var)
        self.settings_tab = SettingsTab(nb, self.client, self.status_bar_var)

        nb.add(self.chat_tab,     text="  💬 Chat  ")
        nb.add(self.ingest_tab,   text="  📤 Ingestia  ")
        nb.add(self.status_tab,   text="  📊 System  ")
        nb.add(self.settings_tab, text="  ⚙️  Ustawienia  ")

        # ── Status bar ──
        status_bar = ttk.Label(
            self,
            textvariable=self.status_bar_var,
            bootstyle=SECONDARY,
            font=("Consolas", 8),
            anchor=W,
            padding=(8, 2),
        )
        status_bar.grid(row=1, column=0, sticky=EW)

    def _initial_health_check(self):
        def check():
            try:
                data = self.client.health()
                st   = data.get("status", "?")
                self.after(0, lambda: self.status_bar_var.set(
                    f"✅ Backend połączony – {self.client.base_url}  |  status: {st}"
                ))
            except Exception:
                self.after(0, lambda: self.status_bar_var.set(
                    f"⚠️  Backend niedostępny pod {self.client.base_url}  –  sprawdź Ustawienia"
                ))
        threading.Thread(target=check, daemon=True).start()


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
def main():
    app = KlimtechApp()
    app.mainloop()


if __name__ == "__main__":
    main()
