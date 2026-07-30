#!/usr/bin/env bash
set -Eeuo pipefail

# =============================================================================
# Online install — fetch deps with curl and bring Wargaming up.
#
# For servers WITH internet. Counterpart to the offline docker-*-offline.sh flow.
#
# One-liner (from any empty Linux server):
#   curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh | sudo bash
#
# With options:
#   curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh \
#     | sudo bash -s -- --gpu --allowed-hosts "10.0.0.10,localhost,127.0.0.1"
#
# Or after cloning:
#   git clone https://github.com/13alireza77/Wargaming.git
#   cd Wargaming && sudo bash docker-install-online.sh
# =============================================================================

REPO_URL="https://github.com/13alireza77/Wargaming.git"
REPO_TARBALL_URL="https://github.com/13alireza77/Wargaming/archive/refs/heads/main.tar.gz"
RAW_BASE="https://raw.githubusercontent.com/13alireza77/Wargaming/main"
INSTALL_DIR="/opt/wargaming"
BRANCH="main"
ALLOWED_HOSTS=""
ENABLE_GPU=0
SKIP_MODEL_PULL=0
OLLAMA_MODELS="gemma3:12b"
FORCE_RECLONE=0
SKIP_GIT_PULL=0
COMPOSE_PROJECT_NAME="wargaming"

usage() {
  cat <<'EOF'
Usage:
  sudo bash docker-install-online.sh [options]

  # First install (from any empty Linux server):
  curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh | sudo bash

  # Update / redeploy existing install (git pull + rebuild):
  curl -fsSL https://raw.githubusercontent.com/13alireza77/Wargaming/main/docker-install-online.sh \
    | sudo bash -s -- --gpu

Options:
  --install-dir <path>         Where to place/run the project.
                               Default: /opt/wargaming
  --repo-url <url>             Git clone URL.
                               Default: https://github.com/13alireza77/Wargaming.git
  --branch <name>              Git branch / tarball ref. Default: main
  --allowed-hosts <csv>        Django ALLOWED_HOSTS.
                               Default: auto-detect local IP + localhost,127.0.0.1
  --ollama-models <csv>        Models to pull into Ollama. Default: gemma3:12b
  --gpu                        Enable NVIDIA GPU for Ollama
  --skip-model-pull            Do not pull Ollama models (app may still retrain later)
  --force-reclone              Delete install-dir and re-download the project
  --skip-git-pull              Do not git pull when an existing checkout is found
  --help                       Show this help

What this script installs/downloads (via curl / Docker):
  1. curl + ca-certificates (apt) if missing
  2. Docker Engine + Compose (https://get.docker.com)
  3. Project source (git clone, or curl GitHub tarball if git is missing)
  4. On re-run: git pull latest code, then rebuild/restart
  5. Docker images: python base (build), ollama/ollama:latest
  6. Ollama model weights (ollama pull)
  7. Starts app + ollama; entrypoint creates wargaming:unified
EOF
}

log()  { printf '[docker-install-online] %s\n' "$*"; }
warn() { printf '[docker-install-online][WARN] %s\n' "$*" >&2; }
err()  { printf '[docker-install-online][ERROR] %s\n' "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

detect_server_ip() {
  hostname -I 2>/dev/null | awk '{print $1}'
}

retry_cmd() {
  local tries="$1"
  shift
  local n
  for n in $(seq 1 "$tries"); do
    if "$@"; then
      return 0
    fi
    log "Command failed (attempt $n/$tries): $*"
    if [[ "$n" -lt "$tries" ]]; then
      sleep $((n * 3))
      log "Retrying..."
    fi
  done
  return 1
}

ensure_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || err "Run as root: sudo bash docker-install-online.sh ..."
}

ensure_curl() {
  if have curl; then
    return 0
  fi
  log "curl not found — installing via apt..."
  if have apt-get; then
    apt-get update -y
    apt-get install -y --no-install-recommends curl ca-certificates
  else
    err "curl is required and apt-get is not available. Install curl manually."
  fi
  have curl || err "curl still missing after install"
}

ensure_docker() {
  if have docker && docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker already installed: $(docker --version)"
    return 0
  fi

  log "Installing Docker with curl (https://get.docker.com) ..."
  curl -fsSL https://get.docker.com | sh
  if have systemctl; then
    systemctl enable --now docker || true
  fi
  have docker || err "Docker install finished but 'docker' is still not on PATH"
  docker info >/dev/null 2>&1 || err "Docker daemon is not reachable"
  docker compose version >/dev/null 2>&1 || err "docker compose not found after Docker install"
  log "Docker ready: $(docker --version)"
}

# Resolve project root: existing checkout, or download into INSTALL_DIR.
resolve_project() {
  local src="${BASH_SOURCE[0]:-}" script_dir=""
  # When piped (curl | bash), BASH_SOURCE is often empty, "bash", or a /dev/fd path.
  if [[ -n "$src" && "$src" != "bash" && "$src" != "-" && "$src" != "/dev/stdin" && "$src" != /dev/fd/* ]]; then
    script_dir="$(cd "$(dirname "$src")" && pwd)"
    if [[ -f "$script_dir/docker-compose.yml" && -f "$script_dir/Dockerfile" ]]; then
      PROJECT_ROOT="$script_dir"
      log "Using existing checkout: $PROJECT_ROOT"
      return 0
    fi
  fi

  if [[ "$FORCE_RECLONE" -eq 1 && -d "$INSTALL_DIR" ]]; then
    log "Removing existing install dir (--force-reclone): $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
  fi

  if [[ -f "$INSTALL_DIR/docker-compose.yml" && -f "$INSTALL_DIR/Dockerfile" ]]; then
    PROJECT_ROOT="$INSTALL_DIR"
    log "Using existing install at: $PROJECT_ROOT"
    return 0
  fi

  mkdir -p "$(dirname "$INSTALL_DIR")"
  download_project "$INSTALL_DIR"
  PROJECT_ROOT="$INSTALL_DIR"
}

# Pull latest code when re-running against an existing git checkout.
pull_latest_code() {
  if [[ "$SKIP_GIT_PULL" -eq 1 ]]; then
    log "Skipping git pull (--skip-git-pull)."
    return 0
  fi
  if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
    warn "No .git in $PROJECT_ROOT — cannot pull. Use --force-reclone to re-download."
    return 0
  fi
  have git || err "git is required to update an existing install"
  log "Updating code: git pull origin $BRANCH in $PROJECT_ROOT"
  git -C "$PROJECT_ROOT" remote set-url origin "$REPO_URL" 2>/dev/null || true
  retry_cmd 3 git -C "$PROJECT_ROOT" fetch --depth 1 origin "$BRANCH" ||
    err "git fetch failed"
  git -C "$PROJECT_ROOT" checkout -B "$BRANCH" "origin/$BRANCH" 2>/dev/null ||
    git -C "$PROJECT_ROOT" checkout "$BRANCH"
  retry_cmd 3 git -C "$PROJECT_ROOT" pull --ff-only origin "$BRANCH" ||
    err "git pull failed — fix the checkout or use --force-reclone"
  log "Code at: $(git -C "$PROJECT_ROOT" rev-parse --short HEAD) ($(git -C "$PROJECT_ROOT" log -1 --pretty=%s))"
}

download_project() {
  local dest="$1"
  local tmp

  if have git; then
    log "Cloning $REPO_URL (branch $BRANCH) into $dest ..."
    if [[ -d "$dest/.git" ]]; then
      git -C "$dest" fetch --depth 1 origin "$BRANCH"
      git -C "$dest" checkout "$BRANCH"
      git -C "$dest" pull --ff-only origin "$BRANCH" || true
    else
      rm -rf "$dest"
      retry_cmd 3 git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$dest" ||
        err "git clone failed"
    fi
    return 0
  fi

  log "git not found — downloading source tarball with curl..."
  tmp="$(mktemp -d /tmp/wargaming-src-XXXXXX)"
  local tarball_url="https://github.com/13alireza77/Wargaming/archive/refs/heads/${BRANCH}.tar.gz"
  if [[ "$BRANCH" == "main" ]]; then
    tarball_url="$REPO_TARBALL_URL"
  fi
  retry_cmd 3 curl -fL --retry 3 --retry-delay 2 -o "$tmp/src.tar.gz" "$tarball_url" || {
    rm -rf "$tmp"
    err "failed to download $tarball_url"
  }
  mkdir -p "$tmp/extract"
  tar -xzf "$tmp/src.tar.gz" -C "$tmp/extract"
  local extracted
  extracted="$(find "$tmp/extract" -mindepth 1 -maxdepth 1 -type d | head -1)"
  [[ -n "$extracted" ]] || { rm -rf "$tmp"; err "tarball extracted empty"; }
  rm -rf "$dest"
  mv "$extracted" "$dest"
  rm -rf "$tmp"
  log "Source extracted to $dest"
}

write_override() {
  local override="$1"
  log "Writing runtime override: $override"
  cat > "$override" <<EOF
services:
  app:
    environment:
      - DJANGO_ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - OLLAMA_BASE_URL=http://ollama:11434
      - DATABASE_PATH=/app/db/db.sqlite3
      - OLLAMA_WAIT_SECONDS=300
EOF

  if [[ "$ENABLE_GPU" -eq 1 ]]; then
    cat >> "$override" <<'EOF'
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
}

wait_for_ollama() {
  local seconds="${1:-180}"
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

pull_models() {
  local models_csv="$1"
  local model
  IFS=',' read -r -a models <<< "$models_csv"
  for model in "${models[@]}"; do
    model="$(echo "$model" | xargs)"
    [[ -n "$model" ]] || continue
    log "Pulling Ollama model (online): $model"
    retry_cmd 5 docker exec wargaming-ollama ollama pull "$model" ||
      err "failed to pull model: $model"
  done
  log "Models available:"
  docker exec wargaming-ollama ollama list || true
}

wait_for_app() {
  local seconds="${1:-180}"
  local waited=0
  local url="http://127.0.0.1:8000/chat/"
  log "Waiting up to ${seconds}s for app at $url ..."
  while (( waited < seconds )); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      log "App is responding."
      return 0
    fi
    sleep 3
    waited=$((waited + 3))
  done
  warn "App did not answer yet — it may still be migrating / building the wargaming model."
  warn "Follow logs: docker compose -f $PROJECT_ROOT/docker-compose.yml -f $PROJECT_ROOT/docker-compose.override.yml logs -f app"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)     INSTALL_DIR="${2:-}"; shift 2 ;;
    --repo-url)        REPO_URL="${2:-}"; shift 2 ;;
    --branch)          BRANCH="${2:-}"; shift 2 ;;
    --allowed-hosts)   ALLOWED_HOSTS="${2:-}"; shift 2 ;;
    --ollama-models)   OLLAMA_MODELS="${2:-}"; shift 2 ;;
    --gpu)             ENABLE_GPU=1; shift ;;
    --skip-model-pull) SKIP_MODEL_PULL=1; shift ;;
    --force-reclone)   FORCE_RECLONE=1; shift ;;
    --skip-git-pull)   SKIP_GIT_PULL=1; shift ;;
    --help|-h)         usage; exit 0 ;;
    *)                 err "Unknown argument: $1" ;;
  esac
done

ensure_root
ensure_curl
ensure_docker

if [[ -z "$ALLOWED_HOSTS" ]]; then
  DETECTED_IP="$(detect_server_ip)"
  if [[ -n "$DETECTED_IP" ]]; then
    ALLOWED_HOSTS="${DETECTED_IP},localhost,127.0.0.1"
  else
    ALLOWED_HOSTS="*"
  fi
  log "Using ALLOWED_HOSTS=$ALLOWED_HOSTS"
fi

resolve_project
pull_latest_code
[[ -f "$PROJECT_ROOT/docker-compose.yml" ]] || err "missing docker-compose.yml in $PROJECT_ROOT"
[[ -f "$PROJECT_ROOT/Dockerfile" ]] || err "missing Dockerfile in $PROJECT_ROOT"

cd "$PROJECT_ROOT"
OVERRIDE="$PROJECT_ROOT/docker-compose.override.yml"
write_override "$OVERRIDE"

export COMPOSE_PROJECT_NAME
COMPOSE=(docker compose -f "$PROJECT_ROOT/docker-compose.yml" -f "$OVERRIDE")

log "Pulling Ollama image..."
retry_cmd 5 docker pull ollama/ollama:latest || err "failed to pull ollama/ollama:latest"

log "Building app image and starting containers (online)..."
retry_cmd 3 "${COMPOSE[@]}" up -d --build || err "docker compose up failed"

wait_for_ollama 180

if [[ "$SKIP_MODEL_PULL" -eq 0 ]]; then
  pull_models "$OLLAMA_MODELS"
else
  log "Skipping model pull (--skip-model-pull)."
fi

# Entrypoint builds wargaming:unified once Ollama + base model are ready.
# Restart app so retrain sees the freshly pulled base model if it started earlier.
log "Restarting app so it can build wargaming:unified if needed..."
"${COMPOSE[@]}" restart app >/dev/null
wait_for_app 300

"${COMPOSE[@]}" ps

FIRST_HOST="$(echo "$ALLOWED_HOSTS" | cut -d',' -f1)"
[[ "$FIRST_HOST" == "*" ]] && FIRST_HOST="localhost"

echo
log "Done (online install)."
log "Project  : $PROJECT_ROOT"
log "Chat UI  : http://${FIRST_HOST}:8000/chat/"
log "Admin    : http://${FIRST_HOST}:8000/admin/"
log "Logs     : ${COMPOSE[*]} logs -f app"
log ""
log "Update / redeploy later:"
log "  curl -fsSL ${RAW_BASE}/docker-install-online.sh | sudo bash -s -- --gpu"
if [[ "$ENABLE_GPU" -eq 1 ]]; then
  log "  (keep passing --gpu on GPU servers)"
fi
