from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

CHAT_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KlimtechRAG Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; height: 100vh; display: flex; flex-direction: column; }
        h1 { text-align: center; padding: 15px; background: #16213e; border-radius: 10px; margin-bottom: 15px; }
        #chat-box { flex: 1; overflow-y: auto; background: #0f0f23; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
        .msg { margin: 10px 0; padding: 12px 15px; border-radius: 15px; max-width: 85%; word-wrap: break-word; }
        .user { background: #4a69bd; margin-left: auto; text-align: right; }
        .assistant { background: #2d3436; border: 1px solid #4a69bd; }
        .system { background: #6c5ce7; font-size: 0.9em; opacity: 0.8; }
        .success { background: #27ae60; }
        .error { background: #c0392b; }
        .input-area { display: flex; gap: 10px; flex-wrap: wrap; }
        #user-input { flex: 1; padding: 12px 15px; border: none; border-radius: 25px; background: #16213e; color: #eee; font-size: 16px; min-width: 200px; }
        #user-input:focus { outline: 2px solid #4a69bd; }
        button { padding: 12px 25px; border: none; border-radius: 25px; background: #4a69bd; color: white; font-size: 16px; cursor: pointer; }
        button:hover { background: #5a79cd; }
        button:disabled { background: #333; cursor: not-allowed; }
        .typing { font-style: italic; opacity: 0.7; }
        .rag-info { font-size: 0.8em; color: #888; margin-top: 5px; }
        .file-upload { display: flex; gap: 10px; align-items: center; margin-top: 10px; }
        #file-input { display: none; }
        .upload-btn { background: #27ae60; }
        .upload-btn:hover { background: #2ecc71; }
        #file-name { color: #888; font-size: 14px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .drop-zone { border: 2px dashed #4a69bd; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 10px; display: none; }
        .drop-zone.active { display: block; background: rgba(74, 105, 189, 0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 KlimtechRAG Chat</h1>
        <div id="chat-box"></div>
        <div class="drop-zone" id="drop-zone">
            📁 Upuść plik tutaj (PDF, TXT, MP3, MP4, JSON, obrazy...)
        </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Zapytaj o dokumenty w bazie RAG..." autofocus>
            <button id="send-btn" onclick="sendMessage()">Wyślij</button>
        </div>
        <div class="file-upload">
            <input type="file" id="file-input" onchange="handleFileSelect(event)">
            <button class="upload-btn" onclick="document.getElementById('file-input').click()">📎 Dodaj plik</button>
            <span id="file-name"></span>
            <button id="upload-btn" style="display:none;" onclick="uploadFile()">📤 Wyślij</button>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chat-box');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const fileInput = document.getElementById('file-input');
        const fileName = document.getElementById('file-name');
        const uploadBtn = document.getElementById('upload-btn');
        const dropZone = document.getElementById('drop-zone');

        let selectedFile = null;

        function addMessage(role, content, ragInfo = '') {
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.innerHTML = content.replace(/\\n/g, '<br>');
            if (ragInfo) {
                const info = document.createElement('div');
                info.className = 'rag-info';
                info.textContent = ragInfo;
                div.appendChild(info);
            }
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function handleFileSelect(event) {
            selectedFile = event.target.files[0];
            if (selectedFile) {
                fileName.textContent = selectedFile.name;
                uploadBtn.style.display = 'inline-block';
            } else {
                fileName.textContent = '';
                uploadBtn.style.display = 'none';
            }
        }

        async function uploadFile() {
            if (!selectedFile) return;

            const formData = new FormData();
            formData.append('file', selectedFile);

            addMessage('system', '📤 Wysyłanie: ' + selectedFile.name);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    addMessage('success', '✅ ' + data.message);
                } else {
                    addMessage('error', '❌ Błąd: ' + (data.detail || 'Nieznany błąd'));
                }
            } catch (err) {
                addMessage('error', '❌ Błąd połączenia: ' + err.message);
            }

            selectedFile = null;
            fileInput.value = '';
            fileName.textContent = '';
            uploadBtn.style.display = 'none';
        }

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
            document.body.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        document.body.addEventListener('dragenter', () => dropZone.classList.add('active'));
        document.body.addEventListener('dragleave', (e) => {
            if (!e.relatedTarget || !document.body.contains(e.relatedTarget)) {
                dropZone.classList.remove('active');
            }
        });

        document.body.addEventListener('drop', async (e) => {
            dropZone.classList.remove('active');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                selectedFile = files[0];
                fileName.textContent = selectedFile.name;
                await uploadFile();
            }
        });

        async function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;

            addMessage('user', query);
            userInput.value = '';
            sendBtn.disabled = true;

            const typingDiv = document.createElement('div');
            typingDiv.className = 'msg assistant typing';
            typingDiv.textContent = 'Pisze...';
            chatBox.appendChild(typingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/v1/chat/completions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model: 'klimtech-rag',
                        messages: [{ role: 'user', content: query }],
                        use_rag: true,
                        top_k: 5
                    })
                });

                chatBox.removeChild(typingDiv);

                if (!response.ok) {
                    addMessage('system', 'Błąd: ' + response.status);
                    return;
                }

                const data = await response.json();
                const answer = data.choices[0].message.content;
                addMessage('assistant', answer);
            } catch (err) {
                chatBox.removeChild(typingDiv);
                addMessage('system', 'Błąd połączenia: ' + err.message);
            }

            sendBtn.disabled = false;
            userInput.focus();
        }

        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        addMessage('system', 'Witaj! Jestem asystentem RAG z dostępem do Twoich dokumentów. Możesz też dodać pliki (PDF, TXT, MP3, MP4, obrazy) klikając 📎 lub przeciągając je tutaj.');
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
@router.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    return CHAT_HTML
