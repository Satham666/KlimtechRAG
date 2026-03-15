#!/bin/bash
# Naprawia brakujące kontenery przed startem backend_gpu

echo "=== KlimtechRAG — naprawa przed startem GPU ==="

# 1. Qdrant — wymagany przez backend
echo ""
echo "🐳 Uruchamiam Qdrant..."
podman start qdrant
if [ $? -eq 0 ]; then
    echo "   ✅ Qdrant uruchomiony"
else
    echo "   ⚠️  Qdrant nie mógł się uruchomić"
    echo "   Sprawdź: podman ps -a | grep qdrant"
fi

# 2. Poczekaj aż Qdrant nasłuchuje
echo "   ⏳ Czekam na Qdrant (port 6333)..."
for i in $(seq 1 15); do
    if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
        echo "   ✅ Qdrant odpowiada (${i}s)"
        break
    fi
    sleep 1
done

# 3. Sprawdź port
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo ""
    echo "✅ Qdrant OK — możesz uruchomić backend:"
    echo "   python3 start_backend_gpu.py"
else
    echo ""
    echo "❌ Qdrant nadal nie odpowiada na port 6333"
    echo "   Sprawdź: podman logs qdrant"
    echo "   Lub ręcznie: podman start qdrant"
fi
