#!/usr/bin/env bash
set -Eeuo pipefail

# =============================================================================
# Upload an offline Docker bundle to a remote server (SCP).
#
# Run this on your ONLINE / local machine after docker-build-offline.sh.
# =============================================================================

BUNDLE_FILE=""
BUNDLE_DIR=""
SERVER=""
REMOTE_DIR="/opt/wargaming-offline"
SSH_USER=""
SSH_PORT="22"
SSH_KEY=""
ALSO_UPLOAD_RUN_SCRIPT=1
USE_RSYNC=1

usage() {
  cat <<'EOF'
Usage:
  bash docker-upload-offline.sh (--bundle-dir <path> | --bundle-file <path>) --server <host> [options]

Required (one of):
  --bundle-dir <path>          Local offline-dist/wargaming-offline-bundle directory.
                               Recommended: rsync only sends the files that changed.
  --bundle-file <path>         Local wargaming-docker-offline-*.tar[.gz]

Required:
  --server <host>              Server hostname or IP

Optional:
  --user <ssh-user>            SSH username. Default: current local user
  --port <ssh-port>            SSH port. Default: 22
  --identity <key-path>        SSH private key path
  --remote-dir <path>          Destination directory on server.
                               Default: /opt/wargaming-offline
  --skip-run-script            Do not also upload docker-run-offline.sh
  --no-rsync                   Force scp even when rsync is available
  --help                       Show this help

Examples:
  # Incremental upload: after a code change only the app image is re-sent.
  bash docker-upload-offline.sh \
    --bundle-dir ./offline-dist/wargaming-offline-bundle \
    --server 85.208.254.201 \
    --user root

  bash docker-upload-offline.sh \
    --bundle-file ./offline-dist/wargaming-docker-offline-20260727-150000.tar \
    --server 10.0.0.10 \
    --user ubuntu \
    --identity ~/.ssh/id_rsa \
    --remote-dir /home/ubuntu/wargaming-offline
EOF
}

log() { printf '[docker-upload-offline] %s\n' "$*"; }
err() { printf '[docker-upload-offline][ERROR] %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-file)       BUNDLE_FILE="${2:-}"; shift 2 ;;
    --bundle-dir)        BUNDLE_DIR="${2:-}"; shift 2 ;;
    --server)            SERVER="${2:-}"; shift 2 ;;
    --user)              SSH_USER="${2:-}"; shift 2 ;;
    --port)              SSH_PORT="${2:-}"; shift 2 ;;
    --identity)          SSH_KEY="${2:-}"; shift 2 ;;
    --remote-dir)        REMOTE_DIR="${2:-}"; shift 2 ;;
    --skip-run-script)   ALSO_UPLOAD_RUN_SCRIPT=0; shift ;;
    --no-rsync)          USE_RSYNC=0; shift ;;
    --help|-h)           usage; exit 0 ;;
    *)                   err "Unknown argument: $1" ;;
  esac
done

[[ -n "$BUNDLE_FILE" || -n "$BUNDLE_DIR" ]] || err "--bundle-dir or --bundle-file is required"
[[ -z "$BUNDLE_FILE" || -z "$BUNDLE_DIR" ]] || err "use either --bundle-dir or --bundle-file, not both"
[[ -n "$SERVER" ]] || err "--server is required"
[[ -z "$BUNDLE_FILE" || -f "$BUNDLE_FILE" ]] || err "bundle file not found: $BUNDLE_FILE"
[[ -z "$BUNDLE_DIR" || -d "$BUNDLE_DIR" ]] || err "bundle directory not found: $BUNDLE_DIR"
command -v scp >/dev/null 2>&1 || err "scp not found"
command -v ssh >/dev/null 2>&1 || err "ssh not found"
command -v rsync >/dev/null 2>&1 || USE_RSYNC=0

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$PROJECT_ROOT/docker-run-offline.sh"
SSH_USER="${SSH_USER:-$(id -un)}"
TARGET="${SSH_USER}@${SERVER}"

SCP_OPTS=(-P "$SSH_PORT")
SSH_OPTS=(-p "$SSH_PORT")
SSH_CMD="ssh -p $SSH_PORT"
if [[ -n "$SSH_KEY" ]]; then
  [[ -f "$SSH_KEY" ]] || err "SSH key not found: $SSH_KEY"
  SCP_OPTS+=(-i "$SSH_KEY")
  SSH_OPTS+=(-i "$SSH_KEY")
  SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi

# rsync resumes interrupted transfers and skips files the server already has.
upload_path() {
  local src="$1" dest="$2"
  if [[ "$USE_RSYNC" -eq 1 ]]; then
    rsync -rlptvh --partial --progress -e "$SSH_CMD" "$src" "$dest"
  elif [[ -d "${src%/}" ]]; then
    scp "${SCP_OPTS[@]}" -r "${src%/}/." "$dest"
  else
    scp "${SCP_OPTS[@]}" "$src" "$dest"
  fi
}

log "Target      : $TARGET"
log "Remote dir  : $REMOTE_DIR"
log "Transport   : $([[ "$USE_RSYNC" -eq 1 ]] && echo 'rsync (incremental, resumable)' || echo scp)"

log "Creating remote directory..."
ssh "${SSH_OPTS[@]}" "$TARGET" "mkdir -p '$REMOTE_DIR'"

if [[ -n "$BUNDLE_DIR" ]]; then
  log "Bundle dir  : $BUNDLE_DIR"
  log "Uploading bundle contents (only changed files are sent)..."
  upload_path "${BUNDLE_DIR%/}/" "${TARGET}:${REMOTE_DIR}/"
else
  log "Bundle file : $BUNDLE_FILE"
  log "Uploading bundle (this may take a while)..."
  upload_path "$BUNDLE_FILE" "${TARGET}:${REMOTE_DIR}/"
fi

if [[ "$ALSO_UPLOAD_RUN_SCRIPT" -eq 1 ]]; then
  [[ -f "$RUN_SCRIPT" ]] || err "run script missing: $RUN_SCRIPT"
  log "Uploading docker-run-offline.sh..."
  scp "${SCP_OPTS[@]}" "$RUN_SCRIPT" "${TARGET}:${REMOTE_DIR}/"
fi
ssh "${SSH_OPTS[@]}" "$TARGET" "chmod +x '$REMOTE_DIR/docker-run-offline.sh'"

echo
log "Upload complete."
log ""
log "On the server, run:"
log "  ssh ${SSH_OPTS[*]} $TARGET"
log "  cd $REMOTE_DIR"
if [[ -n "$BUNDLE_DIR" ]]; then
  log "  sudo bash docker-run-offline.sh --allowed-hosts \"SERVER_IP,localhost,127.0.0.1\""
  log ""
  log "GPU example:"
  log "  sudo bash docker-run-offline.sh --gpu"
else
  BUNDLE_NAME="$(basename "$BUNDLE_FILE")"
  log "  sudo bash docker-run-offline.sh --bundle-file ./$BUNDLE_NAME --allowed-hosts \"SERVER_IP,localhost,127.0.0.1\""
  log ""
  log "GPU example:"
  log "  sudo bash docker-run-offline.sh --bundle-file ./$BUNDLE_NAME --gpu"
fi
