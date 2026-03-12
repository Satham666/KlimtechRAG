path = "/media/lobo/BACKUP/KlimtechRAG/start_klimtech.py"
with open(path, "r") as f:
    content = f.read()

stare = '''    print(f"   📦 Qdrant:        http://localhost:6333")
    print(f"   ☁️  Nextcloud:     http://localhost:8443")
    print(f"   🔗 n8n:           http://localhost:5678")'''

nowe = '''    def get_container_port(name):
        try:
            w = subprocess.run(["podman", "port", name], capture_output=True, text=True, timeout=5)
            for linia in w.stdout.strip().splitlines():
                if "->" in linia:
                    return linia.split(":")[-1].strip()
        except Exception:
            pass
        return "???"
    print(f"   📦 Qdrant:        http://localhost:{get_container_port('qdrant')}")
    print(f"   ☁️  Nextcloud:     http://localhost:{get_container_port('nextcloud')}")
    print(f"   🔗 n8n:           http://localhost:{get_container_port('n8n')}")'''

if stare in content:
    content = content.replace(stare, nowe)
    with open(path, "w") as f:
        f.write(content)
    print("OK")
else:
    print("NIE ZNALEZIONO")
