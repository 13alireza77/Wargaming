#!/usr/bin/env bash
set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Wargaming Docker entrypoint
# - runs migrations
# - seeds admin data
# - waits for Ollama (optional)
# - then exec's the CMD (gunicorn by default)
# ---------------------------------------------------------------------------

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Seeding admin data..."
python manage.py seed_admin_data --force

# Wait for Ollama if OLLAMA_BASE_URL is reachable
OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
OLLAMA_WAIT="${OLLAMA_WAIT_SECONDS:-30}"

echo "[entrypoint] Waiting up to ${OLLAMA_WAIT}s for Ollama at $OLLAMA_URL ..."
waited=0
while (( waited < OLLAMA_WAIT )); do
  if curl -fsS "${OLLAMA_URL}/api/version" >/dev/null 2>&1; then
    echo "[entrypoint] Ollama is ready."
    break
  fi
  sleep 2
  waited=$((waited + 2))
done

if (( waited >= OLLAMA_WAIT )); then
  echo "[entrypoint][WARN] Ollama not reachable at $OLLAMA_URL — starting anyway."
fi

# Build wargaming model if it doesn't exist yet.
# Uses manage.py retrain which talks to Ollama over HTTP (no local ollama CLI).
if curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
  WARGAMING_MODEL="${OLLAMA_WARGAMING_MODEL:-wargaming:unified}"
  if ! curl -fsS "${OLLAMA_URL}/api/tags" | python -c "
import sys, json
name = '${WARGAMING_MODEL}'
models = [m.get('name') or '' for m in json.load(sys.stdin).get('models', [])]
ok = name in models or (name + ':latest') in models
sys.exit(0 if ok else 1)
" 2>/dev/null; then
    echo "[entrypoint] Building $WARGAMING_MODEL model via Ollama HTTP API..."
    if ! python manage.py retrain_wargaming_llm --force; then
      echo "[entrypoint][ERROR] retrain failed — chat will 404 until the model exists."
      echo "[entrypoint][ERROR] Fix with: docker exec wargaming-app python manage.py retrain_wargaming_llm --force"
    fi
  else
    echo "[entrypoint] Model $WARGAMING_MODEL already exists."
  fi
fi

echo "[entrypoint] Starting: $*"
exec "$@"
