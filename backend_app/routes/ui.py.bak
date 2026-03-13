"""
routes/ui.py — Responsywny interfejs KlimtechRAG
================================================

Układ:
- LEWA POŁOWA: Wgraj pliki (góra) + Statystyki (dół)
- PRAWA POŁOWA: Czat (pełna wysokość)

Responsywny: na małych ekranach układ pionowy
Nie wymaga nowych endpointów - działa z istniejącym backendem
"""
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List
import os
import json

router = APIRouter(tags=["UI"])

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------

BASE_DIR = os.environ.get("KLIMTECH_BASE_PATH", "/media/lobo/BACKUP/KlimtechRAG")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")


# ---------------------------------------------------------------------------
# GŁÓWNA STRONA UI
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def main_ui():
    """Główny interfejs - wszystko na jednej stronie."""
    
    html = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KlimtechRAG — System RAG</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg-primary: #0f0f1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #252542;
            --accent: #4ecca3;
            --accent-hover: #38a3a5;
            --danger: #ff6b6b;
            --warning: #ffd93d;
            --text-primary: #ffffff;
            --text-secondary: #b0b0c0;
            --border: #333355;
            --chat-user: #3b82f6;
            --chat-ai: #4ecca3;
        }
        
        html, body {
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow: hidden;
        }
        
        .app-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100%;
        }
        
        /* HEADER */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            z-index: 100;
        }
        
        .logo { display: flex; align-items: center; gap: 10px; }
        
        .logo-icon {
            width: 32px; height: 32px;
            background: linear-gradient(135deg, var(--accent), var(--accent-hover));
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px;
        }
        
        .logo-text { font-size: 20px; font-weight: 600; }
        
        .header-actions { display: flex; gap: 10px; align-items: center; }
        
        .model-status {
            display: flex; align-items: center; gap: 8px;
            padding: 8px 16px;
            background: var(--bg-card);
            border-radius: 20px;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: var(--danger);
            animation: pulse 2s infinite;
        }
        
        .status-dot.active { background: var(--accent); }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        /* MAIN CONTENT */
        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        /* LEFT COLUMN */
        .left-column {
            width: 45%;
            min-width: 350px;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
        }
        
        /* RIGHT COLUMN */
        .right-column {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-primary);
            min-width: 400px;
        }
        
        /* UPLOAD PANEL */
        .upload-panel {
            flex: 0 0 auto;
            max-height: 45%;
            padding: 20px;
            border-bottom: 1px solid var(--border);
            overflow-y: auto;
        }
        
        .panel-title {
            font-size: 16px; font-weight: 600;
            margin-bottom: 15px;
            display: flex; align-items: center; gap: 8px;
        }
        
        .drop-zone {
            border: 2px dashed var(--border);
            border-radius: 12px;
            padding: 30px 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(78, 204, 163, 0.05);
            transition: all 0.3s;
        }
        
        .drop-zone:hover, .drop-zone.dragover {
            border-color: var(--accent);
            background: rgba(78, 204, 163, 0.1);
        }
        
        .drop-zone-icon { font-size: 48px; margin-bottom: 10px; opacity: 0.7; }
        .drop-zone-text { color: var(--text-secondary); font-size: 14px; margin-bottom: 15px; }
        .drop-zone-hint { color: var(--text-secondary); font-size: 12px; opacity: 0.7; }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .btn-primary { background: var(--accent); color: var(--bg-primary); }
        .btn-primary:hover { background: var(--accent-hover); transform: translateY(-1px); }
        
        /* VLM TOGGLE */
        .vlm-toggle {
            display: flex; align-items: center; gap: 10px;
            margin-top: 15px;
            padding: 10px;
            background: var(--bg-card);
            border-radius: 8px;
        }
        
        .toggle-switch {
            position: relative;
            width: 44px; height: 24px;
            background: var(--border);
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .toggle-switch.active { background: var(--accent); }
        
        .toggle-switch::after {
            content: '';
            position: absolute;
            top: 2px; left: 2px;
            width: 20px; height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }
        
        .toggle-switch.active::after { transform: translateX(20px); }
        
        /* PROGRESS */
        .progress-container { margin-top: 15px; display: none; }
        .progress-container.active { display: block; }
        
        .progress-bar {
            height: 8px;
            background: var(--bg-card);
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--accent-hover));
            border-radius: 4px;
            transition: width 0.3s;
            width: 0%;
        }
        
        .progress-text { font-size: 12px; color: var(--text-secondary); margin-top: 5px; }
        
        /* STATS PANEL */
        .stats-panel { flex: 1; padding: 20px; overflow-y: auto; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: var(--bg-card);
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        
        .stat-value { font-size: 24px; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 5px; }
        
        /* FILES LIST */
        .files-list {
            background: var(--bg-card);
            border-radius: 10px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .files-list-header {
            padding: 10px 15px;
            border-bottom: 1px solid var(--border);
            font-weight: 500;
            font-size: 14px;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 15px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }
        
        .file-item:last-child { border-bottom: none; }
        .file-icon { margin-right: 10px; font-size: 16px; }
        .file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        
        .file-status {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .file-status.pending { background: var(--warning); color: var(--bg-primary); }
        .file-status.indexed { background: var(--accent); color: var(--bg-primary); }
        .file-status.error { background: var(--danger); color: white; }
        
        /* CHAT PANEL */
        .chat-panel { flex: 1; display: flex; flex-direction: column; height: 100%; }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            display: flex;
            gap: 12px;
            max-width: 85%;
        }
        
        .message.user { flex-direction: row-reverse; margin-left: auto; }
        
        .message-avatar {
            width: 36px; height: 36px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar { background: var(--chat-user); }
        .message.assistant .message-avatar { background: var(--chat-ai); }
        
        .message-content {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 12px 16px;
            line-height: 1.6;
            max-width: 100%;
        }
        
        .message.user .message-content {
            background: var(--chat-user);
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content { border-bottom-left-radius: 4px; }
        
        .message-content pre {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0;
            font-size: 13px;
        }
        
        .message-content code {
            background: rgba(0,0,0,0.3);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
        }
        
        .message-sources {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid var(--border);
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        /* CHAT INPUT */
        .chat-input-container {
            padding: 15px 20px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }
        
        .chat-input-wrapper { display: flex; gap: 10px; align-items: flex-end; }
        
        .chat-input {
            flex: 1;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-size: 14px;
            resize: none;
            min-height: 48px;
            max-height: 150px;
            line-height: 1.4;
        }
        
        .chat-input:focus { outline: none; border-color: var(--accent); }
        .chat-input::placeholder { color: var(--text-secondary); }
        
        .send-btn {
            width: 48px; height: 48px;
            border-radius: 12px;
            background: var(--accent);
            border: none;
            color: var(--bg-primary);
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex; align-items: center; justify-content: center;
        }
        
        .send-btn:hover { background: var(--accent-hover); transform: scale(1.05); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        
        /* TYPING */
        .typing-indicator { display: none; padding: 10px 20px; }
        
        .typing-indicator.active {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        
        .typing-dot {
            width: 8px; height: 8px;
            background: var(--accent);
            border-radius: 50%;
            animation: typingBounce 1.4s infinite ease-in-out both;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typingBounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        /* RESPONSIVE */
        @media (max-width: 900px) {
            .main-content { flex-direction: column; }
            .left-column {
                width: 100%; max-width: none; min-width: auto;
                max-height: 45vh;
                border-right: none;
                border-bottom: 1px solid var(--border);
            }
            .right-column { min-width: auto; }
        }
        
        @media (max-width: 600px) {
            .header { padding: 10px 15px; }
            .logo-text { font-size: 16px; }
            .model-status { padding: 6px 10px; font-size: 12px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .chat-input { font-size: 16px; }
        }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }
        
        .fade-in { animation: fadeIn 0.3s ease-in-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- HEADER -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">🤖</div>
                <span class="logo-text">KlimtechRAG</span>
            </div>
            <div class="header-actions">
                <div class="model-status">
                    <span class="status-dot" id="statusDot"></span>
                    <span id="modelStatus">Sprawdzam...</span>
                </div>
            </div>
        </header>
        
        <!-- MAIN CONTENT -->
        <main class="main-content">
            <!-- LEFT COLUMN -->
            <aside class="left-column">
                <!-- UPLOAD PANEL -->
                <section class="upload-panel">
                    <h2 class="panel-title">
                        <span>📤</span>
                        Wgraj pliki do indeksu
                    </h2>
                    
                    <div class="drop-zone" id="dropZone">
                        <div class="drop-zone-icon">📁</div>
                        <div class="drop-zone-text">Przeciągnij pliki tutaj lub kliknij</div>
                        <div class="drop-zone-hint">PDF, DOCX, TXT, MD (max 50MB)</div>
                        <input type="file" id="fileInput" multiple hidden 
                               accept=".pdf,.docx,.doc,.txt,.md,.json">
                    </div>
                    
                    <div class="progress-container" id="progressContainer">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                        <div class="progress-text" id="progressText">Przygotowywanie...</div>
                    </div>
                    
                    <!-- VLM Toggle -->
                    <div class="vlm-toggle">
                        <div class="toggle-switch" id="vlmToggle" onclick="toggleVLM()"></div>
                        <div>
                            <div style="font-weight: 500; font-size: 14px;">Tryb VLM</div>
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Dla PDF ze zdjęciami/rysunkami
                            </div>
                        </div>
                    </div>
                </section>
                
                <!-- STATS PANEL -->
                <section class="stats-panel">
                    <h2 class="panel-title">
                        <span>📊</span>
                        Statystyki
                    </h2>
                    
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" id="totalDocs">-</div>
                            <div class="stat-label">Dokumenty</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="totalChunks">-</div>
                            <div class="stat-label">Chunki</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="pendingFiles">-</div>
                            <div class="stat-label">Do indeksu</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="indexedToday">-</div>
                            <div class="stat-label">Dzisiaj</div>
                        </div>
                    </div>
                    
                    <div class="files-list">
                        <div class="files-list-header">📋 Ostatnie pliki</div>
                        <div id="filesListContent">
                            <div class="file-item" style="justify-content: center; color: var(--text-secondary);">
                                Ładowanie...
                            </div>
                        </div>
                    </div>
                </section>
            </aside>
            
            <!-- RIGHT COLUMN - CHAT -->
            <section class="right-column">
                <div class="chat-panel">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message assistant fade-in">
                            <div class="message-avatar">🤖</div>
                            <div class="message-content">
                                Witam! Jestem asystentem RAG KlimtechRAG.
                                <br><br>
                                Zadaj pytanie — przeszukam zaindeksowane dokumenty i odpowiem na podstawie ich treści.
                                <br><br>
                                <small style="opacity: 0.7">💡 Wgraj pliki po lewej stronie, aby rozszerzyć bazę wiedzy.</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="typing-indicator" id="typingIndicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <span style="margin-left: 10px; color: var(--text-secondary); font-size: 14px;">
                            Asystent pisze...
                        </span>
                    </div>
                    
                    <div class="chat-input-container">
                        <div class="chat-input-wrapper">
                            <textarea 
                                class="chat-input" 
                                id="chatInput" 
                                placeholder="Zadaj pytanie na podstawie zaindeksowanych dokumentów..."
                                rows="1"
                            ></textarea>
                            <button class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    </div>
    
    <script>
        // ============================================
        // KONFIGURACJA
        // ============================================
        const API_BASE = window.location.origin;
        let vlmMode = false;
        
        // ============================================
        // INICJALIZACJA
        // ============================================
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadFiles();
            checkLLMStatus();
            
            // Auto-refresh co 30s
            setInterval(() => {
                loadStats();
                checkLLMStatus();
            }, 30000);
        });
        
        // ============================================
        // SPRAWDZANIE STATUSU LLM
        // ============================================
        async function checkLLMStatus() {
            const dot = document.getElementById('statusDot');
            const status = document.getElementById('modelStatus');
            
            try {
                const response = await fetch(`${API_BASE}/v1/models`, {
                    method: 'GET',
                    signal: AbortSignal.timeout(3000)
                });
                
                if (response.ok) {
                    dot.classList.add('active');
                    status.textContent = 'LLM działa';
                } else {
                    dot.classList.remove('active');
                    status.textContent = 'LLM błąd';
                }
            } catch (error) {
                dot.classList.remove('active');
                status.textContent = 'LLM niedostępny';
            }
        }
        
        // ============================================
        // WGARJANIE PLIKÓW
        // ============================================
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        async function handleFiles(files) {
            if (files.length === 0) return;
            
            progressContainer.classList.add('active');
            progressFill.style.width = '0%';
            progressText.textContent = `Przygotowywanie ${files.length} plików...`;
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const progress = ((i) / files.length) * 100;
                
                progressText.textContent = `Wgrywanie: ${file.name}`;
                progressFill.style.width = `${progress}%`;
                
                const formData = new FormData();
                formData.append('file', file);
                if (vlmMode) formData.append('use_vlm', 'true');
                
                try {
                    const response = await fetch(`${API_BASE}/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        console.error(`Upload failed: ${file.name}`);
                    }
                } catch (error) {
                    console.error(`Error uploading ${file.name}:`, error);
                }
            }
            
            progressFill.style.width = '100%';
            progressText.textContent = '✅ Zakończono!';
            
            setTimeout(() => {
                progressContainer.classList.remove('active');
                loadStats();
                loadFiles();
            }, 2000);
        }
        
        // ============================================
        // VLM TOGGLE
        // ============================================
        function toggleVLM() {
            vlmMode = !vlmMode;
            document.getElementById('vlmToggle').classList.toggle('active', vlmMode);
        }
        
        // ============================================
        // STATYSTYKI
        // ============================================
        async function loadStats() {
            try {
                const response = await fetch(`${API_BASE}/files/stats`);
                if (response.ok) {
                    const data = await response.json();
                    document.getElementById('totalDocs').textContent = data.total_files || 0;
                    document.getElementById('totalChunks').textContent = data.total_chunks || 0;
                    document.getElementById('pendingFiles').textContent = data.pending || 0;
                    document.getElementById('indexedToday').textContent = data.indexed_today || 0;
                }
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }
        
        async function loadFiles() {
            try {
                const response = await fetch(`${API_BASE}/files/pending`);
                const files = await response.json();
                const container = document.getElementById('filesListContent');
                
                if (!files || files.length === 0) {
                    container.innerHTML = `
                        <div class="file-item" style="justify-content: center; color: var(--text-secondary);">
                            Brak plików
                        </div>
                    `;
                    return;
                }
                
                container.innerHTML = files.slice(0, 8).map(file => `
                    <div class="file-item fade-in">
                        <span class="file-icon">📄</span>
                        <span class="file-name">${file.name || file}</span>
                        <span class="file-status ${file.status || 'pending'}">
                            ${file.status === 'indexed' ? 'OK' : 'Pend'}
                        </span>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading files:', error);
            }
        }
        
        // ============================================
        // CZAT
        // ============================================
        const chatInput = document.getElementById('chatInput');
        const chatMessages = document.getElementById('chatMessages');
        const typingIndicator = document.getElementById('typingIndicator');
        const sendBtn = document.getElementById('sendBtn');
        
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
        
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        async function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            chatInput.value = '';
            chatInput.style.height = 'auto';
            
            typingIndicator.classList.add('active');
            sendBtn.disabled = true;
            
            try {
                const response = await fetch(`${API_BASE}/v1/chat/completions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: [{ role: 'user', content: message }],
                        stream: false
                    })
                });
                
                const data = await response.json();
                typingIndicator.classList.remove('active');
                sendBtn.disabled = false;
                
                const content = data.choices?.[0]?.message?.content || 'Brak odpowiedzi';
                addMessage(content, 'assistant');
                
            } catch (error) {
                typingIndicator.classList.remove('active');
                sendBtn.disabled = false;
                addMessage('❌ Błąd połączenia. Sprawdź czy LLM działa (start_klimtech.py)', 'assistant');
                console.error('Error:', error);
            }
        }
        
        function addMessage(content, role) {
            const div = document.createElement('div');
            div.className = `message ${role} fade-in`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            
            div.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">${formatContent(content)}</div>
            `;
            
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function formatContent(content) {
            return content
                .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)
