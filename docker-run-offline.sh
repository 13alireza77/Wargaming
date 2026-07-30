#!/usr/bin/env bash
set -Eeuo pipefail

# =============================================================================
# 3/3 — Load offline Docker bundle and start Wargaming.
#
# Run on the OFFLINE server. Never downloads from the internet.
# Models must already be inside the bundle (packed by docker-build-offline.sh).
#
# Prerequisite: Docker + docker compose already installed on this server.
# =============================================================================

BUNDLE_FILE=""
INSTALL_DIR="/opt/wargaming-offline"
ALLOWED_HOSTS=""
ENABLE_GPU=0
SKIP_START=0
FORCE_RESTORE=0

usage() {
  cat <<'EOF'
Usage:
  sudo bash docker-run-offline.sh [options]

Options:
  --bundle-file <path>         Path to wargaming-docker-offline-*.tar[.gz]
                               (not needed when the bundle is already extracted
                               next to this script or in --install-dir)
  --install-dir <path>         Where to extract/run from.
                               Default: /opt/wargaming-offline
  --allowed-hosts <csv>        Django ALLOWED_HOSTS.
                               Default: auto-detect local IP + localhost,127.0.0.1
  --gpu                        Enable NVIDIA GPU for Ollama
  --skip-start                 Load images only (do not start containers)
  --restore-models             Re-extract model weights even if the volume
                               already contains them
  --help                       Show this help

Examples:
  sudo bash docker-run-offline.sh \
    --bundle-file ./wargaming-docker-offline-20260727-150000.tar.gz \
    --allowed-hosts "10.0.0.10,localhost,127.0.0.1"

  sudo bash docker-run-offline.sh \
    --bundle-file ./wargaming-docker-offline-20260727-150000.tar.gz \
    --gpu
EOF
}

log() { printf '[docker-run-offline] %s\n' "$*"; }
err() { printf '[docker-run-offline][ERROR] %s\n' "$*" >&2; exit 1; }

need_docker() {
  cat >&2 <<'EOF'
[docker-run-offline][ERROR] docker not found

Docker must be installed on this server BEFORE running the offline bundle.
The offline bundle does NOT install Docker itself.

If this server currently has internet (test server), install Docker once:

  # Ubuntu / Debian
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
  docker --version
  docker compose version

Then re-run:
  sudo bash docker-run-offline.sh --bundle-file <bundle.tar.gz>

For a REAL offline server: install Docker beforehand (or transfer Docker .deb
packages from an online machine), then run this script with no internet.
EOF
  exit 1
}

detect_server_ip() {
  # Prefer local interface IP (works offline). Avoid public IP APIs.
  hostname -I 2>/dev/null | awk '{print $1}'
}

wait_for_ollama() {
  local seconds="${1:-90}"
  local waited=0
  log "Waiting up to ${seconds}s for Ollama..."
  while (( waited < seconds )); do
    if docker exec wargaming-ollama ollama list >/dev/null 2>&1; then
      log "Ollama is ready."
      return 0
    fi
    sleep 2
    waited=$((waited + 2))
  done
  err "Ollama did not become ready. Check: docker logs wargaming-ollama"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-file)     BUNDLE_FILE="${2:-}"; shift 2 ;;
    --install-dir)     INSTALL_DIR="${2:-}"; shift 2 ;;
    --allowed-hosts)   ALLOWED_HOSTS="${2:-}"; shift 2 ;;
    --gpu)             ENABLE_GPU=1; shift ;;
    --skip-start)      SKIP_START=1; shift ;;
    --restore-models)  FORCE_RESTORE=1; shift ;;
    --pull-base-model|--base-model)
      err "Internet model download was removed. Rebuild with docker-build-offline.sh so models are packed inside the bundle."
      ;;
    --help|-h)         usage; exit 0 ;;
    *)                 err "Unknown argument: $1" ;;
  esac
done

[[ "${EUID:-$(id -u)}" -eq 0 ]] || err "Run as root: sudo bash docker-run-offline.sh ..."
command -v docker >/dev/null 2>&1 || need_docker
docker compose version >/dev/null 2>&1 || err "docker compose not found. Install Docker Compose v2 (included with modern Docker)."

mkdir -p "$INSTALL_DIR"

# Image tarballs may be plain or gzipped; docker load and tar detect both.
first_existing() {
  local candidate
  for candidate in "$@"; do
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$BUNDLE_FILE" ]] && [[ -f "$SCRIPT_DIR/docker-compose.yml" ]] &&
   first_existing "$SCRIPT_DIR/wargaming-app.tar" "$SCRIPT_DIR/wargaming-app.tar.gz" >/dev/null; then
  INSTALL_DIR="$SCRIPT_DIR"
  log "Detected extracted bundle in: $INSTALL_DIR"
fi

if [[ -n "$BUNDLE_FILE" ]]; then
  [[ -f "$BUNDLE_FILE" ]] || err "bundle file not found: $BUNDLE_FILE"
  log "Extracting bundle into $INSTALL_DIR ..."
  tar -xf "$BUNDLE_FILE" -C "$INSTALL_DIR"
fi

APP_TAR="$(first_existing "$INSTALL_DIR/wargaming-app.tar" "$INSTALL_DIR/wargaming-app.tar.gz")" ||
  err "missing $INSTALL_DIR/wargaming-app.tar[.gz] (pass --bundle-file)"
[[ -f "$INSTALL_DIR/docker-compose.yml" ]] || err "missing $INSTALL_DIR/docker-compose.yml"

if [[ -z "$ALLOWED_HOSTS" ]]; then
  DETECTED_IP="$(detect_server_ip)"
  if [[ -n "$DETECTED_IP" ]]; then
    ALLOWED_HOSTS="${DETECTED_IP},localhost,127.0.0.1"
  else
    ALLOWED_HOSTS="*"
  fi
  log "Using ALLOWED_HOSTS=$ALLOWED_HOSTS"
fi

cd "$INSTALL_DIR"

log "Loading app image (offline)..."
docker load -i "$APP_TAR"

if OLLAMA_TAR="$(first_existing "$INSTALL_DIR/ollama.tar" "$INSTALL_DIR/ollama.tar.gz")"; then
  log "Loading Ollama image (offline)..."
  docker load -i "$OLLAMA_TAR"
else
  log "ollama.tar not found — assuming Ollama image already exists locally."
fi

if [[ "$SKIP_START" -eq 1 ]]; then
  log "Images loaded. --skip-start set, not starting containers."
  exit 0
fi

OVERRIDE="$INSTALL_DIR/docker-compose.override.yml"
log "Writing runtime override: $OVERRIDE"
cat > "$OVERRIDE" <<EOF
services:
  app:
    environment:
      - DJANGO_ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - OLLAMA_BASE_URL=http://ollama:11434
      - DATABASE_PATH=/app/db/db.sqlite3
      - OLLAMA_WAIT_SECONDS=180
EOF

if [[ "$ENABLE_GPU" -eq 1 ]]; then
  cat >> "$OVERRIDE" <<'EOF'
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
EOF
fi

# Restore packed models into the named volume BEFORE first Ollama start,
# so the offline server never needs to download weights.
if MODELS_TAR="$(first_existing "$INSTALL_DIR/ollama-models.tar" "$INSTALL_DIR/ollama-models.tar.gz")"; then
  docker volume create ollama_data >/dev/null 2>&1 || true
  ALREADY_RESTORED=0
  if [[ "$FORCE_RESTORE" -eq 0 ]] && docker run --rm \
      --entrypoint bash \
      -v ollama_data:/root/.ollama \
      wargaming-app:latest \
      -c 'test -n "$(find /root/.ollama/models/manifests -type f 2>/dev/null | head -1)"' >/dev/null 2>&1; then
    ALREADY_RESTORED=1
  fi

  if [[ "$ALREADY_RESTORED" -eq 1 ]]; then
    log "Models already present in the ollama_data volume — skipping restore."
    log "Use --restore-models to overwrite them from the bundle."
  else
    log "Restoring Ollama models from offline archive (no internet)..."
    docker run --rm \
      --entrypoint bash \
      -v ollama_data:/root/.ollama \
      -v "$MODELS_TAR:/models.tar:ro" \
      wargaming-app:latest \
      -c 'mkdir -p /root/.ollama && tar -xf /models.tar -C /root/.ollama'
  fi
else
  log "WARN: ollama-models.tar missing in bundle."
  log "Rebuild with: bash docker-build-offline.sh   (do NOT use --skip-ollama-models)"
fi

log "Starting containers..."
docker compose -f "$INSTALL_DIR/docker-compose.yml" -f "$OVERRIDE" up -d
wait_for_ollama 120

log "Models available:"
docker exec wargaming-ollama ollama list || true

log "Waiting for app..."
sleep 8
docker compose -f "$INSTALL_DIR/docker-compose.yml" -f "$OVERRIDE" ps

FIRST_HOST="$(echo "$ALLOWED_HOSTS" | cut -d',' -f1)"
[[ "$FIRST_HOST" == "*" ]] && FIRST_HOST="localhost"

echo
log "Done (no internet used)."
log "Chat UI : http://${FIRST_HOST}:8000/chat/"
log "Admin   : http://${FIRST_HOST}:8000/admin/"
log "Logs    : docker compose -f $INSTALL_DIR/docker-compose.yml -f $OVERRIDE logs -f app"
