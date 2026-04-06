(function () {
  "use strict";

  var WIDGET_VERSION = "1.0.0";
  var cfg = window.KlimtechWidget || {};
  var API_URL = cfg.apiUrl || window.location.origin;
  var API_KEY = cfg.apiKey || "sk-local";
  var PLACEHOLDER = cfg.placeholder || "Zadaj pytanie…";
  var TITLE = cfg.title || "KlimtechRAG";
  var USE_RAG = cfg.useRag !== undefined ? cfg.useRag : false;
  var POSITION = cfg.position || "right";

  var CSS = [
    "#kw-btn{position:fixed;bottom:24px;" + (POSITION === "left" ? "left" : "right") + ":24px;",
    "width:56px;height:56px;border-radius:50%;background:#1a6cf6;color:#fff;border:none;",
    "font-size:24px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);z-index:9998;}",
    "#kw-box{display:none;position:fixed;bottom:92px;" + (POSITION === "left" ? "left" : "right") + ":24px;",
    "width:360px;max-height:500px;background:#fff;border-radius:12px;",
    "box-shadow:0 8px 32px rgba(0,0,0,.2);z-index:9999;flex-direction:column;overflow:hidden;}",
    "#kw-box.open{display:flex;}",
    "#kw-header{background:#1a6cf6;color:#fff;padding:12px 16px;font-weight:600;font-size:15px;",
    "display:flex;justify-content:space-between;align-items:center;}",
    "#kw-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;line-height:1;}",
    "#kw-msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;}",
    ".kw-msg{max-width:85%;padding:8px 12px;border-radius:10px;font-size:14px;line-height:1.5;word-wrap:break-word;}",
    ".kw-user{align-self:flex-end;background:#1a6cf6;color:#fff;border-bottom-right-radius:2px;}",
    ".kw-bot{align-self:flex-start;background:#f0f0f0;color:#222;border-bottom-left-radius:2px;}",
    ".kw-typing{color:#888;font-style:italic;font-size:13px;}",
    "#kw-form{display:flex;border-top:1px solid #e0e0e0;padding:8px;}",
    "#kw-input{flex:1;border:1px solid #ddd;border-radius:8px;padding:8px 12px;font-size:14px;outline:none;}",
    "#kw-send{background:#1a6cf6;color:#fff;border:none;border-radius:8px;",
    "padding:8px 14px;margin-left:6px;cursor:pointer;font-size:14px;}"
  ].join("");

  function injectStyles() {
    var s = document.createElement("style");
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function buildUI() {
    var btn = document.createElement("button");
    btn.id = "kw-btn";
    btn.title = TITLE;
    btn.textContent = "💬";

    var box = document.createElement("div");
    box.id = "kw-box";
    box.innerHTML = [
      "<div id='kw-header'><span>" + TITLE + "</span><button id='kw-close'>✕</button></div>",
      "<div id='kw-msgs'></div>",
      "<form id='kw-form'><input id='kw-input' placeholder='" + PLACEHOLDER + "' autocomplete='off'/>",
      "<button type='submit' id='kw-send'>➤</button></form>"
    ].join("");

    document.body.appendChild(btn);
    document.body.appendChild(box);

    btn.addEventListener("click", function () { box.classList.toggle("open"); });
    document.getElementById("kw-close").addEventListener("click", function () { box.classList.remove("open"); });
    document.getElementById("kw-form").addEventListener("submit", handleSubmit);
  }

  function addMsg(text, role) {
    var msgs = document.getElementById("kw-msgs");
    var d = document.createElement("div");
    d.className = "kw-msg " + (role === "user" ? "kw-user" : "kw-bot");
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  function handleSubmit(e) {
    e.preventDefault();
    var input = document.getElementById("kw-input");
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMsg(text, "user");
    var typing = addMsg("…", "bot kw-typing");
    sendMessage(text, typing);
  }

  function sendMessage(text, typingEl) {
    var body = JSON.stringify({
      model: "klimtech-rag",
      messages: [{ role: "user", content: text }],
      use_rag: USE_RAG,
      stream: false
    });

    var xhr = new XMLHttpRequest();
    xhr.open("POST", API_URL + "/v1/chat/completions", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.setRequestHeader("Authorization", "Bearer " + API_KEY);

    xhr.onload = function () {
      typingEl.remove();
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          var answer = data.choices[0].message.content;
          addMsg(answer, "bot");
        } catch (err) {
          addMsg("Błąd parsowania odpowiedzi.", "bot");
        }
      } else {
        addMsg("Błąd serwera (" + xhr.status + ").", "bot");
      }
    };
    xhr.onerror = function () {
      typingEl.remove();
      addMsg("Brak połączenia z backendem.", "bot");
    };
    xhr.send(body);
  }

  function init() {
    injectStyles();
    buildUI();
    console.log("[KlimtechWidget] v" + WIDGET_VERSION + " załadowany");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
