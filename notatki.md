


# 1. Poprawienie ścierzek katlogów w aplikacju klimtechRAG
	- sprawdź we szystkich plikach główną ścierzkę która została zmieniona z powodu przeniesienia całego projektu z ~/KlimtechRAG/ do /media/lobo/BACKUP/KlimtechRAG/ i popraw na nową
	- llama.cpp będzie uruchamiał modele które zawsze będą pobierane do jednego katalogu /media/lobo/BACKUP/KlimtechRAG/modele_LLM
	- katalog /media/lobo/BACKUP/KlimtechRAG/modele_LLM jest podzielony na podkatalogi które zawieraja różne modele językowe stworzone do konkretych zadań:
	   - /media/lobo/BACKUP/KlimtechRAG/modele_LLM/AudioLLM - 


🗑️ Reset bazy Qdrant
Opcja 1 — Tylko usunięcie kolekcji (zalecane)
Usuwa wektory, zachowuje kontener i konfigurację:
bash# Usuń kolekcję
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

# Sprawdź czy zniknęła
curl -s http://localhost:6333/collections | python3 -m json.tool
Kolekcja zostanie odtworzona automatycznie przy następnym starcie backendu.

Opcja 2 — Usuń kolekcję + file_registry (pełny reset)
Żeby backend nie pamiętał, które pliki już zaindeksował:
bash# 1. Usuń kolekcję Qdrant
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

# 2. Usuń rejestr plików
rm /media/lobo/BACKUP/KlimtechRAG/data/file_registry.db

# 3. Zrestartuj backend
pkill -f "uvicorn backend_app"
Po restarcie start_klimtech.py kolekcja i baza SQLite zostaną odtworzone od zera.

Opcja 3 — Snapshot przed resetem (bezpieczniej)
bash# Zrób backup najpierw
curl -X POST "http://localhost:6333/collections/klimtech_docs/snapshots"

# Sprawdź gdzie zapisany
curl "http://localhost:6333/collections/klimtech_docs/snapshots"

# Potem dopiero usuń
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

Po resecie — ponowne indeksowanie
bash# Sprawdź czy kolekcja pusta
curl -s http://localhost:6333/collections/klimtech_docs | python3 -m json.tool

# Zaindeksuj wszystkie pliki od nowa (CPU)
curl -X POST "http://localhost:8000/ingest_all?limit=50"

# Lub masowo na GPU (szybciej ~70x)
pkill llama-server
./start_backend_gpu.sh
curl -X POST "http://localhost:8000/ingest_all?limit=200"

\\ VIDEO
./llama-server -hf unsloth/Qwen2.5-VL-7B-Instruct-GGUF:UD-Q4_K_XL
./llama-server -hf unsloth/Qwen2.5-VL-7B-Instruct-GGUF:UD-Q6_K_XL

./llama-server -hf LiquidAI/LFM2.5-VL-1.6B-GGUF:BF16

\\ AUDIO
./llama-server -hf LiquidAI/LFM2.5-Audio-1.5B-GGUF:F16



\\ emmbending tekst
./lama-server -hf mykor/bge-m3.gguf:F32
./llama-server -hf ChristianAzinn/bge-large-en-v1.5-gguf:Q8_0


\\\ podstawowe

./llama-server -hf LiquidAI/LFM2.5-1.2B-Base-GGUF:F16
./llama-server -hf DevQuasar/LiquidAI.LFM2-2.6B-GGUF:F16

./llama-server -hf speakleash/Bielik-11B-v3.0-Instruct-GGUF:Q8_0
./llama-server -hf speakleash/Bielik-4.5B-v3.0-Instruct-GGUF:Q8_0\


(klimtech_venv) lobo@hall9000 ~/.c/llama.cpp> tree  /media/lobo/BACKUP/KlimtechRAG/modele_LLM
/media/lobo/BACKUP/KlimtechRAG/modele_LLM
├── model_audio
│   ├── LiquidAI_LFM2.5-Audio-1.5B-GGUF_LFM2.5-Audio-1.5B-F16.gguf
│   ├── LiquidAI_LFM2.5-Audio-1.5B-GGUF_LFM2.5-Audio-1.5B-F16.gguf.etag
│   ├── LiquidAI_LFM2.5-Audio-1.5B-GGUF_mmproj-LFM2.5-Audio-1.5B-F16.gguf
│   ├── LiquidAI_LFM2.5-Audio-1.5B-GGUF_mmproj-LFM2.5-Audio-1.5B-F16.gguf.etag
│   └── manifest=LiquidAI=LFM2.5-Audio-1.5B-GGUF=F16.json
├── model_embedding
│   ├── ChristianAzinn_bge-large-en-v1.5-gguf_bge-large-en-v1.5.Q8_0.gguf
│   ├── ChristianAzinn_bge-large-en-v1.5-gguf_bge-large-en-v1.5.Q8_0.gguf.etag
│   ├── manifest=ChristianAzinn=bge-large-en-v1.5-gguf=Q8_0.json
│   ├── manifest=mykor=bge-m3.gguf=F32.json
│   ├── mykor_bge-m3.gguf_Bge-M3-567M-F32.gguf
│   └── mykor_bge-m3.gguf_Bge-M3-567M-F32.gguf.etag
├── model_financial_analysis
├── model_medical
├── model_thinking
│   ├── DevQuasar_LiquidAI.LFM2-2.6B-GGUF_LiquidAI.LFM2-2.6B.f16.gguf
│   ├── DevQuasar_LiquidAI.LFM2-2.6B-GGUF_LiquidAI.LFM2-2.6B.f16.gguf.etag
│   ├── LiquidAI_LFM2.5-1.2B-Base-GGUF_LFM2.5-1.2B-Base-BF16.gguf
│   ├── LiquidAI_LFM2.5-1.2B-Base-GGUF_LFM2.5-1.2B-Base-BF16.gguf.etag
│   ├── manifest=DevQuasar=LiquidAI.LFM2-2.6B-GGUF=F16.json
│   ├── manifest=LiquidAI=LFM2.5-1.2B-Base-GGUF=F16.json
│   ├── manifest=speakleash=Bielik-11B-v3.0-Instruct-GGUF=Q8_0.json
│   ├── manifest=speakleash=Bielik-4.5B-v3.0-Instruct-GGUF=Q8_0.json
│   ├── speakleash_Bielik-11B-v3.0-Instruct-GGUF_Bielik-11B-v3.0-Instruct.Q8_0.gguf
│   ├── speakleash_Bielik-11B-v3.0-Instruct-GGUF_Bielik-11B-v3.0-Instruct.Q8_0.gguf.etag
│   ├── speakleash_Bielik-4.5B-v3.0-Instruct-GGUF_Bielik-4.5B-v3.0-Instruct.Q8_0.gguf
│   └── speakleash_Bielik-4.5B-v3.0-Instruct-GGUF_Bielik-4.5B-v3.0-Instruct.Q8_0.gguf.etag
└── model_video
    ├── LiquidAI_LFM2.5-VL-1.6B-GGUF_LFM2.5-VL-1.6B-BF16.gguf
    ├── LiquidAI_LFM2.5-VL-1.6B-GGUF_LFM2.5-VL-1.6B-BF16.gguf.etag
    ├── LiquidAI_LFM2.5-VL-1.6B-GGUF_mmproj-LFM2.5-VL-1.6b-BF16.gguf
    ├── LiquidAI_LFM2.5-VL-1.6B-GGUF_mmproj-LFM2.5-VL-1.6b-BF16.gguf.etag
    ├── manifest=LiquidAI=LFM2.5-VL-1.6B-GGUF=BF16.json
    ├── manifest=unsloth=Qwen2.5-VL-7B-Instruct-GGUF=UD-Q4_K_XL.json
    ├── manifest=unsloth=Qwen2.5-VL-7B-Instruct-GGUF=UD-Q6_K_XL.json
    ├── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_mmproj-BF16.gguf
    ├── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_mmproj-BF16.gguf.etag
    ├── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf
    ├── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf.etag
    ├── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q6_K_XL.gguf
    └── unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q6_K_XL.gguf.etag

7 directories, 36 files