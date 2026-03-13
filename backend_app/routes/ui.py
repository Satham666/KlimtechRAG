"""
routes/ui.py — Interfejs KlimtechRAG
Wbudowane poprawki:
  - loadFiles()    : rozpakowanie {count, files:[]} z /files/pending
  - checkStatus()  : używa /model/status zamiast brakującego /v1/models na :8000
  - toggleVLM()    : wywołuje POST /model/switch/vlm|llm przez API
  - indexed_today  : obsługuje brak pola w stats
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI"])

_HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>KlimtechRAG</title>
<style>
/* ── RESET & TOKENS ─────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg0:  #0c0d14;
  --bg1:  #13141f;
  --bg2:  #1a1b28;
  --bg3:  #22243a;
  --bg4:  #2b2d48;
  --line: rgba(255,255,255,.07);
  --a:    #4ecda4;
  --ah:   #38b48d;
  --ad:   rgba(78,205,164,.15);
  --blue: #5b8dee;
  --bd:   rgba(91,141,238,.18);
  --warn: #f6c90e;
  --err:  #f87171;
  --t1:   #e8eaf0;
  --t2:   #9497b0;
  --t3:   #5c5e7a;
  --rad:  12px;
  --sh:   0 4px 24px rgba(0,0,0,.45);
}

html, body { height: 100%; overflow: hidden; font-family: 'SF Pro Display', 'Segoe UI', system-ui, sans-serif; background: var(--bg0); color: var(--t1); }

/* ── SCROLLBAR ───────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 99px; }

/* ── LAYOUT ──────────────────────────────────────────── */
.shell { display: flex; flex-direction: column; height: 100vh; }

/* TOPBAR */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 54px; flex-shrink: 0;
  background: var(--bg1); border-bottom: 1px solid var(--line);
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-gem {
  width: 28px; height: 28px; border-radius: 8px;
  background: linear-gradient(135deg, var(--a), var(--blue));
  display: grid; place-items: center; font-size: 15px; flex-shrink: 0;
}
.logo-name { font-size: 16px; font-weight: 600; letter-spacing: -.3px; }
.logo-ver  { font-size: 11px; color: var(--t3); margin-left: 2px; }

.status-pill {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 14px; border-radius: 99px;
  background: var(--bg3); font-size: 13px; color: var(--t2);
  cursor: default; user-select: none;
}
.dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--t3); transition: background .4s;
  flex-shrink: 0;
}
.dot.on  { background: var(--a);    box-shadow: 0 0 6px var(--a); }
.dot.err { background: var(--err);  box-shadow: 0 0 6px var(--err); }
.dot.busy { background: var(--warn); animation: pulse 1s infinite; }
@keyframes pulse { 50% { opacity: .4; } }

/* BODY */
.body { display: flex; flex: 1; overflow: hidden; }

/* ── SIDEBAR ─────────────────────────────────────────── */
.sidebar {
  width: 300px; flex-shrink: 0;
  display: flex; flex-direction: column; gap: 0;
  background: var(--bg1); border-right: 1px solid var(--line);
  overflow-y: auto;
}

.sb-section {
  padding: 18px 20px;
  border-bottom: 1px solid var(--line);
}
.sb-label {
  font-size: 10px; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--t3); margin-bottom: 12px;
}

/* UPLOAD DROP */
.drop {
  border: 1.5px dashed var(--bg4);
  border-radius: var(--rad); padding: 22px 16px;
  text-align: center; cursor: pointer;
  transition: border-color .2s, background .2s;
}
.drop:hover, .drop.over { border-color: var(--a); background: var(--ad); }
.drop-icon { font-size: 28px; margin-bottom: 8px; opacity: .7; }
.drop-text { font-size: 13px; color: var(--t2); line-height: 1.5; }
.drop-hint { font-size: 11px; color: var(--t3); margin-top: 4px; }
input[type=file] { display: none; }

/* PROGRESS */
.prog-wrap { margin-top: 10px; display: none; }
.prog-wrap.show { display: block; }
.prog-bar { height: 4px; background: var(--bg4); border-radius: 99px; overflow: hidden; }
.prog-fill { height: 100%; background: var(--a); width: 0; transition: width .3s; border-radius: 99px; }
.prog-text { font-size: 11px; color: var(--t3); margin-top: 5px; }

/* VLM TOGGLE */
.vlm-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 12px;
}
.vlm-info .vlm-title { font-size: 13px; font-weight: 500; }
.vlm-info .vlm-sub   { font-size: 11px; color: var(--t3); margin-top: 1px; }

.tog-track {
  position: relative; width: 40px; height: 22px;
  background: var(--bg4); border-radius: 99px;
  cursor: pointer; transition: background .3s; flex-shrink: 0;
}
.tog-track.on { background: var(--a); }
.tog-track.busy { pointer-events: none; opacity: .6; }
.tog-thumb {
  position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; background: #fff;
  border-radius: 50%; transition: transform .25s;
}
.tog-track.on .tog-thumb { transform: translateX(18px); }

/* STATS */
.stats-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.stat {
  background: var(--bg2); border-radius: 10px;
  padding: 12px 14px;
}
.stat-val { font-size: 22px; font-weight: 700; color: var(--a); line-height: 1; }
.stat-lbl { font-size: 11px; color: var(--t3); margin-top: 4px; }

/* FILES LIST */
.file-list { display: flex; flex-direction: column; gap: 1px; }
.file-row {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 0; border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.file-row:last-child { border-bottom: none; }
.file-row .ico { font-size: 14px; flex-shrink: 0; }
.file-row .fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--t2); }
.badge {
  padding: 2px 7px; border-radius: 99px; font-size: 10px; font-weight: 600;
  flex-shrink: 0;
}
.badge.pending  { background: rgba(246,201,14,.15); color: var(--warn); }
.badge.indexed  { background: rgba(78,205,164,.15); color: var(--a); }
.badge.error    { background: rgba(248,113,113,.15); color: var(--err); }
.empty-msg { font-size: 12px; color: var(--t3); text-align: center; padding: 12px 0; }

/* ── CHAT PANEL ──────────────────────────────────────── */
.chat-wrap { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.messages {
  flex: 1; overflow-y: auto; padding: 32px 40px;
  display: flex; flex-direction: column; gap: 24px;
  scroll-behavior: smooth;
}

/* WELCOME */
.welcome {
  margin: auto;
  max-width: 520px; text-align: center;
  opacity: 0; animation: fadeup .5s .1s forwards;
}
.welcome-gem {
  width: 52px; height: 52px; border-radius: 14px;
  background: linear-gradient(135deg, var(--a), var(--blue));
  display: grid; place-items: center; font-size: 26px;
  margin: 0 auto 18px;
}
.welcome h1 { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
.welcome p  { font-size: 14px; color: var(--t2); line-height: 1.7; }
.welcome-tips {
  margin-top: 24px; display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
}
.tip {
  padding: 7px 14px; border-radius: 99px;
  background: var(--bg3); border: 1px solid var(--line);
  font-size: 12px; color: var(--t2); cursor: pointer;
  transition: background .15s, color .15s;
}
.tip:hover { background: var(--ad); color: var(--a); border-color: var(--a); }

@keyframes fadeup { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }

/* MESSAGES */
.msg { display: flex; gap: 12px; max-width: 82%; animation: fadeup .25s forwards; }
.msg.user { flex-direction: row-reverse; margin-left: auto; }

.av {
  width: 32px; height: 32px; border-radius: 50%;
  display: grid; place-items: center; font-size: 14px;
  flex-shrink: 0; align-self: flex-end;
}
.av.ai   { background: var(--ad); color: var(--a); }
.av.user { background: var(--bd); color: var(--blue); }

.bubble {
  padding: 13px 17px; border-radius: 16px;
  font-size: 14px; line-height: 1.7; max-width: 100%;
}
.msg.ai   .bubble {
  background: var(--bg2); border-bottom-left-radius: 4px;
  border: 1px solid var(--line);
}
.msg.user .bubble {
  background: var(--blue); color: #fff; border-bottom-right-radius: 4px;
}
.bubble pre {
  background: var(--bg0); border-radius: 8px;
  padding: 12px; margin: 10px 0; overflow-x: auto; font-size: 12px;
}
.bubble code {
  background: var(--bg0); padding: 2px 5px; border-radius: 4px; font-size: 12px;
}
.sources {
  margin-top: 10px; padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 11px; color: var(--t3);
}
.sources span { color: var(--a); margin-right: 4px; }

/* TYPING */
.typing { display: none; align-items: center; gap: 5px; padding: 0 40px 0; }
.typing.show { display: flex; }
.typing-dot {
  width: 7px; height: 7px; background: var(--a); border-radius: 50%;
  animation: bounce 1.3s infinite ease-in-out both;
}
.typing-dot:nth-child(2) { animation-delay: .16s; }
.typing-dot:nth-child(3) { animation-delay: .32s; }
@keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }
.typing-lbl { font-size: 13px; color: var(--t3); margin-left: 4px; }

/* INPUT BAR */
.input-bar {
  padding: 16px 40px 20px;
  background: var(--bg1); border-top: 1px solid var(--line);
  flex-shrink: 0;
}
.input-row { display: flex; align-items: flex-end; gap: 10px; }

.input-box {
  flex: 1; background: var(--bg2); border: 1.5px solid var(--bg4);
  border-radius: var(--rad); padding: 13px 16px;
  color: var(--t1); font-size: 14px; resize: none;
  min-height: 50px; max-height: 160px; line-height: 1.5;
  transition: border-color .2s; font-family: inherit;
}
.input-box:focus { outline: none; border-color: var(--a); }
.input-box::placeholder { color: var(--t3); }

.send-btn {
  width: 50px; height: 50px; flex-shrink: 0;
  background: var(--a); color: var(--bg0);
  border: none; border-radius: var(--rad);
  font-size: 20px; cursor: pointer;
  display: grid; place-items: center;
  transition: background .15s, transform .1s;
}
.send-btn:hover:not(:disabled) { background: var(--ah); transform: scale(1.04); }
.send-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; }

.input-hint { font-size: 11px; color: var(--t3); margin-top: 7px; text-align: center; }

/* RESPONSIVE */
@media (max-width: 760px) {
  .sidebar { width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--line); flex-shrink: 0; max-height: 40vh; }
  .body { flex-direction: column; }
  .messages { padding: 20px; }
  .input-bar { padding: 12px 20px 16px; }
}
</style>
</head>
<body>
<div class="shell">

  <!-- TOPBAR -->
  <header class="topbar">
    <div class="logo">
      <div class="logo-gem">🤖</div>
      <span class="logo-name">KlimtechRAG</span>
      <span class="logo-ver">v3</span>
    </div>
    <div class="status-pill">
      <div class="dot" id="dot"></div>
      <span id="statusTxt">Sprawdzam...</span>
    </div>
  </header>

  <div class="body">

    <!-- SIDEBAR -->
    <aside class="sidebar">

      <!-- UPLOAD -->
      <div class="sb-section">
        <div class="sb-label">Wgraj pliki</div>
        <div class="drop" id="drop">
          <div class="drop-icon">📁</div>
          <div class="drop-text">Przeciągnij lub kliknij</div>
          <div class="drop-hint">PDF · DOCX · TXT · MD (max 50 MB)</div>
          <input type="file" id="fileIn" multiple accept=".pdf,.docx,.doc,.txt,.md,.json">
        </div>
        <div class="prog-wrap" id="progWrap">
          <div class="prog-bar"><div class="prog-fill" id="progFill"></div></div>
          <div class="prog-text" id="progTxt">Przygotowuję...</div>
        </div>

        <!-- VLM TOGGLE -->
        <div class="vlm-row">
          <div class="vlm-info">
            <div class="vlm-title">Tryb VLM</div>
            <div class="vlm-sub">PDF ze zdjęciami / rysunkami</div>
          </div>
          <div class="tog-track" id="togTrack" onclick="toggleVLM()">
            <div class="tog-thumb"></div>
          </div>
        </div>
      </div>

      <!-- STATS -->
      <div class="sb-section">
        <div class="sb-label">Statystyki</div>
        <div class="stats-grid">
          <div class="stat"><div class="stat-val" id="sDocs">–</div><div class="stat-lbl">Dokumenty</div></div>
          <div class="stat"><div class="stat-val" id="sChunks">–</div><div class="stat-lbl">Chunki</div></div>
          <div class="stat"><div class="stat-val" id="sPending">–</div><div class="stat-lbl">Do indeksu</div></div>
          <div class="stat"><div class="stat-val" id="sToday">–</div><div class="stat-lbl">Dzisiaj</div></div>
        </div>
      </div>

      <!-- FILES -->
      <div class="sb-section">
        <div class="sb-label">Ostatnie pliki</div>
        <div id="fileList" class="file-list">
          <div class="empty-msg">Ładowanie...</div>
        </div>
      </div>

    </aside>

    <!-- CHAT -->
    <div class="chat-wrap">
      <div class="messages" id="msgs">
        <div class="welcome" id="welcome">
          <div class="welcome-gem">🤖</div>
          <h1>Witaj w KlimtechRAG</h1>
          <p>Zadaj pytanie — przeszukam zaindeksowane dokumenty<br>i odpowiem na podstawie ich treści.</p>
          <div class="welcome-tips">
            <div class="tip" onclick="useTip(this)">Co zawierają moje dokumenty?</div>
            <div class="tip" onclick="useTip(this)">Podsumuj najważniejsze informacje</div>
            <div class="tip" onclick="useTip(this)">Szukaj informacji o...</div>
          </div>
        </div>
      </div>

      <div class="typing" id="typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <span class="typing-lbl">Asystent pisze...</span>
      </div>

      <div class="input-bar">
        <div class="input-row">
          <textarea class="input-box" id="input"
            placeholder="Zadaj pytanie..." rows="1"></textarea>
          <button class="send-btn" id="sendBtn" onclick="send()" title="Wyślij (Enter)">➤</button>
        </div>
        <div class="input-hint">Enter — wyślij &nbsp;·&nbsp; Shift+Enter — nowa linia</div>
      </div>
    </div>

  </div>
</div>

<script>
// ── CONFIG ────────────────────────────────────────────
const B = window.location.origin;
let vlmOn = false;
let switching = false;

// ── INIT ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadFiles();
  checkStatus();
  setInterval(() => { loadStats(); checkStatus(); }, 30_000);
});

// ── STATUS (FIX: używa /model/status zamiast /v1/models) ──
async function checkStatus() {
  const dot = document.getElementById('dot');
  const txt = document.getElementById('statusTxt');
  try {
    const r = await fetch(`${B}/model/status`, { signal: AbortSignal.timeout(4000) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    dot.className = 'dot ' + (d.running ? 'on' : 'err');
    if (d.running) {
      txt.textContent = d.model_type === 'vlm' ? 'VLM aktywny' : 'LLM aktywny';
      // Synchronizuj suwak ze stanem serwera
      if (!switching) setVLMVisual(d.model_type === 'vlm');
    } else {
      txt.textContent = 'Model zatrzymany';
    }
  } catch {
    dot.className = 'dot err';
    txt.textContent = 'Backend niedostępny';
  }
}

// ── VLM TOGGLE (FIX: wywołuje API zamiast tylko CSS) ──
async function toggleVLM() {
  if (switching) return;
  switching = true;

  const track = document.getElementById('togTrack');
  const txt   = document.getElementById('statusTxt');
  const dot   = document.getElementById('dot');

  vlmOn = !vlmOn;
  setVLMVisual(vlmOn);
  track.classList.add('busy');
  dot.className = 'dot busy';
  txt.textContent = vlmOn ? 'Przełączam na VLM...' : 'Przełączam na LLM...';

  try {
    const type = vlmOn ? 'vlm' : 'llm';
    const r = await fetch(`${B}/model/switch/${type}`, {
      method: 'POST',
      signal: AbortSignal.timeout(90_000)   // ~20s na załadowanie modelu
    });
    const d = await r.json();
    if (!d.success) {
      vlmOn = !vlmOn;       // rollback
      setVLMVisual(vlmOn);
      txt.textContent = '⚠ ' + (d.message || 'Błąd przełączania');
      dot.className = 'dot err';
    } else {
      dot.className = 'dot on';
      txt.textContent = vlmOn ? 'VLM aktywny' : 'LLM aktywny';
    }
  } catch (e) {
    vlmOn = !vlmOn;          // rollback
    setVLMVisual(vlmOn);
    txt.textContent = 'Błąd połączenia';
    dot.className = 'dot err';
  } finally {
    track.classList.remove('busy');
    switching = false;
  }
}

function setVLMVisual(on) {
  vlmOn = on;
  document.getElementById('togTrack').classList.toggle('on', on);
}

// ── STATS ─────────────────────────────────────────────
async function loadStats() {
  try {
    const r = await fetch(`${B}/files/stats`);
    if (!r.ok) return;
    const d = await r.json();
    document.getElementById('sDocs').textContent    = d.total_files ?? '–';
    document.getElementById('sChunks').textContent  = d.total_chunks ?? '–';
    document.getElementById('sPending').textContent = d.pending ?? '–';
    document.getElementById('sToday').textContent   = d.indexed_today ?? '–';
  } catch {}
}

// ── FILES (FIX: rozpakowanie {count, files:[]} z /files/pending) ──
async function loadFiles() {
  const el = document.getElementById('fileList');
  try {
    const r = await fetch(`${B}/files/pending`);
    if (!r.ok) throw new Error();
    const json = await r.json();
    // Endpoint zwraca {count:N, files:[...]}  ← klucz poprawki
    const list = Array.isArray(json) ? json : (json.files ?? []);
    if (!list.length) {
      el.innerHTML = '<div class="empty-msg">Brak plików do indeksowania</div>';
      return;
    }
    el.innerHTML = list.slice(0, 10).map(f => `
      <div class="file-row">
        <span class="ico">📄</span>
        <span class="fname" title="${f.filename ?? f}">${f.filename ?? f}</span>
        <span class="badge ${f.status ?? 'pending'}">${
          f.status === 'indexed' ? '✓' :
          f.status === 'error'   ? '!' : '…'
        }</span>
      </div>`).join('');
  } catch {
    el.innerHTML = '<div class="empty-msg">Błąd ładowania</div>';
  }
}

// ── UPLOAD ────────────────────────────────────────────
const drop = document.getElementById('drop');
const fileIn = document.getElementById('fileIn');
const progWrap = document.getElementById('progWrap');
const progFill = document.getElementById('progFill');
const progTxt  = document.getElementById('progTxt');

drop.addEventListener('click', () => fileIn.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); handleFiles(e.dataTransfer.files); });
fileIn.addEventListener('change', () => handleFiles(fileIn.files));

async function handleFiles(files) {
  if (!files.length) return;
  const endpoint = vlmOn ? '/ingest?use_vlm=1' : '/ingest';
  progWrap.classList.add('show');
  let done = 0;
  for (const file of files) {
    progTxt.textContent = `Wysyłam: ${file.name}`;
    const fd = new FormData();
    fd.append('file', file);
    try {
      await fetch(`${B}${endpoint}`, { method: 'POST', body: fd });
    } catch {}
    done++;
    progFill.style.width = (done / files.length * 100) + '%';
  }
  progTxt.textContent = `Gotowe (${done} plików)`;
  setTimeout(() => {
    progWrap.classList.remove('show');
    progFill.style.width = '0';
    loadStats(); loadFiles();
  }, 2500);
}

// ── CHAT ──────────────────────────────────────────────
const input   = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const msgs    = document.getElementById('msgs');
const typing  = document.getElementById('typing');
const welcome = document.getElementById('welcome');

input.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 160) + 'px';
});
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

function useTip(el) {
  input.value = el.textContent.replace('...', '');
  input.focus();
}

async function send() {
  const text = input.value.trim();
  if (!text) return;

  welcome?.remove();

  addMsg(text, 'user');
  input.value = '';
  input.style.height = 'auto';
  sendBtn.disabled = true;
  typing.classList.add('show');
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const r = await fetch(`${B}/v1/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [{ role: 'user', content: text }],
        stream: false
      })
    });
    const d = await r.json();
    typing.classList.remove('show');
    sendBtn.disabled = false;
    const answer = d.choices?.[0]?.message?.content ?? 'Brak odpowiedzi';
    addMsg(answer, 'ai', d.sources);
  } catch (e) {
    typing.classList.remove('show');
    sendBtn.disabled = false;
    addMsg('❌ Błąd połączenia z backendem. Sprawdź czy serwer działa.', 'ai');
  }
  msgs.scrollTop = msgs.scrollHeight;
}

function addMsg(text, role, sources) {
  const d = document.createElement('div');
  d.className = `msg ${role}`;

  const safe = text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/```([\s\S]*?)```/g, (_,c) => `<pre><code>${c.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g, (_,c) => `<code>${c}</code>`)
    .replace(/\n/g, '<br>');

  const srcHtml = sources?.length
    ? `<div class="sources"><span>📎</span>${sources.join(', ')}</div>` : '';

  d.innerHTML = `
    <div class="av ${role}">${role === 'ai' ? '🤖' : '👤'}</div>
    <div class="bubble">${safe}${srcHtml}</div>`;
  msgs.appendChild(d);
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def main_ui():
    return HTMLResponse(content=_HTML)
