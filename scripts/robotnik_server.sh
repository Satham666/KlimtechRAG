#!/usr/bin/env bash
# Robotnik llama-server — start/stop/status/restart
# Użycie: ./scripts/robotnik_server.sh {start|stop|status|restart}
set -euo pipefail

cd "$(dirname "$0")/.."
exec python3 -m robotnik.server "${1:-status}"
