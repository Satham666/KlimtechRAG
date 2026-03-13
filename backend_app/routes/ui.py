"""
KlimtechRAG — Web UI
Serwowany na http://<IP>:8000/

Tryb INGEST (start_backend_gpu.py):
  - Upload plików z wyborem trybu (normalny / VLM dla PDF z grafikami)
  - Podgląd statystyk Qdrant i file_registry

Tryb CZAT (start_klimtech.py):
  - Chat z RAG (Bielik + baza wiedzy)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KlimtechRAG</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600&display=swap');

  :root {
    --bg:       #0d1117;
    --surface:  #161b22;
    --border:   #30363d;
    --accent:   #58a6ff;
    --green:    #3fb950;
    --orange:   #d29922;
    --red:      #f85149;
    --purple:   #bc8cff;
    --text:     #e6edf3;
    --muted:    #8b949e;
    --radius:   10px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── HEADER ── */
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  header h1 { font-size: 18px; font-weight: 600; }
  header h1 span { color: var(--accent); }

  .mode-badge {
    margin-left: auto;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
  }
  .mode-badge.ingest { border-color: var(--green); color: var(--green); }
  .mode-badge.chat   { border-color: var(--purple); color: var(--purple); }

  /* ── TABS ── */
  .tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    background: var(--surface);
  }
  .tab {
    padding: 12px 20px;
    cursor: pointer;
    font-size: 14px;
    color: var(--muted);
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
    user-select: none;
  }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-color: var(--accent); }

  /* ── MAIN ── */
  main { flex: 1; padding: 24px; max-width: 960px; width: 100%; margin: 0 auto; }

  .panel { display: none; }
  .panel.active { display: block; }

  /* ── CARDS ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    margin-bottom: 16px;
  }
  .card h2 {
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: 14px;
  }

  /* ── DROP ZONE ── */
  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 36px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 16px;
  }
  .drop-zone:hover, .drop-zone.drag-over {
    border-color: var(--accent);
    background: rgba(88,166,255,.05);
  }
  .drop-zone .icon { font-size: 32px; margin-bottom: 8px; }
  .drop-zone .label { color: var(--muted); font-size: 14px; }
  .drop-zone .label strong { color: var(--accent); }
  #file-input { display: none; }

  /* ── SELECTED FILES LIST ── */
  #selected-files {
    margin-bottom: 14px;
  }
  .file-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 6px;
    font-size: 13px;
  }
  .file-item .fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .file-item .fsize { color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 11px; }
  .file-item .fpdf-badge {
    font-size: 10px; padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid var(--orange);
    color: var(--orange);
  }
  .file-item .frmv {
    cursor: pointer; color: var(--muted);
    background: none; border: none; font-size: 16px; line-height: 1;
    transition: color 0.15s;
  }
  .file-item .frmv:hover { color: var(--red); }

  /* ── OPTIONS ── */
  .option-row {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .opt-btn {
    flex: 1; min-width: 160px;
    padding: 12px;
    background: var(--bg);
    border: 2px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    text-align: center;
    transition: all 0.15s;
    color: var(--text);
  }
  .opt-btn:hover { border-color: var(--muted); }
  .opt-btn.selected { border-color: var(--accent); background: rgba(88,166,255,.07); }
  .opt-btn .opt-icon { font-size: 22px; margin-bottom: 4px; }
  .opt-btn .opt-name { font-size: 13px; font-weight: 600; }
  .opt-btn .opt-desc { font-size: 11px; color: var(--muted); margin-top: 2px; }

  /* ── BUTTONS ── */
  .btn {
    padding: 10px 22px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-primary { background: var(--accent); color: #000; }
  .btn-primary:hover { filter: brightness(1.1); }
  .btn-primary:disabled { opacity: .45; cursor: not-allowed; }
  .btn-danger  { background: var(--red);  color: #fff; margin-left: 8px; }
  .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }

  /* ── PROGRESS ── */
  #progress-section { display: none; }
  .progress-bar-wrap {
    background: var(--bg);
    border-radius: 4px;
    height: 8px;
    margin: 8px 0 16px;
    overflow: hidden;
  }
  .progress-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.4s;
    width: 0%;
  }

  /* ── LOG ── */
  #log-box {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    max-height: 220px;
    overflow-y: auto;
    line-height: 1.7;
  }
  .log-ok     { color: var(--green); }
  .log-err    { color: var(--red); }
  .log-warn   { color: var(--orange); }
  .log-info   { color: var(--accent); }
  .log-muted  { color: var(--muted); }

  /* ── STATS ── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
    margin-bottom: 12px;
  }
  .stat-box {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    text-align: center;
  }
  .stat-box .stat-val {
    font-size: 26px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
  }
  .stat-box .stat-lbl { font-size: 11px; color: var(--muted); margin-top: 2px; }

  /* ── CHAT ── */
  #chat-messages {
    height: 420px;
    overflow-y: auto;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 14px;
  }
  .msg {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }
  .msg-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    background: var(--border);
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0;
  }
  .msg.user .msg-avatar  { background: rgba(88,166,255,.2); }
  .msg.bot  .msg-avatar  { background: rgba(63,185,80,.2); }
  .msg-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    line-height: 1.6;
    max-width: calc(100% - 50px);
    white-space: pre-wrap;
  }
  .msg.user .msg-bubble { border-color: rgba(88,166,255,.3); }
  .chat-input-row { display: flex; gap: 10px; }
  #chat-input {
    flex: 1;
    padding: 10px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 14px;
    resize: none;
    min-height: 44px;
    max-height: 120px;
  }
  #chat-input:focus { outline: none; border-color: var(--accent); }
  .typing-dots span {
    display: inline-block;
    animation: blink 1.2s infinite;
  }
  .typing-dots span:nth-child(2) { animation-delay: .3s; }
  .typing-dots span:nth-child(3) { animation-delay: .6s; }
  @keyframes blink { 0%,80%,100%{opacity:.2} 40%{opacity:1} }

  /* ── STATUS DOT ── */
  .dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--muted);
    margin-right: 6px;
    vertical-align: middle;
  }
  .dot.ok     { background: var(--green); box-shadow: 0 0 4px var(--green); }
  .dot.err    { background: var(--red); }
  .dot.warn   { background: var(--orange); }

  .info-box {
    background: rgba(88,166,255,.08);
    border: 1px solid rgba(88,166,255,.25);
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: var(--accent);
    margin-bottom: 14px;
  }
</style>
</head>
<body>

<header>
  <span style="font-size:22px">🧠</span>
  <h1>Klimtech<span>RAG</span></h1>
  <div class="mode-badge" id="mode-badge">sprawdzam...</div>
</header>

<nav class="tabs">
  <div class="tab active" onclick="switchTab('upload')">📂 Wgraj pliki</div>
  <div class="tab" onclick="switchTab('stats')">📊 Statystyki</div>
  <div class="tab" onclick="switchTab('chat')">💬 Czat RAG</div>
</nav>

<main>

<!-- ══════════════════════════════════════════════
     TAB: UPLOAD
══════════════════════════════════════════════ -->
<div class="panel active" id="panel-upload">

  <div class="card">
    <h2>Tryb przetwarzania PDF</h2>
    <div class="option-row">
      <div class="opt-btn selected" id="opt-normal" onclick="selectMode('normal')">
        <div class="opt-icon">📄</div>
        <div class="opt-name">Normalny</div>
        <div class="opt-desc">Tekst / OCR<br>szybki, CPU+GPU</div>
      </div>
      <div class="opt-btn" id="opt-vlm" onclick="selectMode('vlm')">
        <div class="opt-icon">🖼️</div>
        <div class="opt-name">VLM — grafiki</div>
        <div class="opt-desc">Opisuje obrazy w PDF<br>przez model wizyjny</div>
      </div>
    </div>
    <div class="info-box" id="mode-info">
      <b>Tryb normalny:</b> pdftotext → jeśli pusty → OCR (Docling). Obsługuje PDF, TXT, DOCX i inne.
    </div>
  </div>

  <div class="card">
    <h2>Pliki do zaindeksowania</h2>

    <div class="drop-zone" id="drop-zone"
         onclick="document.getElementById('file-input').click()"
         ondragover="onDragOver(event)"
         ondragleave="onDragLeave(event)"
         ondrop="onDrop(event)">
      <div class="icon">📁</div>
      <div class="label">Przeciągnij pliki lub <strong>kliknij</strong></div>
      <div class="label" style="margin-top:4px;font-size:12px">PDF, TXT, DOCX, MD, JSON, JPG, PNG, MP3, MP4...</div>
    </div>
    <input type="file" id="file-input" multiple onchange="onFileSelect(event)">

    <div id="selected-files"></div>

    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <button class="btn btn-primary" id="btn-upload" onclick="startUpload()" disabled>
        📤 Zaindeksuj pliki
      </button>
      <button class="btn btn-outline" onclick="clearFiles()">🗑 Wyczyść</button>
      <span id="queue-info" style="font-size:13px;color:var(--muted)"></span>
    </div>
  </div>

  <div id="progress-section" class="card">
    <h2>Postęp</h2>
    <div id="progress-label" style="font-size:13px;color:var(--muted);margin-bottom:4px"></div>
    <div class="progress-bar-wrap"><div class="progress-bar" id="progress-bar"></div></div>
    <div id="log-box"></div>
  </div>

</div><!-- /panel-upload -->

<!-- ══════════════════════════════════════════════
     TAB: STATS
══════════════════════════════════════════════ -->
<div class="panel" id="panel-stats">

  <div class="card">
    <h2>Stan systemu</h2>
    <div id="health-row" style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:8px;font-size:13px">
      <span><span class="dot" id="dot-backend"></span>Backend</span>
      <span><span class="dot" id="dot-qdrant"></span>Qdrant</span>
      <span><span class="dot" id="dot-llm"></span>LLM (llama)</span>
      <span><span class="dot" id="dot-vlm"></span>VLM (port 8083)</span>
    </div>
    <div style="font-size:12px;color:var(--muted)" id="embed-info"></div>
  </div>

  <div class="card">
    <h2>File Registry</h2>
    <div class="stats-grid" id="stats-grid">
      <div class="stat-box"><div class="stat-val" id="s-total">—</div><div class="stat-lbl">Pliki łącznie</div></div>
      <div class="stat-box"><div class="stat-val" id="s-indexed">—</div><div class="stat-lbl">Zindeksowane</div></div>
      <div class="stat-box"><div class="stat-val" id="s-pending">—</div><div class="stat-lbl">Oczekujące</div></div>
      <div class="stat-box"><div class="stat-val" id="s-errors">—</div><div class="stat-lbl">Błędy</div></div>
      <div class="stat-box"><div class="stat-val" id="s-chunks">—</div><div class="stat-lbl">Chunki Qdrant</div></div>
    </div>
    <button class="btn btn-outline" onclick="loadStats()">🔄 Odśwież</button>
  </div>

  <div class="card">
    <h2>Wektory Qdrant</h2>
    <div id="qdrant-info" style="font-size:13px;color:var(--muted)">Ładowanie...</div>
  </div>

</div><!-- /panel-stats -->

<!-- ══════════════════════════════════════════════
     TAB: CHAT
══════════════════════════════════════════════ -->
<div class="panel" id="panel-chat">

  <div class="info-box" id="chat-info-box">
    ⚠️ Czat działa gdy uruchomiony jest <b>start_klimtech.py</b> z modelem LLM (Bielik).
    Jeśli teraz jesteś w trybie GPU ingest (start_backend_gpu.py) — LLM nie działa.
  </div>

  <div class="card" style="padding:0;overflow:hidden">
    <div id="chat-messages"></div>
    <div style="padding:14px;border-top:1px solid var(--border)">
      <div class="chat-input-row">
        <textarea id="chat-input" rows="1" placeholder="Zadaj pytanie na podstawie zaindeksowanych dokumentów..."
                  onkeydown="chatKeydown(event)"></textarea>
        <button class="btn btn-primary" id="btn-send" onclick="sendChat()">Wyślij</button>
      </div>
    </div>
  </div>

</div><!-- /panel-chat -->

</main>

<script>
// ────────────────────────────────────────────────
// STATE
// ────────────────────────────────────────────────
let selectedFiles = [];   // File objects
let ingestMode = 'normal'; // 'normal' | 'vlm'
let uploading = false;

// ────────────────────────────────────────────────
// TABS
// ────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',['upload','stats','chat'][i]===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+name).classList.add('active');
  if(name==='stats') loadStats();
  if(name==='chat')  checkLLM();
}

// ────────────────────────────────────────────────
// MODE SELECTION
// ────────────────────────────────────────────────
function selectMode(m) {
  ingestMode = m;
  document.getElementById('opt-normal').classList.toggle('selected', m==='normal');
  document.getElementById('opt-vlm').classList.toggle('selected', m==='vlm');
  document.getElementById('mode-info').innerHTML = m==='normal'
    ? '<b>Tryb normalny:</b> pdftotext → jeśli pusty → OCR (Docling). Obsługuje PDF, TXT, DOCX i inne.'
    : '<b>Tryb VLM:</b> Wyodrębnia obrazy z PDF i opisuje je modelem wizyjnym (LFM2.5-VL). Tekst i opisy trafiają razem do Qdrant. Wolniejszy, ale uwzględnia diagramy i schematy.';
}

// ────────────────────────────────────────────────
// FILE HANDLING
// ────────────────────────────────────────────────
function onDragOver(e)  { e.preventDefault(); document.getElementById('drop-zone').classList.add('drag-over'); }
function onDragLeave(e) { document.getElementById('drop-zone').classList.remove('drag-over'); }
function onDrop(e)      { e.preventDefault(); document.getElementById('drop-zone').classList.remove('drag-over'); addFiles(e.dataTransfer.files); }
function onFileSelect(e){ addFiles(e.target.files); e.target.value=''; }

function addFiles(fileList) {
  for (const f of fileList) {
    if (!selectedFiles.find(x=>x.name===f.name && x.size===f.size)) selectedFiles.push(f);
  }
  renderFiles();
}

function removeFile(idx) { selectedFiles.splice(idx,1); renderFiles(); }
function clearFiles()    { selectedFiles=[]; renderFiles(); }

function renderFiles() {
  const cont = document.getElementById('selected-files');
  cont.innerHTML = '';
  selectedFiles.forEach((f,i)=>{
    const isPdf = f.name.toLowerCase().endsWith('.pdf');
    const sizeStr = f.size>1048576 ? (f.size/1048576).toFixed(1)+' MB' : (f.size/1024).toFixed(0)+' KB';
    cont.innerHTML += `
      <div class="file-item">
        <span>${isPdf?'📄':'📝'}</span>
        <span class="fname" title="${f.name}">${f.name}</span>
        <span class="fsize">${sizeStr}</span>
        ${isPdf?'<span class="fpdf-badge">PDF</span>':''}
        <button class="frmv" onclick="removeFile(${i})" title="Usuń">×</button>
      </div>`;
  });
  document.getElementById('btn-upload').disabled = selectedFiles.length===0 || uploading;
  document.getElementById('queue-info').textContent = selectedFiles.length ? `${selectedFiles.length} plik${selectedFiles.length>1?'ów':''}` : '';
}

// ────────────────────────────────────────────────
// UPLOAD & INGEST
// ────────────────────────────────────────────────
async function startUpload() {
  if (!selectedFiles.length || uploading) return;
  uploading = true;
  document.getElementById('btn-upload').disabled = true;

  const section = document.getElementById('progress-section');
  const logBox  = document.getElementById('log-box');
  const bar     = document.getElementById('progress-bar');
  const label   = document.getElementById('progress-label');
  section.style.display = 'block';
  logBox.innerHTML = '';
  bar.style.width = '0%';

  const total = selectedFiles.length;
  let done = 0;

  function log(msg, cls='log-info') {
    logBox.innerHTML += `<div class="${cls}">${msg}</div>`;
    logBox.scrollTop = logBox.scrollHeight;
  }

  log(`Tryb: <b>${ingestMode==='vlm'?'VLM (grafiki)':'Normalny'}</b> | Plików: ${total}`);

  for (let i=0; i<selectedFiles.length; i++) {
    const f = selectedFiles[i];
    label.textContent = `Plik ${i+1}/${total}: ${f.name}`;
    bar.style.width = Math.round((i/total)*100)+'%';

    const isPdf = f.name.toLowerCase().endsWith('.pdf');
    log(`<span class="log-muted">→ ${f.name}</span>`);

    try {
      // Krok 1: Upload pliku
      const fd = new FormData();
      fd.append('file', f);

      const fileSizeMB = (f.size / 1048576).toFixed(1);
      if (f.size > 50*1024*1024) {
        log(`  ⏳ Duży plik (${fileSizeMB} MB) — przesyłanie może potrwać...`, 'log-warn');
      }

      let upResp, rawText, upData;
      try {
        upResp = await fetch('/upload', { method:'POST', body: fd });
        rawText = await upResp.text();
      } catch(fetchErr) {
        log(`  ❌ Błąd połączenia: ${fetchErr.message}`, 'log-err');
        log(`  ℹ️  Sprawdź czy backend działa i czy plik nie jest za duży (limit 200MB)`, 'log-muted');
        continue;
      }

      // Parsuj JSON
      try {
        upData = JSON.parse(rawText);
      } catch(jsonErr) {
        log(`  ❌ Serwer zwrócił nie-JSON (HTTP ${upResp.status})`, 'log-err');
        log(`  📄 Odpowiedź: ${rawText.slice(0,300)}`, 'log-muted');
        continue;
      }

      // HTTP 200 ale body null — backend zwrócił None
      if (upData === null) {
        log(`  ❌ Backend zwrócił null (HTTP ${upResp.status}) — prawdopodobny błąd w ingest.py`, 'log-err');
        log(`  📄 Raw: ${rawText}`, 'log-muted');
        log(`  ℹ️  Uruchom: python3 ingest_fix.py  i zrestartuj backend`, 'log-warn');
        // Spróbuj sprawdzić /health żeby zobaczyć czy backend w ogóle działa
        try {
          const hResp = await fetch('/health');
          const hData = await hResp.json();
          log(`  🔍 Health: qdrant=${hData.qdrant} llm=${hData.llm} status=${hData.status}`, 'log-muted');
        } catch(e) {}
        continue;
      }

      if (!upResp.ok) {
        const detail = upData?.detail || upData?.message || rawText.slice(0,150);
        log(`  ❌ Upload błąd (HTTP ${upResp.status}): ${detail}`, 'log-err');
        log(`  📄 Pełna odpowiedź: ${rawText.slice(0,300)}`, 'log-muted');
        continue;
      }

      const savedPath = upData.saved_path || upData.path || null;
      log(`  ✅ Zapisano → ${upData.nextcloud_folder||'?'} | ${fileSizeMB} MB`, 'log-ok');

      if (!savedPath && ingestMode === 'vlm' && isPdf) {
        log(`  ⚠️  Brak saved_path w odpowiedzi — uruchom ingest_fix.py aby naprawić`, 'log-warn');
        log(`  ℹ️  Plik zapisany, ale VLM nie może go przetworzyć bez ścieżki`, 'log-muted');
        continue;
      }

      // Krok 2: Jeśli normalny tryb — backend już zaindeksował w tle, śledź postęp
      if (ingestMode === 'normal') {
        if (upData.indexing) {
          log(`  ⏳ Indeksowanie w tle...`, 'log-info');

          // Polling przez 30s żeby pokazać kiedy chunki pojawią się w bazie
          const normId = 'norm-progress-' + Date.now();
          logBox.innerHTML += `<div id="${normId}" class="log-muted">  ⏱️  Czekam na chunki w Qdrant...</div>`;
          logBox.scrollTop = logBox.scrollHeight;

          let chunksBefore2 = 0;
          try { const r = await fetch('/files/stats'); const d = await r.json(); chunksBefore2 = d.total_chunks||0; } catch(e){}

          await new Promise(resolve => {
            let attempts = 0;
            const t = setInterval(async () => {
              attempts++;
              try {
                const r = await fetch('/files/stats');
                const d = await r.json();
                const now = d.total_chunks || 0;
                const el = document.getElementById(normId);
                if (el) el.textContent = `  ⏱️  Indeksowanie... chunki w bazie: ${now} (+${now - chunksBefore2} nowych)`;
                if (now > chunksBefore2 || attempts >= 15) {
                  clearInterval(t);
                  if (el) el.remove();
                  if (now > chunksBefore2) {
                    log(`  ✅ Zaindeksowano: +${now - chunksBefore2} chunków (łącznie: ${now})`, 'log-ok');
                  } else {
                    log(`  ℹ️  Chunki będą widoczne za chwilę (indeksowanie async)`, 'log-muted');
                  }
                  resolve();
                }
              } catch(e) { attempts++; }
            }, 2000);
          });

        } else {
          log(`  ℹ️  Format zapisany, indeksowanie nie dotyczy tego typu pliku`, 'log-muted');
        }
      }

      // Krok 3: VLM dla PDF
      if (isPdf && ingestMode==='vlm' && savedPath) {
        log(`  🖼️  VLM: uruchamiam opis grafik w: ${f.name}`, 'log-warn');
        log(`  ⏳ To może potrwać kilka minut dla dużych PDF...`, 'log-muted');

        // Pobierz chunki PRZED — żeby liczyć przyrost
        let chunksBefore = 0;
        try {
          const sb = await fetch('/files/stats');
          const db = await sb.json();
          chunksBefore = db.total_chunks || 0;
        } catch(e) {}

        // Placeholder linii postępu — będziemy go aktualizować
        const progressId = 'vlm-progress-' + Date.now();
        logBox.innerHTML += `<div id="${progressId}" class="log-muted">  ⏱️  VLM pracuje... 0s | chunki: ${chunksBefore}</div>`;
        logBox.scrollTop = logBox.scrollHeight;

        const startTs = Date.now();
        let pollTimer = null;
        let lastChunks = chunksBefore;

        // Polling co 4s — aktualizuj linię postępu
        function startPolling() {
          pollTimer = setInterval(async () => {
            try {
              const sp = await fetch('/files/stats');
              const dp = await sp.json();
              const nowChunks = dp.total_chunks || 0;
              const elapsed   = Math.round((Date.now() - startTs) / 1000);
              const newChunks = nowChunks - chunksBefore;
              const el = document.getElementById(progressId);
              if (el) {
                const arrow = nowChunks > lastChunks ? ' ▲' : '';
                el.textContent = `  ⏱️  VLM pracuje... ${elapsed}s | chunki w bazie: ${nowChunks}${arrow} (+${newChunks} nowych)`;
                lastChunks = nowChunks;
              }
            } catch(e) {}
          }, 4000);
        }

        startPolling();

        try {
          const vlmResp = await fetch('/ingest_pdf_vlm', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ path: savedPath })
          });
          const vlmRaw = await vlmResp.text();
          let vlmData;
          try { vlmData = JSON.parse(vlmRaw); } catch(e) { vlmData = null; }

          clearInterval(pollTimer);
          const elapsed = Math.round((Date.now() - startTs) / 1000);

          // Usuń linię tymczasową
          const el = document.getElementById(progressId);
          if (el) el.remove();

          if (vlmResp.ok && vlmData) {
            log(`  ✅ VLM gotowe (${elapsed}s): ${vlmData.chunks_processed} chunków | VLM użyto: ${vlmData.vlm_used}`, 'log-ok');
          } else {
            const vlmErr = vlmData?.detail || vlmRaw.slice(0,100);
            log(`  ⚠️  VLM błąd po ${elapsed}s: ${vlmErr}`, 'log-warn');
          }
        } catch(vlmErr) {
          clearInterval(pollTimer);
          const el = document.getElementById(progressId);
          if (el) el.remove();
          log(`  ⚠️  VLM timeout/błąd: ${vlmErr.message}`, 'log-warn');
        }
      }

    } catch(e) {
      log(`  ❌ Nieoczekiwany błąd: ${e.message}`, 'log-err');
    }

    done++;
  }

  bar.style.width = '100%';
  bar.style.background = 'var(--green)';
  label.textContent = `✅ Gotowe — ${done}/${total} plików`;
  log(`\n🎉 Zakończono. Sprawdź zakładkę Statystyki.`, 'log-ok');
  log(`\nAby uruchomić czat: zatrzymaj backend (CTRL+C) i uruchom start_klimtech.py`, 'log-muted');

  uploading = false;
  selectedFiles = [];
  renderFiles();
  loadStats();
}

// ────────────────────────────────────────────────
// STATS
// ────────────────────────────────────────────────
async function loadStats() {
  // Health
  async function checkPort(url, dotId) {
    try {
      const r = await fetch(url, {signal: AbortSignal.timeout(2000)});
      document.getElementById(dotId).className = r.ok ? 'dot ok' : 'dot err';
    } catch { document.getElementById(dotId).className = 'dot err'; }
  }
  checkPort('/health',             'dot-backend');
  checkPort('http://'+location.hostname+':6333/collections', 'dot-qdrant');
  checkPort('http://'+location.hostname+':8082/health',      'dot-llm');
  checkPort('http://'+location.hostname+':8083/health',      'dot-vlm');

  // File stats
  try {
    const r = await fetch('/files/stats');
    const d = await r.json();
    document.getElementById('s-total').textContent   = d.total_files   ?? '—';
    document.getElementById('s-indexed').textContent = d.indexed       ?? '—';
    document.getElementById('s-pending').textContent = d.pending       ?? '—';
    document.getElementById('s-errors').textContent  = d.errors        ?? '—';
    document.getElementById('s-chunks').textContent  = d.total_chunks  ?? '—';
  } catch { }

  // RAG debug → embedding info + Qdrant
  try {
    const r = await fetch('/rag/debug?query=test');
    const d = await r.json();
    document.getElementById('embed-info').textContent =
      `Embedding: ${d.embedding_device||'?'} | Model: ${d.embedding_model||'?'}`;
    document.getElementById('qdrant-info').innerHTML =
      `<b>Punkty:</b> ${d.qdrant_points??'?'} | <b>Zindeksowane:</b> ${d.qdrant_indexed??'?'}` +
      (d.retrieved_docs!=null ? ` | <b>Retrieval test:</b> ${d.retrieved_docs} docs` : '');
  } catch {
    document.getElementById('embed-info').textContent = 'Nie można pobrać danych';
  }
}

// ────────────────────────────────────────────────
// CHAT
// ────────────────────────────────────────────────
let chatHistory = [];

function chatKeydown(e) {
  if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}

function addChatMsg(role, content) {
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ' + (role==='user'?'user':'bot');
  div.innerHTML = `
    <div class="msg-avatar">${role==='user'?'👤':'🤖'}</div>
    <div class="msg-bubble">${content}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div.querySelector('.msg-bubble');
}

async function checkLLM() {
  try {
    const r = await fetch('http://'+location.hostname+':8082/health', {signal:AbortSignal.timeout(2000)});
    if (r.ok) document.getElementById('chat-info-box').style.display='none';
  } catch { }
}

async function sendChat() {
  const inp = document.getElementById('chat-input');
  const query = inp.value.trim();
  if (!query) return;
  inp.value = '';
  document.getElementById('btn-send').disabled = true;

  addChatMsg('user', query);
  chatHistory.push({role:'user', content: query});

  const bubble = addChatMsg('bot',
    '<span class="typing-dots"><span>●</span><span>●</span><span>●</span></span>');

  try {
    const r = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        model: 'klimtech-rag',
        messages: chatHistory,
        use_rag: true,
        top_k: 5
      })
    });
    if (r.ok) {
      const d = await r.json();
      const ans = d.choices[0].message.content;
      bubble.textContent = ans;
      chatHistory.push({role:'assistant', content: ans});
    } else {
      const err = await r.json().catch(()=>({detail:'Błąd '+r.status}));
      bubble.innerHTML = `<span style="color:var(--red)">❌ ${err.detail||r.status}</span>`;
    }
  } catch(e) {
    bubble.innerHTML = `<span style="color:var(--red)">❌ ${e.message}</span>`;
  }

  document.getElementById('btn-send').disabled = false;
  document.getElementById('chat-input').focus();
}

// ────────────────────────────────────────────────
// INIT
// ────────────────────────────────────────────────
async function detectMode() {
  const badge = document.getElementById('mode-badge');
  try {
    // Jeśli LLM działa → tryb czat
    const r = await fetch('http://'+location.hostname+':8082/health', {signal:AbortSignal.timeout(1500)});
    if (r.ok) {
      badge.textContent = '💬 tryb czat';
      badge.className = 'mode-badge chat';
      return;
    }
  } catch { }
  badge.textContent = '📂 tryb ingest';
  badge.className = 'mode-badge ingest';
}

// Pobierz saved_path z upload response (dodajemy to do backendu przez patch)
// — jeśli backend tego nie zwraca, VLM fallback do /ingest_pdf_vlm bez ścieżki nie zadziała;
// dlatego UI wyświetli ostrzeżenie.

window.addEventListener('DOMContentLoaded', ()=>{
  detectMode();
  // Wiadomość powitalna czat
  addChatMsg('bot', 'Witaj! Jestem asystentem RAG. Zadaj pytanie — przeszukam zaindeksowane dokumenty i odpowiem na podstawie ich treści.\n\n⚠️ Czat wymaga działającego LLM (start_klimtech.py).');
});
</script>
</body>
</html>
"""

@router.get("/", response_class=HTMLResponse)
@router.get("/chat", response_class=HTMLResponse)
async def main_ui():
    return HTML
