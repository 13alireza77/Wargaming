#!/usr/bin/env bash
# =============================================================================
# Wargaming — fast code update via ZIP (no git)
# Run on server:  bash update_server.sh
# =============================================================================
set -Eeuo pipefail

PROJECT_DIR="/opt/Wargaming"
PROJECT_ZIP_URL="https://github.com/13alireza77/Wargaming/archive/refs/heads/main.zip"

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
green() { color "1;32" "$1"; }
yellow() { color "1;33" "$1"; }
cyan() { color "1;36" "$1"; }
bold() { color "1" "$1"; }

step() {
  echo
  echo "$(cyan "══") $(bold "$1")"
}

run() {
  echo "$(yellow "\$") $(bold "$*")"
  "$@"
}

[[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "Run as root"; exit 1; }
[[ -d "$PROJECT_DIR" ]] || { echo "Missing $PROJECT_DIR — run deploy_server.sh first"; exit 1; }

echo "$(bold "Wargaming ZIP update")"
echo "Started: $(date)"

step "Backup .venv + db.sqlite3"
BACKUP_DIR="/tmp/wargaming-update-backup-$$"
mkdir -p "$BACKUP_DIR"
[[ -d "$PROJECT_DIR/.venv" ]] && cp -a "$PROJECT_DIR/.venv" "$BACKUP_DIR/.venv"
[[ -f "$PROJECT_DIR/db.sqlite3" ]] && cp -a "$PROJECT_DIR/db.sqlite3" "$BACKUP_DIR/db.sqlite3"
[[ -f "$PROJECT_DIR/db.sqlite3-journal" ]] && cp -a "$PROJECT_DIR/db.sqlite3-journal" "$BACKUP_DIR/db.sqlite3-journal"

step "Download ZIP"
rm -f /tmp/Wargaming.zip
run curl -fL "$PROJECT_ZIP_URL" -o /tmp/Wargaming.zip

step "Replace project files"
find "$PROJECT_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
run bsdtar --strip-components 1 -xf /tmp/Wargaming.zip -C "$PROJECT_DIR"

step "Restore runtime files"
[[ -d "$BACKUP_DIR/.venv" ]] && cp -a "$BACKUP_DIR/.venv" "$PROJECT_DIR/.venv"
[[ -f "$BACKUP_DIR/db.sqlite3" ]] && cp -a "$BACKUP_DIR/db.sqlite3" "$PROJECT_DIR/db.sqlite3"
[[ -f "$BACKUP_DIR/db.sqlite3-journal" ]] && cp -a "$BACKUP_DIR/db.sqlite3-journal" "$PROJECT_DIR/db.sqlite3-journal"
rm -rf "$BACKUP_DIR"

step "Install deps + migrate + static"
# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"
cd "$PROJECT_DIR"
run pip install -r requirements.txt
run python manage.py migrate
run python manage.py collectstatic --noinput

if [[ "${1:-}" == "--retrain" ]]; then
  step "Retrain model"
  run python manage.py retrain_wargaming_llm --force
fi

step "Restart service"
run systemctl restart wargaming
run systemctl --no-pager --full status wargaming || true
run curl -I http://127.0.0.1:8000/chat/ || true

echo
echo "$(green "UPDATE DONE") — $(date)"
echo "Chat: http://$(curl -fsS --max-time 3 https://ifconfig.me 2>/dev/null || echo SERVER_IP):8000/chat/"
