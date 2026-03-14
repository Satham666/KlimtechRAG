"""
routes/ui.py — KlimtechRAG Interface v4
Nowe funkcje:
  - Trwałość czatu (localStorage) — przeżywa odświeżenie strony
  - Historia sesji w sidebarze (wiele rozmów)
  - Eksport aktywnej sesji do pliku JSON
  - Import sesji z pliku JSON
  - Poprawki: VLM toggle API, loadFiles fix, status fix
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
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg0:#0b0c15;--bg1:#11121e;--bg2:#181929;--bg3:#1f2035;--bg4:#272844;
  --line:rgba(255,255,255,.065);
  --a:#4ecda4;--ah:#38b48d;--ad:rgba(78,205,164,.12);
  --blue:#5b8dee;--bd:rgba(91,141,238,.16);
  --warn:#f6c90e;--err:#f87171;
  --t1:#e8eaf0;--t2:#9094b0;--t3:#51547a;
  --r:10px;
}
html,body{height:100%;overflow:hidden;
  font-family:'SF Pro Text','Segoe UI',system-ui,sans-serif;
  background:var(--bg0);color:var(--t1);font-size:14px}
::-webkit-scrollbar{width:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--bg4);border-radius:99px}

/* SHELL */
.shell{display:flex;height:100vh;overflow:hidden}

/* RAIL — historia sesji */
.rail{width:220px;flex-shrink:0;display:flex;flex-direction:column;
  background:var(--bg1);border-right:1px solid var(--line);overflow:hidden}
.rail-head{padding:14px 14px 10px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:8px}
.rail-logo{width:26px;height:26px;border-radius:7px;flex-shrink:0;
  background:linear-gradient(135deg,var(--a),var(--blue));
  display:grid;place-items:center;font-size:13px}
.rail-brand{font-size:13px;font-weight:600;flex:1}
.rail-brand small{display:block;font-size:10px;color:var(--t3);font-weight:400}
.btn-new{width:28px;height:28px;border-radius:7px;flex-shrink:0;
  background:var(--ad);border:1px solid var(--a);color:var(--a);
  font-size:18px;cursor:pointer;display:grid;place-items:center;
  transition:background .15s;line-height:1}
.btn-new:hover{background:rgba(78,205,164,.22)}

.sessions{flex:1;overflow-y:auto;padding:8px}
.sess-item{display:flex;align-items:center;gap:6px;
  padding:8px 10px;border-radius:8px;cursor:pointer;
  transition:background .12s;margin-bottom:2px;user-select:none;
  border:1px solid transparent}
.sess-item:hover{background:var(--bg3)}
.sess-item.active{background:var(--ad);border-color:rgba(78,205,164,.2)}
.sess-icon{font-size:14px;flex-shrink:0}
.sess-meta{flex:1;min-width:0}
.sess-title{font-size:12px;font-weight:500;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sess-date{font-size:10px;color:var(--t3);margin-top:1px}
.sess-del{opacity:0;font-size:12px;color:var(--t3);cursor:pointer;
  padding:2px 5px;border-radius:4px;flex-shrink:0;transition:opacity .12s,color .12s}
.sess-item:hover .sess-del{opacity:1}
.sess-del:hover{color:var(--err)}

.rail-foot{padding:10px 10px;border-top:1px solid var(--line);display:flex;gap:5px}
.rail-btn{flex:1;padding:7px 3px;border-radius:7px;
  background:var(--bg3);border:1px solid var(--line);color:var(--t2);
  font-size:10px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;gap:3px;
  transition:background .12s,color .12s;font-family:inherit}
.rail-btn:hover{background:var(--bg4);color:var(--t1)}
.rail-btn.danger:hover{background:rgba(248,113,113,.1);color:var(--err)}
.rail-btn label{cursor:pointer}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}

/* TOPBAR */
.topbar{display:flex;align-items:center;justify-content:space-between;
  padding:0 20px;height:50px;flex-shrink:0;
  background:var(--bg1);border-bottom:1px solid var(--line);gap:12px}
.topbar-title{font-size:13px;font-weight:500;color:var(--t2);flex:1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.status-pill{display:flex;align-items:center;gap:7px;flex-shrink:0;
  padding:5px 12px;border-radius:99px;background:var(--bg3);
  font-size:12px;color:var(--t2)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--t3);
  flex-shrink:0;transition:background .3s}
.dot.on {background:var(--a);box-shadow:0 0 5px var(--a)}
.dot.err{background:var(--err);box-shadow:0 0 5px var(--err)}
.dot.busy{background:var(--warn);animation:blink 1s infinite}
@keyframes blink{50%{opacity:.3}}

/* LAYOUT */
.layout{display:flex;flex:1;overflow:hidden}

/* SIDEBAR */
.sidebar{width:255px;flex-shrink:0;overflow-y:auto;
  background:var(--bg1);border-right:1px solid var(--line);
  display:flex;flex-direction:column}
.sb-s{padding:14px 14px;border-bottom:1px solid var(--line)}
.sb-lbl{font-size:10px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--t3);margin-bottom:10px}

/* DROP */
.drop{border:1.5px dashed var(--bg4);border-radius:var(--r);
  padding:18px 12px;text-align:center;cursor:pointer;
  transition:border-color .2s,background .2s}
.drop:hover,.drop.over{border-color:var(--a);background:var(--ad)}
.drop-icon{font-size:24px;margin-bottom:6px;opacity:.7}
.drop-text{font-size:12px;color:var(--t2);line-height:1.5}
.drop-hint{font-size:10px;color:var(--t3);margin-top:3px}
input[type=file]{display:none}
.prog-wrap{margin-top:10px;display:none}
.prog-wrap.show{display:block}
.prog-bar{height:3px;background:var(--bg4);border-radius:99px;overflow:hidden}
.prog-fill{height:100%;background:var(--a);width:0;transition:width .3s;border-radius:99px}
.prog-txt{font-size:10px;color:var(--t3);margin-top:4px}

/* VLM */
.vlm-row{display:flex;align-items:center;justify-content:space-between;margin-top:12px}
.vlm-title{font-size:12px;font-weight:500}
.vlm-sub{font-size:10px;color:var(--t3);margin-top:1px}
.tog{position:relative;width:36px;height:20px;background:var(--bg4);
  border-radius:99px;cursor:pointer;transition:background .25s;flex-shrink:0}
.tog.on{background:var(--a)}
.tog.busy{pointer-events:none;opacity:.6}
.tog-th{position:absolute;top:2px;left:2px;width:16px;height:16px;
  background:#fff;border-radius:50%;transition:transform .22s}
.tog.on .tog-th{transform:translateX(16px)}

/* STATS */
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.stat{background:var(--bg2);border-radius:8px;padding:10px 12px}
.stat-val{font-size:20px;font-weight:700;color:var(--a);line-height:1}
.stat-lbl{font-size:10px;color:var(--t3);margin-top:3px}

/* FILES */
.flist{display:flex;flex-direction:column;gap:1px}
.frow{display:flex;align-items:center;gap:7px;padding:7px 0;
  border-bottom:1px solid var(--line);font-size:11px}
.frow:last-child{border-bottom:none}
.frow .ico{font-size:13px;flex-shrink:0}
.frow .fn{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--t2)}
.badge{padding:2px 6px;border-radius:99px;font-size:9px;font-weight:700;flex-shrink:0}
.badge.pending{background:rgba(246,201,14,.12);color:var(--warn)}
.badge.indexed{background:rgba(78,205,164,.12);color:var(--a)}
.badge.error  {background:rgba(248,113,113,.12);color:var(--err)}
.empty{font-size:11px;color:var(--t3);text-align:center;padding:10px 0}

/* CHAT */
.chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.messages{flex:1;overflow-y:auto;padding:28px 36px;
  display:flex;flex-direction:column;gap:20px;scroll-behavior:smooth}

/* WELCOME */
.welcome{margin:auto;max-width:460px;text-align:center;
  opacity:0;animation:fu .5s .1s forwards}
.wgem{width:48px;height:48px;border-radius:13px;
  background:linear-gradient(135deg,var(--a),var(--blue));
  display:grid;place-items:center;font-size:24px;margin:0 auto 16px}
.welcome h1{font-size:19px;font-weight:600;margin-bottom:6px}
.welcome p{font-size:12px;color:var(--t2);line-height:1.7}
.tips{margin-top:18px;display:flex;flex-wrap:wrap;gap:7px;justify-content:center}
.tip{padding:6px 13px;border-radius:99px;background:var(--bg3);
  border:1px solid var(--line);font-size:11px;color:var(--t2);
  cursor:pointer;transition:background .12s,color .12s,border-color .12s}
.tip:hover{background:var(--ad);color:var(--a);border-color:var(--a)}
@keyframes fu{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

/* MESSAGES */
.msg{display:flex;gap:10px;max-width:80%;animation:fu .22s forwards}
.msg.user{flex-direction:row-reverse;margin-left:auto}
.av{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;
  font-size:13px;flex-shrink:0;align-self:flex-end}
.av.ai  {background:var(--ad);color:var(--a)}
.av.user{background:var(--bd);color:var(--blue)}
.bubble{padding:11px 15px;border-radius:14px;font-size:13px;line-height:1.7;max-width:100%}
.msg.ai   .bubble{background:var(--bg2);border-bottom-left-radius:3px;border:1px solid var(--line)}
.msg.user .bubble{background:var(--blue);color:#fff;border-bottom-right-radius:3px}
.bubble pre{background:var(--bg0);border-radius:7px;padding:10px;margin:8px 0;
  overflow-x:auto;font-size:11px;font-family:monospace}
.bubble code{background:var(--bg0);padding:1px 5px;border-radius:4px;font-size:11px;font-family:monospace}
.bubble strong{color:var(--a)}
.src{margin-top:8px;padding-top:8px;border-top:1px solid var(--line);
  font-size:10px;color:var(--t3)}
.src span{color:var(--a)}
.msg-time{font-size:9px;color:var(--t3);margin-top:3px;padding:0 2px}
.msg.user .msg-time{text-align:right}

/* TYPING */
.typing{display:none;align-items:center;gap:5px;padding:0 36px 4px}
.typing.show{display:flex}
.td{width:6px;height:6px;background:var(--a);border-radius:50%;
  animation:bounce 1.3s infinite ease-in-out both}
.td:nth-child(2){animation-delay:.16s}
.td:nth-child(3){animation-delay:.32s}
@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
.tl{font-size:12px;color:var(--t3);margin-left:4px}

/* INPUT */
.input-bar{padding:12px 36px 16px;background:var(--bg1);
  border-top:1px solid var(--line);flex-shrink:0}
.input-row{display:flex;align-items:flex-end;gap:8px}
.ibox{flex:1;background:var(--bg2);border:1.5px solid var(--bg4);
  border-radius:var(--r);padding:11px 14px;color:var(--t1);
  font-size:13px;resize:none;min-height:46px;max-height:150px;
  line-height:1.5;transition:border-color .2s;font-family:inherit}
.ibox:focus{outline:none;border-color:var(--a)}
.ibox::placeholder{color:var(--t3)}
.send{width:46px;height:46px;flex-shrink:0;background:var(--a);color:var(--bg0);
  border:none;border-radius:var(--r);font-size:18px;cursor:pointer;
  display:grid;place-items:center;transition:background .12s,transform .1s}
.send:hover:not(:disabled){background:var(--ah);transform:scale(1.04)}
.send:disabled{opacity:.35;cursor:not-allowed;transform:none}
.input-hint{font-size:10px;color:var(--t3);margin-top:6px;text-align:center}

/* MODAL */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.65);
  display:none;place-items:center;z-index:999}
.modal-bg.show{display:grid}
.modal{background:var(--bg2);border:1px solid var(--line);
  border-radius:14px;padding:24px;max-width:360px;width:90%;text-align:center}
.modal h3{font-size:15px;margin-bottom:10px}
.modal p{font-size:12px;color:var(--t2);line-height:1.6;margin-bottom:18px;white-space:pre-wrap}
.modal-btns{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
.mbtn{padding:8px 18px;border-radius:8px;border:1px solid var(--line);
  font-size:12px;cursor:pointer;transition:background .12s;font-family:inherit}
.mbtn.ok{background:var(--a);color:var(--bg0);border-color:var(--a)}
.mbtn.ok:hover{background:var(--ah)}
.mbtn.cancel{background:var(--bg3);color:var(--t2)}
.mbtn.cancel:hover{background:var(--bg4);color:var(--t1)}

/* TOAST */
.toast{position:fixed;bottom:24px;left:50%;
  transform:translateX(-50%) translateY(70px);
  background:var(--bg3);border:1px solid var(--line);border-radius:99px;
  padding:8px 20px;font-size:12px;color:var(--t1);z-index:1000;
  transition:transform .3s,opacity .3s;opacity:0;pointer-events:none}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1}

/* RESPONSIVE */
@media(max-width:900px){.rail{display:none}.sidebar{width:220px}}
@media(max-width:640px){.sidebar{display:none}
  .messages{padding:16px}.input-bar{padding:10px 16px 14px}}
</style>
</head>
<body>
<div class="shell">

  <!-- RAIL — sesje -->
  <nav class="rail">
    <div class="rail-head">
      <div class="rail-logo">🤖</div>
      <div class="rail-brand">KlimtechRAG<small>Historia rozmów</small></div>
      <button class="btn-new" onclick="newSession()" title="Nowa rozmowa">+</button>
    </div>
    <div class="sessions" id="sessionsEl"></div>
    <div class="rail-foot">
      <button class="rail-btn" onclick="exportChat()">⬇ Eksport</button>
      <label class="rail-btn">
        ⬆ Import
        <input type="file" id="importIn" accept=".json" onchange="importChat(event)">
      </label>
      <button class="rail-btn danger" onclick="clearAll()">🗑</button>
    </div>
  </nav>

  <!-- MAIN -->
  <div class="main">
    <header class="topbar">
      <div class="topbar-title" id="chatTitle">KlimtechRAG</div>
      <div class="status-pill">
        <div class="dot" id="dot"></div>
        <span id="statusTxt">Sprawdzam...</span>
      </div>
    </header>

    <div class="layout">

      <!-- SIDEBAR -->
      <aside class="sidebar">
        <div class="sb-s">
          <div class="sb-lbl">Wgraj pliki</div>
          <div class="drop" id="drop">
            <div class="drop-icon">📁</div>
            <div class="drop-text">Przeciągnij lub kliknij</div>
            <div class="drop-hint">PDF · DOCX · TXT · MD (max 50 MB)</div>
            <input type="file" id="fileIn" multiple accept=".pdf,.docx,.doc,.txt,.md,.json">
          </div>
          <div class="prog-wrap" id="progWrap">
            <div class="prog-bar"><div class="prog-fill" id="progFill"></div></div>
            <div class="prog-txt" id="progTxt"></div>
          </div>
          <div class="vlm-row">
            <div><div class="vlm-title">Tryb VLM</div><div class="vlm-sub">PDF ze zdjęciami</div></div>
            <div class="tog" id="tog" onclick="toggleVLM()"><div class="tog-th"></div></div>
          </div>
        </div>

        <div class="sb-s">
          <div class="sb-lbl">Statystyki</div>
          <div class="stats-grid">
            <div class="stat"><div class="stat-val" id="sDocs">–</div><div class="stat-lbl">Zaindeksowane</div></div>
            <div class="stat"><div class="stat-val" id="sChunks">–</div><div class="stat-lbl">Wektory RAG</div></div>
            <div class="stat"><div class="stat-val" id="sPending">–</div><div class="stat-lbl">Do indeksu</div></div>
            <div class="stat"><div class="stat-val" id="sToday">–</div><div class="stat-lbl">Dzisiaj</div></div>
          </div>
        </div>

        <div class="sb-s">
          <div class="sb-lbl">Indeksowanie RAG</div>
          <div id="embedStatus" style="font-size:11px;color:var(--t3);margin-bottom:8px">
            Kliknij aby zaindeksować oczekujące pliki
          </div>
          <div class="prog-wrap" id="embedProg">
            <div class="prog-bar"><div class="prog-fill" id="embedFill"></div></div>
            <div class="prog-txt" id="embedTxt"></div>
          </div>
          <button onclick="startEmbedding()" id="embedBtn" style="
            width:100%;padding:9px;border-radius:8px;border:1px solid var(--a);
            background:var(--ad);color:var(--a);font-size:12px;font-weight:600;
            cursor:pointer;transition:background .15s;font-family:inherit;margin-top:4px">
            🧠 Indeksuj pliki w RAG
          </button>
        </div>

        

        <div class="sb-s" style="flex:1">
          <div class="sb-lbl">Ostatnie pliki</div>
          <div id="fileList" class="flist"><div class="empty">Ładowanie...</div></div>
        </div>
      </aside>

      <!-- CHAT -->
      <div class="chat-area">
        <div class="messages" id="msgs"></div>

        <div class="typing" id="typing">
          <div class="td"></div><div class="td"></div><div class="td"></div>
          <span class="tl">Asystent pisze...</span>
        </div>

        <div class="input-bar">
          <div class="input-row">
            <textarea class="ibox" id="ibox" placeholder="Zadaj pytanie..." rows="1"></textarea>
            <button class="send" id="sendBtn" onclick="send()">➤</button>
          </div>
          <div class="input-hint">Enter — wyślij &nbsp;·&nbsp; Shift+Enter — nowa linia</div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- MODAL import -->
<div class="modal-bg" id="modalBg">
  <div class="modal">
    <h3>📥 Importuj czat</h3>
    <p id="modalDesc"></p>
    <div class="modal-btns">
      <button class="mbtn cancel" onclick="closeModal()">Anuluj</button>
      <button class="mbtn" onclick="doImport('new')">Nowa sesja</button>
      <button class="mbtn ok" onclick="doImport('replace')">Zastąp aktywną</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ── STORAGE KEYS ──────────────────────────────────────────
const LS_SESS   = 'klimtech_sessions';
const LS_ACTIVE = 'klimtech_active_id';

// ── STATE ─────────────────────────────────────────────────
const B = window.location.origin;
let vlmOn = false, switching = false;
let sessions = [], activeId = null, pendingImport = null;

// ── SESSION CRUD ──────────────────────────────────────────
function loadSessions(){
  try{ sessions = JSON.parse(localStorage.getItem(LS_SESS)||'[]'); }
  catch{ sessions=[]; }
  if(!Array.isArray(sessions)) sessions=[];
}
function saveSessions(){ localStorage.setItem(LS_SESS, JSON.stringify(sessions)); }
function getSess(id){ return sessions.find(s=>s.id===id)||null; }
function getActive(){ return getSess(activeId); }
function createSess(title){
  const id='sess_'+Date.now();
  const s={id, title:title||'Nowa rozmowa', ts:Date.now(), messages:[]};
  sessions.unshift(s); saveSessions(); return s;
}
function setActive(id){ activeId=id; localStorage.setItem(LS_ACTIVE,id); }

// ── INIT ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded',()=>{
  loadSessions();
  const saved = localStorage.getItem(LS_ACTIVE);
  if(saved && getSess(saved)){ setActive(saved); renderSession(saved); }
  else if(sessions.length){ setActive(sessions[0].id); renderSession(sessions[0].id); }
  else{ const s=createSess(); setActive(s.id); showWelcome(); }
  renderSidebar();
  loadStats(); loadFiles(); checkStatus();
  setInterval(()=>{ loadStats(); checkStatus(); }, 30_000);
});

// ── SIDEBAR ───────────────────────────────────────────────
function renderSidebar(){
  const el=document.getElementById('sessionsEl');
  if(!sessions.length){
    el.innerHTML='<div class="empty" style="padding:20px 8px">Brak rozmów</div>';
    return;
  }
  el.innerHTML=sessions.map(s=>`
    <div class="sess-item ${s.id===activeId?'active':''}" onclick="switchSess('${s.id}')">
      <span class="sess-icon">${s.messages.length?'💬':'✨'}</span>
      <div class="sess-meta">
        <div class="sess-title" title="${esc(s.title)}">${esc(s.title)}</div>
        <div class="sess-date">${fmtDate(s.ts)} · ${s.messages.length} wiad.</div>
      </div>
      <span class="sess-del" onclick="delSess(event,'${s.id}')" title="Usuń">✕</span>
    </div>`).join('');
}

function switchSess(id){
  if(id===activeId) return;
  setActive(id); renderSession(id); renderSidebar();
}

function renderSession(id){
  const sess=getSess(id);
  const msgsEl=document.getElementById('msgs');
  document.getElementById('chatTitle').textContent = sess ? sess.title : 'KlimtechRAG';
  msgsEl.innerHTML='';
  if(!sess||!sess.messages.length){ showWelcome(); return; }
  sess.messages.forEach(m=>appendMsgEl(m.role,m.content,m.sources,m.ts,false));
  msgsEl.scrollTop=msgsEl.scrollHeight;
}

function showWelcome(){
  const msgsEl=document.getElementById('msgs');
  msgsEl.innerHTML='';
  const w=document.createElement('div');
  w.className='welcome';
  w.innerHTML=`
    <div class="wgem">🤖</div>
    <h1>Witaj w KlimtechRAG</h1>
    <p>Zadaj pytanie — przeszukam zaindeksowane dokumenty<br>i odpowiem na podstawie ich treści.</p>
    <div class="tips">
      <div class="tip">Co zawierają moje dokumenty?</div>
      <div class="tip">Podsumuj najważniejsze informacje</div>
      <div class="tip">Szukaj informacji o...</div>
    </div>`;
  w.querySelectorAll('.tip').forEach(t=>t.addEventListener('click',()=>useTip(t)));
  msgsEl.appendChild(w);
}

function newSession(){
  const s=createSess(); setActive(s.id);
  renderSession(s.id); renderSidebar();
  document.getElementById('ibox').focus();
}

function delSess(e,id){
  e.stopPropagation();
  sessions=sessions.filter(s=>s.id!==id); saveSessions();
  if(id===activeId){
    if(sessions.length){ setActive(sessions[0].id); renderSession(sessions[0].id); }
    else{ const s=createSess(); setActive(s.id); showWelcome(); }
  }
  renderSidebar(); toast('Rozmowa usunięta');
}

function clearAll(){
  if(!confirm('Usunąć WSZYSTKIE rozmowy?')) return;
  sessions=[]; saveSessions();
  const s=createSess(); setActive(s.id); showWelcome();
  renderSidebar(); toast('Wszystkie rozmowy usunięte');
}

// ── EKSPORT ───────────────────────────────────────────────
function exportChat(){
  const sess=getActive();
  if(!sess){ toast('Brak aktywnej rozmowy'); return; }
  const payload={version:1, exported_at:new Date().toISOString(), app:'KlimtechRAG', session:sess};
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  const name=sess.title.replace(/[^a-zA-Z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ _-]/g,'').trim()||'czat';
  a.href=url; a.download=`klimtech_${name}_${fmtDateFile(sess.ts)}.json`; a.click();
  URL.revokeObjectURL(url);
  toast('✓ Wyeksportowano: '+a.download);
}

// ── IMPORT ────────────────────────────────────────────────
function importChat(ev){
  const file=ev.target.files[0]; if(!file) return;
  ev.target.value='';
  const reader=new FileReader();
  reader.onload=e=>{
    try{
      const data=JSON.parse(e.target.result);
      if(!data.session||!Array.isArray(data.session.messages)) throw new Error();
      pendingImport=data.session;
      document.getElementById('modalDesc').textContent=
        `Plik: "${file.name}"\nZawiera ${data.session.messages.length} wiadomości.\nCo chcesz zrobić?`;
      document.getElementById('modalBg').classList.add('show');
    }catch{ toast('❌ Nieprawidłowy plik JSON'); }
  };
  reader.readAsText(file);
}

function closeModal(){ document.getElementById('modalBg').classList.remove('show'); pendingImport=null; }

function doImport(mode){
  if(!pendingImport){ closeModal(); return; }
  if(mode==='replace'){
    const sess=getActive();
    if(sess){
      sess.title=pendingImport.title||sess.title;
      sess.messages=pendingImport.messages;
      sess.ts=pendingImport.ts||sess.ts;
      saveSessions(); renderSession(activeId); renderSidebar();
    }
  } else {
    const id='sess_'+Date.now();
    sessions.unshift({id, title:pendingImport.title||'Importowana rozmowa',
      ts:pendingImport.ts||Date.now(), messages:pendingImport.messages});
    saveSessions(); setActive(id); renderSession(id); renderSidebar();
  }
  closeModal(); toast('✓ Czat zaimportowany');
}

// ── STATUS ────────────────────────────────────────────────
async function checkStatus(){
  const dot=document.getElementById('dot'), txt=document.getElementById('statusTxt');
  try{
    const r=await fetch(`${B}/model/status`,{signal:AbortSignal.timeout(8000)});
    if(!r.ok) throw 0;
    const d=await r.json();
    dot.className='dot '+(d.running?'on':'err');
    if(!switching) setVLMVisual(d.model_type==='vlm');
    txt.textContent=d.running?(d.model_type==='vlm'?'VLM aktywny':d.model_type==='unknown'?'Model aktywny':'LLM aktywny'):'Model zatrzymany';
  }catch{ dot.className='dot err'; txt.textContent='Backend niedostępny'; }
}

// ── VLM TOGGLE ────────────────────────────────────────────
async function toggleVLM(){
  if(switching) return; switching=true;
  const tog=document.getElementById('tog');
  const txt=document.getElementById('statusTxt'), dot=document.getElementById('dot');
  vlmOn=!vlmOn; setVLMVisual(vlmOn);
  tog.classList.add('busy'); dot.className='dot busy';
  txt.textContent=vlmOn?'Przełączam na VLM...':'Przełączam na LLM...';
  try{
    const r=await fetch(`${B}/model/switch/${vlmOn?'vlm':'llm'}`,
      {method:'POST',signal:AbortSignal.timeout(90_000)});
    const d=await r.json();
    if(!d.success){ vlmOn=!vlmOn; setVLMVisual(vlmOn); txt.textContent='⚠ '+(d.message||'Błąd'); dot.className='dot err'; }
    else{ dot.className='dot on'; txt.textContent=vlmOn?'VLM aktywny':'LLM aktywny'; }
  }catch{ vlmOn=!vlmOn; setVLMVisual(vlmOn); txt.textContent='Błąd połączenia'; dot.className='dot err'; }
  finally{ tog.classList.remove('busy'); switching=false; }
}
function setVLMVisual(on){ vlmOn=on; document.getElementById('tog').classList.toggle('on',on); }

// ── STATS ─────────────────────────────────────────────────
async function loadStats(){
  try{
    const r=await fetch(`${B}/files/stats`); if(!r.ok) return;
    const d=await r.json();
    document.getElementById('sDocs').textContent   =d.indexed??'–';
    document.getElementById('sChunks').textContent =d.qdrant_points??d.total_chunks??'–';
    document.getElementById('sPending').textContent=d.pending??'–';
    document.getElementById('sToday').textContent  =d.indexed_today??'–';
  }catch{}
}

// ── FILES ─────────────────────────────────────────────────
async function loadFiles(){
  const el=document.getElementById('fileList');
  try{
    const r=await fetch(`${B}/files/pending`); if(!r.ok) throw 0;
    const json=await r.json();
    const list=Array.isArray(json)?json:(json.files??[]);
    if(!list.length){ el.innerHTML='<div class="empty">Brak plików do indeksowania</div>'; return; }
    el.innerHTML=list.slice(0,10).map(f=>`
      <div class="frow">
        <span class="ico">📄</span>
        <span class="fn" title="${esc(f.filename??f)}">${esc(f.filename??f)}</span>
        <span class="badge ${f.status??'pending'}">${
          f.status==='indexed'?'✓':f.status==='error'?'!':'…'}</span>
      </div>`).join('');
  }catch{ el.innerHTML='<div class="empty">Błąd ładowania</div>'; }
}

// ── UPLOAD ────────────────────────────────────────────────
const drop=document.getElementById('drop'), fileIn=document.getElementById('fileIn');
const progW=document.getElementById('progWrap'), progF=document.getElementById('progFill');
const progT=document.getElementById('progTxt');

drop.addEventListener('click',()=>fileIn.click());
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over');});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');handleFiles(e.dataTransfer.files);});
fileIn.addEventListener('change',()=>handleFiles(fileIn.files));

async function handleFiles(files){
  if(!files.length) return;
  progW.classList.add('show'); let done=0;
  for(const file of files){
    progT.textContent=`Wysyłam: ${file.name}`;
    const fd=new FormData(); fd.append('file',file);
    try{ await fetch(`${B}${vlmOn?'/ingest?use_vlm=1':'/ingest'}`,{method:'POST',body:fd}); }catch{}
    progF.style.width=(++done/files.length*100)+'%';
  }
  progT.textContent=`Gotowe (${done} plików)`;
  setTimeout(()=>{ progW.classList.remove('show'); progF.style.width='0'; loadStats(); loadFiles(); },2500);
}

// ── CHAT ──────────────────────────────────────────────────
const ibox=document.getElementById('ibox'), sendBtn=document.getElementById('sendBtn');
const msgsEl=document.getElementById('msgs'), typing=document.getElementById('typing');

ibox.addEventListener('input',function(){
  this.style.height='auto'; this.style.height=Math.min(this.scrollHeight,150)+'px';
});
ibox.addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();} });

function useTip(el){ ibox.value=el.textContent.replace('...',''); ibox.focus(); }

async function send(){
  const text=ibox.value.trim(); if(!text) return;

  // Usuń welcome
  msgsEl.querySelectorAll('.welcome').forEach(w=>w.remove());

  // Upewnij się że jest aktywna sesja
  let sess=getActive();
  if(!sess){ sess=createSess(); setActive(sess.id); renderSidebar(); }

  const now=Date.now();
  const userMsg={role:'user',content:text,sources:null,ts:now};
  sess.messages.push(userMsg);

  // Auto-tytuł z pierwszej wiadomości
  if(sess.messages.length===1){
    sess.title=text.length>40?text.slice(0,37)+'…':text;
    document.getElementById('chatTitle').textContent=sess.title;
  }
  saveSessions();
  appendMsgEl('user',text,null,now,true);
  ibox.value=''; ibox.style.height='auto';
  sendBtn.disabled=true; typing.classList.add('show');
  msgsEl.scrollTop=msgsEl.scrollHeight;

  try{
    const r=await fetch(`${B}/v1/chat/completions`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:[{role:'user',content:text}],stream:false})
    });
    const d=await r.json();
    typing.classList.remove('show'); sendBtn.disabled=false;
    const answer=d.choices?.[0]?.message?.content??'Brak odpowiedzi';
    const sources=d.sources??null;
    const aiTs=Date.now();
    sess.messages.push({role:'ai',content:answer,sources,ts:aiTs});
    saveSessions(); renderSidebar();
    appendMsgEl('ai',answer,sources,aiTs,true);
  }catch{
    typing.classList.remove('show'); sendBtn.disabled=false;
    const err='❌ Błąd połączenia z backendem. Sprawdź czy serwer działa.';
    sess.messages.push({role:'ai',content:err,sources:null,ts:Date.now()});
    saveSessions();
    appendMsgEl('ai',err,null,Date.now(),true);
  }
  msgsEl.scrollTop=msgsEl.scrollHeight;
}

function appendMsgEl(role,content,sources,ts,animate){
  const d=document.createElement('div');
  d.className=`msg ${role}`;
  const safe=content
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/```[\w]*\n?([\s\S]*?)```/g,(_,c)=>`<pre><code>${c.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g,(_,c)=>`<code>${c}</code>`)
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/\n/g,'<br>');
  const srcHtml=sources?.length?`<div class="src"><span>📎</span> ${sources.join(', ')}</div>`:'';
  d.innerHTML=`
    <div class="av ${role}">${role==='ai'?'🤖':'👤'}</div>
    <div>
      <div class="bubble">${safe}${srcHtml}</div>
      <div class="msg-time">${fmtTime(ts)}</div>
    </div>`;
  msgsEl.appendChild(d);
}

// ── HELPERS ───────────────────────────────────────────────
function esc(s){
  return String(s??'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDate(ts){
  const d=new Date(ts), now=new Date();
  if(d.toDateString()===now.toDateString())
    return d.toLocaleTimeString('pl',{hour:'2-digit',minute:'2-digit'});
  return d.toLocaleDateString('pl',{day:'2-digit',month:'2-digit'});
}
function fmtTime(ts){
  return new Date(ts).toLocaleTimeString('pl',{hour:'2-digit',minute:'2-digit'});
}
function fmtDateFile(ts){
  const d=new Date(ts);
  return `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}`;
}
async function startEmbedding(){
  var btn=document.getElementById("embedBtn");
  var status=document.getElementById("embedStatus");
  var prog=document.getElementById("embedProg");
  var fill=document.getElementById("embedFill");
  var txt=document.getElementById("embedTxt");
  var pending=0;
  try{var s=await fetch(B+"/files/stats").then(function(r){return r.json();});pending=s.pending||0;}catch(e){}
  if(pending===0){status.textContent="Brak plikow";status.style.color="var(--a)";return;}
  btn.disabled=true;btn.textContent="Indeksuje...";
  prog.classList.add("show");fill.style.width="5%";
  status.textContent="Indeksuje "+pending+" plikow...";status.style.color="var(--warn)";
  var poll=null;var attempts=0;
  fetch(B+"/ingest_all?limit="+pending,{method:"POST"}).then(function(r){return r.json();}).then(function(d){
    if(poll)clearInterval(poll);
    fill.style.width="100%";
    status.textContent="Zaindeksowano "+(d.indexed||0)+" plikow";
    status.style.color="var(--a)";
    btn.textContent="Indeksuj pliki w RAG";btn.disabled=false;
    setTimeout(function(){prog.classList.remove("show");},3000);
    loadStats();loadFiles();
  }).catch(function(e){
    if(poll)clearInterval(poll);
    status.textContent="Blad: "+e.message;status.style.color="var(--err)";
    btn.textContent="Indeksuj pliki w RAG";btn.disabled=false;
    prog.classList.remove("show");
  });
  poll=setInterval(function(){
    attempts++;
    fetch(B+"/files/stats").then(function(r){return r.json();}).then(function(s){
      var left=s.pending||0;
      fill.style.width=Math.min(95,5+((pending-left)/pending)*90)+"%";
      txt.textContent="Przetworzono: "+(pending-left)+"/"+pending;
      loadStats();
      if(left===0||attempts>60)clearInterval(poll);
    }).catch(function(){clearInterval(poll);});
  },3000);
}
function toast(msg,dur=2800){
  const el=document.getElementById('toast');
  el.textContent=msg; el.classList.add('show');
  clearTimeout(el._t); el._t=setTimeout(()=>el.classList.remove('show'),dur);
}
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def main_ui():
    return HTMLResponse(content=_HTML)
