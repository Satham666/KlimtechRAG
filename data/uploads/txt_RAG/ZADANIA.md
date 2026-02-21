# KlimtechRAG folder analysis


## Temat nr 1

Przeczytaj pliki w folderze ~/KlimtechRAG oraz podfolderch. To są główne pliki z  którymi powionieneś się zapoznać:
~/KlimtechRAG/model_parametr.py
~/KlimtechRAG/stop_klimtech.py
~/KlimtechRAG/start_klimtech.py
~/KlimtechRAG/ingest_pdf.py
~/KlimtechRAG/watch_nextcloud.py
~/KlimtechRAG/backend_app/config.py
~/KlimtechRAG/backend_app/fs_tools.py
~/KlimtechRAG/backend_app/main.py
~/KlimtechRAG/backend_app/monitoring.py


HIP_VISIBLE_DEVICES=0 ./llama.cpp/build/bin/llama-server -m /home/lobo/.cache/llama.cpp/LFM2-2.6B-F16.gguf \
--host 0.0.0.0 \
--port 8082 \
-ngl -1 \
-c 131072 \
--flash-attn \
--n-predict 2048 \
-b 1024 \
-t 32 \
--repeat_penalty 1.2 \
--temp 0.2


HIP_VISIBLE_DEVICES=0 ./llama.cpp/build/bin/llama-server -m /home/lobo/.cache/llama.cpp/LFM2-2.6B-F16.gguf -ngl -1 -c 68672 --n-predict 4096 -b 512 --repeat_penalty 1.1 --temp 0.3 --host 0.0.0.0 --port 8082 --flash-attn on