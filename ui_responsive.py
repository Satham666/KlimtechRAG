"""
routes/ui.py — Responsywny interfejs KlimtechRAG
================================================

Układ:
- LEWA POŁOWA: Wgraj pliki (góra) + Statystyki (dół)
- PRAWA POŁOWA: Czat (pełna wysokość)

Responsywny: na małych ekranach układ pionowy
"""
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List
import os
import json
import subprocess
import asyncio

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
        /* ============================================
           RESET I BAZOWE STYLE
           ============================================ */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow: hidden;
        }
        
        /* ============================================
           GŁÓWNY KONTENER
           ============================================ */
        .app-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100%;
        }
        
        /* ============================================
           NAGŁÓWEK
           ============================================ */
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
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent), var(--accent-hover));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        
        .logo-text {
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .model-status {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-card);
            border-radius: 20px;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--danger);
            animation: pulse 2s infinite;
        }
        
        .status-dot.active {
            background: var(--accent);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* ============================================
           GŁÓWNA ZAWARTOŚĆ - DWIE KOLUMNY
           ============================================ */
        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
            gap: 0;
        }
        
        /* LEWA KOLUMNA - Wgraj pliki + Statystyki */
        .left-column {
            width: 45%;
            min-width: 350px;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
        }
        
        /* PRAWA KOLUMNA - Czat */
        .right-column {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-primary);
            min-width: 400px;
        }
        
        /* ============================================
           PANEL WGARJANIA PLIKÓW
           ============================================ */
        .upload-panel {
            flex: 0 0 auto;
            max-height: 45%;
            padding: 20px;
            border-bottom: 1px solid var(--border);
            overflow-y: auto;
        }
        
        .panel-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .panel-title .icon {
            font-size: 20px;
        }
        
        /* Drop zone */
        .drop-zone {
            border: 2px dashed var(--border);
            border-radius: 12px;
            padding: 30px 20px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
            background: rgba(78, 204, 163, 0.05);
        }
        
        .drop-zone:hover,
        .drop-zone.dragover {
            border-color: var(--accent);
            background: rgba(78, 204, 163, 0.1);
        }
        
        .drop-zone-icon {
            font-size: 48px;
            margin-bottom: 10px;
            opacity: 0.7;
        }
        
        .drop-zone-text {
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 15px;
        }
        
        .drop-zone-hint {
            color: var(--text-secondary);
            font-size: 12px;
            opacity: 0.7;
        }
        
        /* Przyciski */
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
        
        .btn-primary {
            background: var(--accent);
            color: var(--bg-primary);
        }
        
        .btn-primary:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .btn-secondary:hover {
            background: var(--border);
        }
        
        .btn-danger {
            background: var(--danger);
            color: white;
        }
        
        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        /* Tryb VLM */
        .vlm-toggle {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
            padding: 10px;
            background: var(--bg-card);
            border-radius: 8px;
        }
        
        .toggle-switch {
            position: relative;
            width: 44px;
            height: 24px;
            background: var(--border);
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .toggle-switch.active {
            background: var(--accent);
        }
        
        .toggle-switch::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            transition: transform 0.3s;
        }
        
        .toggle-switch.active::after {
            transform: translateX(20px);
        }
        
        /* Progress bar */
        .progress-container {
            margin-top: 15px;
            display: none;
        }
        
        .progress-container.active {
            display: block;
        }
        
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
        
        .progress-text {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 5px;
        }
        
        /* ============================================
           PANEL STATYSTYK
           ============================================ */
        .stats-panel {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        
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
        
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--accent);
        }
        
        .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 5px;
        }
        
        /* Lista plików */
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
        
        .file-item:last-child {
            border-bottom: none;
        }
        
        .file-icon {
            margin-right: 10px;
            font-size: 16px;
        }
        
        .file-name {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .file-status {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        
        .file-status.pending {
            background: var(--warning);
            color: var(--bg-primary);
        }
        
        .file-status.indexed {
            background: var(--accent);
            color: var(--bg-primary);
        }
        
        .file-status.error {
            background: var(--danger);
            color: white;
        }
        
        /* ============================================
           PANEL CZATU
           ============================================ */
        .chat-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
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
            max-width: 90%;
        }
        
        .message.user {
            flex-direction: row-reverse;
            margin-left: auto;
        }
        
        .message-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: var(--chat-user);
        }
        
        .message.assistant .message-avatar {
            background: var(--chat-ai);
        }
        
        .message-content {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 12px 16px;
            line-height: 1.5;
        }
        
        .message.user .message-content {
            background: var(--chat-user);
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content {
            border-bottom-left-radius: 4px;
        }
        
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
        
        .message-sources-title {
            font-weight: 500;
            margin-bottom: 5px;
        }
        
        .source-item {
            display: flex;
            align-items: center;
            gap: 5px;
            margin: 3px 0;
        }
        
        /* Input czatu */
        .chat-input-container {
            padding: 15px 20px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }
        
        .chat-input-wrapper {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }
        
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
        
        .chat-input:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        .chat-input::placeholder {
            color: var(--text-secondary);
        }
        
        .send-btn {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: var(--accent);
            border: none;
            color: var(--bg-primary);
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .send-btn:hover {
            background: var(--accent-hover);
            transform: scale(1.05);
        }
        
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Typing indicator */
        .typing-indicator {
            display: none;
            padding: 10px 20px;
        }
        
        .typing-indicator.active {
            display: flex;
            gap: 5px;
            align-items: center;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
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
        
        /* ============================================
           PRZEŁĄCZANIE MODELI
           ============================================ */
        .model-switch-panel {
            padding: 15px;
            background: var(--bg-card);
            border-radius: 10px;
            margin-top: 15px;
        }
        
        .model-switch-title {
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .model-buttons {
            display: flex;
            gap: 10px;
        }
        
        .model-btn {
            flex: 1;
            padding: 10px;
            border: 2px solid var(--border);
            border-radius: 8px;
            background: transparent;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }
        
        .model-btn.active {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(78, 204, 163, 0.1);
        }
        
        .model-btn:hover:not(.active) {
            border-color: var(--text-secondary);
        }
        
        .model-btn-icon {
            font-size: 20px;
        }
        
        .model-btn-label {
            font-weight: 500;
        }
        
        .model-btn-hint {
            font-size: 11px;
            opacity: 0.7;
        }
        
        /* ============================================
           RESPONSYWNOŚĆ
           ============================================ */
        @media (max-width: 900px) {
            .main-content {
                flex-direction: column;
            }
            
            .left-column {
                width: 100%;
                max-width: none;
                min-width: auto;
                max-height: 50vh;
                border-right: none;
                border-bottom: 1px solid var(--border);
            }
            
            .right-column {
                min-width: auto;
            }
            
            .upload-panel {
                max-height: none;
            }
            
            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }
        
        @media (max-width: 600px) {
            .header {
                padding: 10px 15px;
            }
            
            .logo-text {
                font-size: 16px;
            }
            
            .model-status {
                padding: 6px 10px;
                font-size: 12px;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .panel-title {
                font-size: 14px;
            }
            
            .drop-zone {
                padding: 20px;
            }
            
            .chat-input {
                font-size: 16px; /* Zapobiega zoom na iOS */
            }
        }
        
        /* ============================================
           SCROLLBAR
           ============================================ */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
        
        /* ============================================
           ANIMACJE
           ============================================ */
        .fade-in {
            animation: fadeIn 0.3s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .slide-in {
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- NAGŁÓWEK -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">🤖</div>
                <span class="logo-text">KlimtechRAG</span>
            </div>
            <div class="header-actions">
                <div class="model-status">
                    <span class="status-dot" id="statusDot"></span>
                    <span id="modelType">Ładowanie...</span>
                </div>
            </div>
        </header>
        
        <!-- GŁÓWNA ZAWARTOŚĆ -->
        <main class="main-content">
            <!-- LEWA KOLUMNA -->
            <aside class="left-column">
                <!-- PANEL WGARJANIA -->
                <section class="upload-panel">
                    <h2 class="panel-title">
                        <span class="icon">📤</span>
                        Wgraj pliki do indeksu
                    </h2>
                    
                    <div class="drop-zone" id="dropZone">
                        <div class="drop-zone-icon">📁</div>
                        <div class="drop-zone-text">
                            Przeciągnij pliki tutaj lub kliknij
                        </div>
                        <div class="drop-zone-hint">
                            PDF, DOCX, TXT, MD (max 50MB)
                        </div>
                        <input type="file" id="fileInput" multiple hidden 
                               accept=".pdf,.docx,.doc,.txt,.md,.json">
                    </div>
                    
                    <div class="progress-container" id="progressContainer">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                        <div class="progress-text" id="progressText">Przygotowywanie...</div>
                    </div>
                    
                    <!-- Tryb VLM -->
                    <div class="vlm-toggle">
                        <div class="toggle-switch" id="vlmToggle" onclick="toggleVLM()"></div>
                        <div>
                            <div style="font-weight: 500; font-size: 14px;">Tryb VLM</div>
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Dla PDF ze zdjęciami/rysunkami
                            </div>
                        </div>
                    </div>
                    
                    <!-- Przełączanie modeli -->
                    <div class="model-switch-panel">
                        <div class="model-switch-title">
                            <span>🔄</span>
                            Przełącz model
                        </div>
                        <div class="model-buttons">
                            <button class="model-btn active" id="btnLLM" onclick="switchModel('llm')">
                                <span class="model-btn-icon">💬</span>
                                <span class="model-btn-label">LLM</span>
                                <span class="model-btn-hint">Czat</span>
                            </button>
                            <button class="model-btn" id="btnVLM" onclick="switchModel('vlm')">
                                <span class="model-btn-icon">📷</span>
                                <span class="model-btn-label">VLM</span>
                                <span class="model-btn-hint">Vision</span>
                            </button>
                        </div>
                    </div>
                </section>
                
                <!-- PANEL STATYSTYK -->
                <section class="stats-panel">
                    <h2 class="panel-title">
                        <span class="icon">📊</span>
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
                            <!-- Dynamicznie wypełniane -->
                        </div>
                    </div>
                </section>
            </aside>
            
            <!-- PRAWA KOLUMNA - CZAT -->
            <section class="right-column">
                <div class="chat-panel">
                    <div class="chat-messages" id="chatMessages">
                        <div class="message assistant">
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
                            <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                                ➤
                            </button>
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
        let currentModel = 'llm';
        let vlmMode = false;
        
        // ============================================
        // INICJALIZACJA
        // ============================================
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadFiles();
            checkModelStatus();
            
            // Refresh co 30s
            setInterval(() => {
                loadStats();
                checkModelStatus();
            }, 30000);
        });
        
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
                const progress = ((i + 1) / files.length) * 100;
                
                progressText.textContent = `Wgrywanie: ${file.name}`;
                progressFill.style.width = `${progress}%`;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('use_vlm', vlmMode);
                
                try {
                    const response = await fetch(`${API_BASE}/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    console.log(`Uploaded: ${file.name}`, result);
                    
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
        // TRYB VLM
        // ============================================
        function toggleVLM() {
            vlmMode = !vlmMode;
            const toggle = document.getElementById('vlmToggle');
            toggle.classList.toggle('active', vlmMode);
        }
        
        // ============================================
        // PRZEŁĄCZANIE MODELI
        // ============================================
        async function switchModel(type) {
            const btnLLM = document.getElementById('btnLLM');
            const btnVLM = document.getElementById('btnVLM');
            
            btnLLM.classList.remove('active');
            btnVLM.classList.remove('active');
            
            if (type === 'llm') btnLLM.classList.add('active');
            else btnVLM.classList.add('active');
            
            try {
                const response = await fetch(`${API_BASE}/model/switch/${type}`, {
                    method: 'POST'
                });
                const result = await response.json();
                
                if (result.success) {
                    currentModel = type;
                    updateModelStatus(type, true);
                } else {
                    alert('Błąd: ' + result.message);
                }
            } catch (error) {
                console.error('Error switching model:', error);
                alert('Błąd przełączania modelu');
            }
        }
        
        async function checkModelStatus() {
            try {
                const response = await fetch(`${API_BASE}/model/status`);
                const data = await response.json();
                
                currentModel = data.model_type;
                updateModelStatus(data.model_type, data.running);
                
                const btnLLM = document.getElementById('btnLLM');
                const btnVLM = document.getElementById('btnVLM');
                
                btnLLM.classList.toggle('active', data.model_type === 'llm');
                btnVLM.classList.toggle('active', data.model_type === 'vlm');
                
            } catch (error) {
                console.error('Error checking model status:', error);
                updateModelStatus('unknown', false);
            }
        }
        
        function updateModelStatus(type, running) {
            const dot = document.getElementById('statusDot');
            const text = document.getElementById('modelType');
            
            dot.classList.toggle('active', running);
            
            if (!running) {
                text.textContent = 'Zatrzymany';
            } else if (type === 'llm') {
                text.textContent = 'LLM (Czat)';
            } else if (type === 'vlm') {
                text.textContent = 'VLM (Vision)';
            } else {
                text.textContent = type.toUpperCase();
            }
        }
        
        // ============================================
        // STATYSTYKI
        // ============================================
        async function loadStats() {
            try {
                const response = await fetch(`${API_BASE}/files/stats`);
                const data = await response.json();
                
                document.getElementById('totalDocs').textContent = data.total_files || 0;
                document.getElementById('totalChunks').textContent = data.total_chunks || 0;
                document.getElementById('pendingFiles').textContent = data.pending || 0;
                document.getElementById('indexedToday').textContent = data.indexed_today || 0;
                
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
                
                container.innerHTML = files.slice(0, 10).map(file => `
                    <div class="file-item fade-in">
                        <span class="file-icon">📄</span>
                        <span class="file-name">${file.name || file}</span>
                        <span class="file-status ${file.status || 'pending'}">
                            ${file.status === 'indexed' ? 'Zaindeksowany' : 'Oczekuje'}
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
        
        // Auto-resize textarea
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
        
        // Enter to send
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        async function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;
            
            // Dodaj wiadomość użytkownika
            addMessage(message, 'user');
            chatInput.value = '';
            chatInput.style.height = 'auto';
            
            // Pokaż typing indicator
            typingIndicator.classList.add('active');
            sendBtn.disabled = true;
            
            try {
                const response = await fetch(`${API_BASE}/v1/chat/completions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        messages: [{ role: 'user', content: message }],
                        stream: false
                    })
                });
                
                const data = await response.json();
                
                typingIndicator.classList.remove('active');
                sendBtn.disabled = false;
                
                const assistantMessage = data.choices?.[0]?.message?.content || 'Brak odpowiedzi';
                addMessage(assistantMessage, 'assistant', data.sources);
                
            } catch (error) {
                typingIndicator.classList.remove('active');
                sendBtn.disabled = false;
                addMessage('❌ Błąd połączenia z serwerem. Sprawdź czy LLM działa.', 'assistant');
                console.error('Error:', error);
            }
        }
        
        function addMessage(content, role, sources = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role} fade-in`;
            
            const avatar = role === 'user' ? '👤' : '🤖';
            
            let sourcesHtml = '';
            if (sources && sources.length > 0) {
                sourcesHtml = `
                    <div class="message-sources">
                        <div class="message-sources-title">📚 Źródła:</div>
                        ${sources.map(s => `
                            <div class="source-item">
                                <span>📄</span>
                                <span>${s}</span>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    ${formatMessage(content)}
                    ${sourcesHtml}
                </div>
            `;
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function formatMessage(content) {
            // Proste formatowanie
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
