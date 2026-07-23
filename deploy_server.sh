#!/usr/bin/env bash
# =============================================================================
# Wargaming — one-shot Ubuntu server deploy
# Run as root:  bash deploy_server.sh
# Or:           curl -fsSL ... | bash   (after you push this file to GitHub)
# =============================================================================
set -Eeuo pipefail

# ------------------------------- config --------------------------------------
PROJECT_DIR="/opt/Wargaming"
PROJECT_ZIP_URL="https://github.com/13alireza77/Wargaming/archive/refs/heads/main.zip"
OLLAMA_TARBALL_URL="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst"
OLLAMA_SHA_URL="https://github.com/ollama/ollama/releases/latest/download/sha256sum.txt"
PYTHON_BIN="python3.13"
APP_BIND="0.0.0.0:8000"
GUNICORN_WORKERS="2"
GUNICORN_TIMEOUT="300"
BASE_MODEL="gemma3:12b"

# ------------------------------- helpers -------------------------------------
STEP=0
TOTAL_STEPS=14

color() { printf '\033[%sm%s\033[0m' "$1" "$2"; }
green() { color "1;32" "$1"; }
yellow() { color "1;33" "$1"; }
cyan() { color "1;36" "$1"; }
red() { color "1;31" "$1"; }
bold() { color "1" "$1"; }

banner() {
  STEP=$((STEP + 1))
  echo
  echo "$(cyan "════════════════════════════════════════════════════════════")"
  echo "$(bold "[$STEP/$TOTAL_STEPS]") $(green "$1")"
  echo "$(cyan "════════════════════════════════════════════════════════════")"
}

info() { echo "$(cyan "→") $*"; }
ok() { echo "$(green "✓") $*"; }
warn() { echo "$(yellow "!") $*"; }
fail() { echo "$(red "✗") $*"; exit 1; }

run() {
  echo
  echo "$(yellow "\$") $(bold "$*")"
  echo "$(cyan "────────────────────────────────────────────────────────────")"
  # shellcheck disable=SC2068
  "$@"
  local rc=$?
  echo "$(cyan "────────────────────────────────────────────────────────────")"
  if [[ $rc -eq 0 ]]; then
    ok "exit $rc"
  else
    fail "command failed with exit $rc: $*"
  fi
}

ask_yes_no() {
  local prompt="$1"
  local default="${2:-y}"
  local reply
  if [[ "$default" == "y" ]]; then
    read -r -p "$(yellow "?") $prompt [Y/n]: " reply || true
    reply="${reply:-y}"
  else
    read -r -p "$(yellow "?") $prompt [y/N]: " reply || true
    reply="${reply:-n}"
  fi
  [[ "$reply" =~ ^[Yy]$ ]]
}

need_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    fail "Run this script as root:  sudo bash deploy_server.sh"
  fi
}

detect_public_ip() {
  local ip=""
  ip="$(curl -fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"
  if [[ -z "$ip" ]]; then
    ip="$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
  fi
  if [[ -z "$ip" ]]; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  echo "$ip"
}

# Fresh cloud images often run unattended-upgrades at boot and hold apt locks.
# apt-get update can succeed while dpkg install lock is still held.
stop_background_apt() {
  info "Stopping background apt / unattended-upgrades (ephemeral server)..."
  systemctl stop unattended-upgrades.service 2>/dev/null || true
  systemctl stop apt-daily.service apt-daily-upgrade.service 2>/dev/null || true
  systemctl stop apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
  systemctl disable --now unattended-upgrades.service 2>/dev/null || true
  systemctl kill --kill-who=all unattended-upgrades.service 2>/dev/null || true
  # Do not force-kill dpkg mid-transaction unless it has been stuck a long time.
  ok "requested stop of background apt services"
}

apt_lock_busy() {
  local locks=(
    /var/lib/dpkg/lock-frontend
    /var/lib/dpkg/lock
    /var/cache/apt/archives/lock
    /var/lib/apt/lists/lock
  )
  local lock

  # Process checks (name is truncated to unattended-upgr on Linux)
  if pgrep -x unattended-upgr >/dev/null 2>&1; then
    echo "process:unattended-upgr"
    return 0
  fi
  if pgrep -x apt-get >/dev/null 2>&1; then
    echo "process:apt-get"
    return 0
  fi
  if pgrep -x apt >/dev/null 2>&1; then
    echo "process:apt"
    return 0
  fi
  if pgrep -x dpkg >/dev/null 2>&1; then
    echo "process:dpkg"
    return 0
  fi

  for lock in "${locks[@]}"; do
    if command -v fuser >/dev/null 2>&1; then
      if fuser "$lock" >/dev/null 2>&1; then
        echo "lock:$lock"
        return 0
      fi
    elif command -v lsof >/dev/null 2>&1; then
      if lsof "$lock" >/dev/null 2>&1; then
        echo "lock:$lock"
        return 0
      fi
    fi
  done

  # Last resort: try opening the frontend lock non-blocking with flock
  if command -v flock >/dev/null 2>&1; then
    if ! flock --nonblock /var/lib/dpkg/lock-frontend true 2>/dev/null; then
      echo "flock:/var/lib/dpkg/lock-frontend"
      return 0
    fi
  fi

  return 1
}

wait_for_apt() {
  local max_wait_seconds="${1:-1200}"
  local waited=0
  local holder=""

  info "Waiting for apt/dpkg locks (unattended-upgrades may be running)..."
  while (( waited < max_wait_seconds )); do
    holder="$(apt_lock_busy || true)"
    if [[ -z "$holder" ]]; then
      ok "apt is free (waited ${waited}s)"
      return 0
    fi

    if (( waited % 15 == 0 )); then
      warn "apt busy (${holder}) — waited ${waited}s / ${max_wait_seconds}s"
      ps -o pid,etime,cmd -C unattended-upgr,apt-get,apt,dpkg 2>/dev/null || true
    fi

    # Keep trying to stop background upgraders while we wait
    if (( waited > 0 && waited % 60 == 0 )); then
      stop_background_apt
    fi

    sleep 5
    waited=$((waited + 5))
  done

  fail "Timed out waiting for apt lock after ${max_wait_seconds}s. Run: ps aux | grep -E 'apt|dpkg|unattended'"
}

apt_update() {
  wait_for_apt
  local attempt
  for attempt in 1 2 3 4 5; do
    echo
    echo "$(yellow "\$") $(bold "apt-get update")  (attempt $attempt/5)"
    echo "$(cyan "────────────────────────────────────────────────────────────")"
    if apt-get update; then
      echo "$(cyan "────────────────────────────────────────────────────────────")"
      ok "exit 0"
      return 0
    fi
    warn "apt-get update failed — waiting for lock and retrying..."
    sleep 10
    wait_for_apt
  done
  fail "apt-get update failed after retries"
}

apt_install() {
  wait_for_apt
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    echo
    echo "$(yellow "\$") $(bold "apt-get install -y $*")  (attempt $attempt/10)"
    echo "$(cyan "────────────────────────────────────────────────────────────")"
    if apt-get install -y "$@"; then
      echo "$(cyan "────────────────────────────────────────────────────────────")"
      ok "exit 0"
      return 0
    fi
    warn "apt-get install failed (likely lock) — waiting and retrying..."
    stop_background_apt
    sleep 15
    wait_for_apt
  done
  fail "apt-get install failed after retries: $*"
}

# =============================================================================
need_root

echo
echo "$(bold "Wargaming server deploy")"
echo "Project dir : $PROJECT_DIR"
echo "ZIP URL     : $PROJECT_ZIP_URL"
echo "Python      : $PYTHON_BIN"
echo "Started at  : $(date)"
echo

SERVER_IP="$(detect_public_ip)"
info "Detected server IP: ${SERVER_IP:-unknown}"
if [[ -n "${SERVER_IP:-}" ]]; then
  if ask_yes_no "Use detected IP ($SERVER_IP) in Django ALLOWED_HOSTS?" "y"; then
    :
  else
    read -r -p "$(yellow "?") Enter public IP / hostname for ALLOWED_HOSTS: " SERVER_IP
  fi
else
  read -r -p "$(yellow "?") Enter public IP / hostname for ALLOWED_HOSTS: " SERVER_IP
fi
[[ -n "${SERVER_IP:-}" ]] || fail "SERVER_IP is required"

DO_SUPERUSER=false
if ask_yes_no "Create Django superuser interactively after migrate?" "y"; then
  DO_SUPERUSER=true
fi

DO_RETRAIN=true
if ask_yes_no "Pull $BASE_MODEL and build wargaming:unified? (slow / ~8GB)" "y"; then
  DO_RETRAIN=true
else
  DO_RETRAIN=false
fi

DO_UFW=true
if ask_yes_no "Configure UFW firewall (OpenSSH + port 8000)?" "y"; then
  DO_UFW=true
else
  DO_UFW=false
fi

# =============================================================================
banner "Install system packages + Python 3.13"
stop_background_apt
wait_for_apt

apt_update
apt_install \
  software-properties-common \
  curl \
  unzip \
  libarchive-tools \
  zstd \
  ca-certificates \
  build-essential \
  git \
  psmisc

if ! apt-cache show "$PYTHON_BIN" >/dev/null 2>&1; then
  info "Adding deadsnakes PPA for $PYTHON_BIN"
  wait_for_apt
  run add-apt-repository -y ppa:deadsnakes/ppa
  apt_update
fi

apt_install \
  "$PYTHON_BIN" \
  "${PYTHON_BIN}-venv" \
  "${PYTHON_BIN}-dev"

run "$PYTHON_BIN" --version

# =============================================================================
banner "Check architecture + GPU"
run dpkg --print-architecture
run uname -m
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || warn "nvidia-smi returned non-zero (GPU may be missing/driver issue)"
else
  warn "nvidia-smi not found — Ollama will run on CPU (much slower)"
  if ask_yes_no "Try auto-install NVIDIA drivers now? (needs reboot after)" "n"; then
    wait_for_apt
    run ubuntu-drivers autoinstall
    warn "Reboot the server, then re-run this script."
    exit 0
  fi
fi

# =============================================================================
banner "Install Ollama from GitHub release"
cd /tmp
run curl -fL "$OLLAMA_TARBALL_URL" -o ollama-linux-amd64.tar.zst
run curl -fL "$OLLAMA_SHA_URL" -o sha256sum.txt
info "Verifying checksum..."
sha256sum -c sha256sum.txt --ignore-missing
ok "checksum OK"

info "Removing old /usr/lib/ollama (if any)"
rm -rf /usr/lib/ollama
run tar --zstd -xf /tmp/ollama-linux-amd64.tar.zst -C /usr
run command -v ollama
run ollama --version

# =============================================================================
banner "Create Ollama system user"
if id ollama >/dev/null 2>&1; then
  ok "user ollama already exists"
else
  run useradd \
    --system \
    --user-group \
    --create-home \
    --home-dir /usr/share/ollama \
    --shell /usr/sbin/nologin \
    ollama
fi
usermod -aG video ollama || true
getent group render >/dev/null && usermod -aG render ollama || true
mkdir -p /usr/share/ollama
chown -R ollama:ollama /usr/share/ollama
ok "ollama home ready"

# =============================================================================
banner "Install Ollama systemd service"
tee /etc/systemd/system/ollama.service >/dev/null <<'EOF'
[Unit]
Description=Ollama Service
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/bin/ollama serve
Environment="HOME=/usr/share/ollama"
Environment="OLLAMA_HOST=127.0.0.1:11434"
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
ok "wrote /etc/systemd/system/ollama.service"

run systemctl daemon-reload
run systemctl enable --now ollama
run systemctl --no-pager --full status ollama || true
info "Waiting for Ollama API..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    ok "Ollama API is up"
    curl -fsS http://127.0.0.1:11434/api/version
    echo
    break
  fi
  sleep 1
  if [[ $i -eq 30 ]]; then
    fail "Ollama API did not become ready"
  fi
done

# =============================================================================
banner "Download project ZIP from GitHub"
mkdir -p "$PROJECT_DIR"

# Preserve runtime state across re-deploys
BACKUP_DIR="/tmp/wargaming-runtime-backup-$$"
mkdir -p "$BACKUP_DIR"
if [[ -d "$PROJECT_DIR/.venv" ]]; then
  info "Backing up existing .venv"
  cp -a "$PROJECT_DIR/.venv" "$BACKUP_DIR/.venv"
fi
if [[ -f "$PROJECT_DIR/db.sqlite3" ]]; then
  info "Backing up existing db.sqlite3"
  cp -a "$PROJECT_DIR/db.sqlite3" "$BACKUP_DIR/db.sqlite3"
  [[ -f "$PROJECT_DIR/db.sqlite3-journal" ]] && cp -a "$PROJECT_DIR/db.sqlite3-journal" "$BACKUP_DIR/db.sqlite3-journal"
fi

rm -f /tmp/Wargaming.zip
run curl -fL "$PROJECT_ZIP_URL" -o /tmp/Wargaming.zip

info "Clearing $PROJECT_DIR"
find "$PROJECT_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

run bsdtar --strip-components 1 -xf /tmp/Wargaming.zip -C "$PROJECT_DIR"
ok "extracted project"

if [[ -d "$BACKUP_DIR/.venv" ]]; then
  info "Restoring .venv"
  cp -a "$BACKUP_DIR/.venv" "$PROJECT_DIR/.venv"
fi
if [[ -f "$BACKUP_DIR/db.sqlite3" ]]; then
  info "Restoring db.sqlite3"
  cp -a "$BACKUP_DIR/db.sqlite3" "$PROJECT_DIR/db.sqlite3"
  [[ -f "$BACKUP_DIR/db.sqlite3-journal" ]] && cp -a "$BACKUP_DIR/db.sqlite3-journal" "$PROJECT_DIR/db.sqlite3-journal"
fi
rm -rf "$BACKUP_DIR"

run ls -la "$PROJECT_DIR"

# =============================================================================
banner "Patch ALLOWED_HOSTS for this server IP"
CONFIG_FILE="$PROJECT_DIR/war_game/project_config.py"
if [[ -f "$CONFIG_FILE" ]]; then
  info "Updating DJANGO_ALLOWED_HOSTS to include $SERVER_IP"
  "$PYTHON_BIN" - <<PY
from pathlib import Path
path = Path("$CONFIG_FILE")
text = path.read_text(encoding="utf-8")
needle = 'DJANGO_ALLOWED_HOSTS = ['
start = text.find(needle)
if start < 0:
    raise SystemExit("DJANGO_ALLOWED_HOSTS not found")
end = text.find(']', start)
hosts = ['"$SERVER_IP"', '"localhost"', '"127.0.0.1"']
# keep unique order
seen = set()
ordered = []
for h in hosts:
    if h not in seen:
        seen.add(h)
        ordered.append(h)
new_line = "DJANGO_ALLOWED_HOSTS = [" + ", ".join(ordered) + "]"
# replace whole assignment line(s) until closing ]
line_end = text.find("\n", end)
new_text = text[:start] + new_line + text[line_end:]
path.write_text(new_text, encoding="utf-8")
print(new_line)
PY
  ok "patched $CONFIG_FILE"
else
  warn "config file missing: $CONFIG_FILE"
fi

# =============================================================================
banner "Create Python 3.13 venv + install deps"
cd "$PROJECT_DIR"
if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  run "$PYTHON_BIN" -m venv .venv
else
  ok ".venv already present (restored)"
fi

# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"
run python -m pip install --upgrade pip setuptools wheel
run pip install -r requirements.txt
run python --version
run gunicorn --version

# =============================================================================
banner "Django migrate / seed / collectstatic"
cd "$PROJECT_DIR"
# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"
run python manage.py migrate
run python manage.py seed_admin_data --force
run python manage.py collectstatic --noinput
run python manage.py check --deploy || warn "check --deploy reported issues (continuing)"

# =============================================================================
banner "Optional: create Django superuser"
if [[ "$DO_SUPERUSER" == true ]]; then
  echo
  warn "Interactive step — enter username / email / password"
  echo "$(yellow "\$") python manage.py createsuperuser"
  echo "$(cyan "────────────────────────────────────────────────────────────")"
  # Do not fail the whole deploy if user aborts
  set +e
  python manage.py createsuperuser
  rc=$?
  set -e
  echo "$(cyan "────────────────────────────────────────────────────────────")"
  if [[ $rc -eq 0 ]]; then
    ok "superuser created"
  else
    warn "createsuperuser skipped or failed (exit $rc) — continue"
  fi
else
  info "Skipped createsuperuser"
fi

# =============================================================================
banner "Ollama model pull + build wargaming:unified"
if [[ "$DO_RETRAIN" == true ]]; then
  cd "$PROJECT_DIR"
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"
  run ollama pull "$BASE_MODEL"
  run python manage.py retrain_wargaming_llm --model "$BASE_MODEL" --force
  run ollama list
else
  warn "Skipped model pull/retrain — chat will fail until you run it later"
fi

# =============================================================================
banner "Install Wargaming systemd service"
tee /etc/systemd/system/wargaming.service >/dev/null <<EOF
[Unit]
Description=Wargaming Django Gunicorn Service
Wants=network-online.target
After=network-online.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$PROJECT_DIR/.venv/bin/gunicorn war_game.wsgi:application --bind $APP_BIND --workers $GUNICORN_WORKERS --timeout $GUNICORN_TIMEOUT --access-logfile - --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
ok "wrote /etc/systemd/system/wargaming.service"

run systemctl daemon-reload
run systemctl enable --now wargaming
run systemctl --no-pager --full status wargaming || true

# =============================================================================
banner "Firewall (UFW)"
if [[ "$DO_UFW" == true ]]; then
  run ufw allow OpenSSH
  run ufw allow 8000/tcp
  # non-interactive enable
  ufw --force enable
  run ufw status
else
  info "Skipped UFW"
fi

# =============================================================================
banner "Final verification"
run systemctl is-active ollama
run systemctl is-active wargaming
run curl -fsS http://127.0.0.1:11434/api/version
echo
curl -I http://127.0.0.1:8000/chat/ || warn "HTTP check failed — see journalctl -u wargaming"
echo

cd "$PROJECT_DIR"
# shellcheck disable=SC1091
source "$PROJECT_DIR/.venv/bin/activate"
if [[ -f test_system.py ]]; then
  set +e
  python test_system.py
  set -e
fi

echo
echo "$(green "════════════════════════════════════════════════════════════")"
echo "$(bold "$(green "DEPLOY COMPLETE")")"
echo "$(green "════════════════════════════════════════════════════════════")"
echo "Chat UI : http://$SERVER_IP:8000/chat/"
echo "Admin   : http://$SERVER_IP:8000/admin/"
echo
echo "Useful commands:"
echo "  systemctl status ollama wargaming"
echo "  journalctl -u wargaming -f"
echo "  journalctl -u ollama -n 100 --no-pager"
echo
echo "Quick re-deploy later (same script):"
echo "  bash $PROJECT_DIR/deploy_server.sh"
echo "  # or download fresh script from ZIP again"
echo
echo "Finished at: $(date)"
