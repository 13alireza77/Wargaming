#!/usr/bin/env bash
set -Eeuo pipefail

# =============================================================================
# 1/3 — Build Docker images + Ollama models into a portable offline bundle.
#
# IMPORTANT: Offline servers are usually linux/amd64, so images are built for
# --platform linux/amd64 by default, even on an ARM Mac.
#
# Ollama model weights are architecture independent, so they are downloaded by
# a container running the HOST architecture. The amd64 Ollama binary crashes
# ("fatal error: found pointer to free object") under Docker's amd64-on-ARM
# emulation, which is why model downloads must not be emulated.
#
# Everything expensive (image tarballs, model archive, model weights) is cached
# and reused while its inputs are unchanged, so a rebuild after a code change
# only redoes the app image.
#
# Output: <output-dir>/wargaming-offline-bundle/   (+ optional single .tar)
# =============================================================================

OUTPUT_DIR="./offline-dist"
CACHE_DIR=""
APP_IMAGE="wargaming-app:latest"
OLLAMA_IMAGE="ollama/ollama:latest"
BASE_IMAGE="python:3.13-slim"
INCLUDE_OLLAMA_IMAGE=1
INCLUDE_OLLAMA_MODELS=1
OLLAMA_MODELS="gemma3:12b"
# Target server arch. Override only if your offline server is ARM.
PLATFORM="linux/amd64"
# Platform used to download models. Empty = host arch (never emulated).
MODEL_PLATFORM=""
COMPRESS_IMAGES=1
MAKE_ARCHIVE=0
FORCE=0
REFRESH_IMAGES=0
PRUNE_STALE_VOLUMES=0
# Model weights are arch independent, so one cache volume serves every platform.
MODEL_CACHE_VOLUME="wargaming-offline-model-cache"
LEGACY_CACHE_VOLUME_PREFIX="wargaming-offline-model-cache"
# Seconds to wait for the temporary Ollama API to answer.
OLLAMA_READY_SECONDS=180
# Cached artifact generations to keep per kind.
CACHE_KEEP=3

usage() {
  cat <<'EOF'
Usage:
  bash docker-build-offline.sh [options]

Options:
  --output-dir <path>          Where to write the bundle. Default: ./offline-dist
  --cache-dir <path>           Reusable artifact cache. Default: <repo>/.offline-cache
  --app-image <name:tag>       App image name. Default: wargaming-app:latest
  --ollama-image <name:tag>    Ollama image name. Default: ollama/ollama:latest
  --platform <platform>        Target platform. Default: linux/amd64
                               Use linux/arm64 only if the OFFLINE server is ARM.
  --model-platform <platform>  Platform of the throwaway container that downloads
                               models. Default: host arch (recommended).
  --ollama-models <csv>        Models to pull and pack. Default: gemma3:12b
  --skip-ollama-image          Don't include the Ollama Docker image
  --skip-ollama-models         Don't download/pack model weights
  --archive                    Also pack the bundle into a single .tar file
  --no-compress-images         Store image tarballs uncompressed (faster, bigger)
  --refresh-images             Re-pull base/Ollama images even if already local
  --force                      Ignore the artifact cache and rebuild everything
  --prune-stale-volumes        Delete leftover wargaming-offline-models-* volumes
  --help                       Show this help

Examples:
  # Correct for most Linux servers (x86_64 / amd64), even when building on Mac M1/M2/M3:
  bash docker-build-offline.sh --output-dir ./offline-dist

  # Same, but also produce one single file for scp:
  bash docker-build-offline.sh --output-dir ./offline-dist --archive

  # Only if the offline server itself is ARM:
  bash docker-build-offline.sh --platform linux/arm64
EOF
}

log()  { printf '[docker-build-offline] %s\n' "$*"; }
warn() { printf '[docker-build-offline][WARN] %s\n' "$*" >&2; }
err()  { printf '[docker-build-offline][ERROR] %s\n' "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

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

host_platform() {
  local machine
  machine="$(uname -m)"
  case "$machine" in
    arm64|aarch64) echo "linux/arm64" ;;
    x86_64|amd64)  echo "linux/amd64" ;;
    *)             echo "linux/${machine}" ;;
  esac
}

image_id() { docker image inspect "$1" --format '{{.Id}}' 2>/dev/null || true; }

image_matches_platform() {
  local got
  got="$(docker image inspect "$1" --format '{{.Os}}/{{.Architecture}}' 2>/dev/null || true)"
  [[ "$got" == "$2" ]]
}

# Keep one local tag per platform: Docker can only hold a single image per tag,
# so pulling ollama for the host arch would otherwise drop the amd64 one.
ensure_image_platform() {
  local ref="$1" platform="$2" alias="$3"
  if [[ "$REFRESH_IMAGES" -eq 0 ]] && image_matches_platform "$alias" "$platform"; then
    log "Reusing local image for $platform: $ref"
    return 0
  fi
  if [[ "$REFRESH_IMAGES" -eq 0 ]] && image_matches_platform "$ref" "$platform"; then
    docker tag "$ref" "$alias"
    log "Reusing local image for $platform: $ref"
    return 0
  fi
  log "Pulling $ref for $platform ..."
  retry_cmd 5 docker pull --platform "$platform" "$ref" || return 1
  docker tag "$ref" "$alias"
}

sanitize() { printf '%s' "$1" | tr '/:' '__'; }

# File ops use create+cp (no container start). Prefer the app image we just built
# so we never need an extra alpine pull while Docker Desktop's run path is broken.
HELPER_IMAGE=""
HELPER_PLATFORM=""
pick_helper_image() {
  [[ -z "$HELPER_IMAGE" ]] || return 0
  if image_matches_platform "$APP_IMAGE" "$PLATFORM"; then
    HELPER_IMAGE="$APP_IMAGE"
    HELPER_PLATFORM="$PLATFORM"
  elif image_matches_platform "$OLLAMA_ALIAS_TARGET" "$PLATFORM"; then
    HELPER_IMAGE="$OLLAMA_ALIAS_TARGET"
    HELPER_PLATFORM="$PLATFORM"
  else
    HELPER_IMAGE="$APP_IMAGE"
    HELPER_PLATFORM="$PLATFORM"
  fi
  log "File helper image: $HELPER_IMAGE ($HELPER_PLATFORM)"
}

# Ollama stores every model under models/manifests/<host>/<namespace>/<name>/<tag>
model_manifest_path() {
  local model="$1" host repo tag rest first
  rest="$model"
  tag="latest"
  case "$rest" in
    *:*) tag="${rest##*:}"; rest="${rest%:*}" ;;
  esac
  case "$rest" in
    */*/*)
      host="${rest%%/*}"
      repo="${rest#*/}"
      ;;
    */*)
      first="${rest%%/*}"
      case "$first" in
        *.*|localhost) host="$first"; repo="library/${rest#*/}" ;;
        *)             host="registry.ollama.ai"; repo="$rest" ;;
      esac
      ;;
    *)
      host="registry.ollama.ai"
      repo="library/$rest"
      ;;
  esac
  printf 'models/manifests/%s/%s/%s' "$host" "$repo" "$tag"
}

wait_for_ollama_api() {
  local seconds="$1" waited=0
  while (( waited < seconds )); do
    if [[ "$(docker inspect -f '{{.State.Running}}' "$TMP_OLLAMA" 2>/dev/null || echo false)" == "true" ]]; then
      if docker exec "$TMP_OLLAMA" /bin/ollama list >/dev/null 2>&1; then
        return 0
      fi
    elif docker ps -a --format '{{.Names}}' | grep -Fxq "$TMP_OLLAMA"; then
      log "Temporary Ollama container stopped; restarting..."
      docker start "$TMP_OLLAMA" >/dev/null 2>&1 || true
    fi
    if (( waited % 20 == 0 )); then
      log "Waiting for Ollama API... (${waited}/${seconds}s)"
    fi
    sleep 2
    waited=$((waited + 2))
  done

  log "Temporary Ollama container state:"
  docker inspect "$TMP_OLLAMA" --format 'status={{.State.Status}} exit={{.State.ExitCode}} error={{.State.Error}}' 2>/dev/null || true
  log "Temporary Ollama container logs (tail):"
  docker logs "$TMP_OLLAMA" --tail 30 2>&1 || true
  return 1
}

# Interrupted downloads resume from the partial blobs kept in the cache volume.
pull_model_with_retry() {
  local model="$1" attempt
  for attempt in 1 2 3 4 5; do
    wait_for_ollama_api "$OLLAMA_READY_SECONDS" || return 1
    if docker exec "$TMP_OLLAMA" /bin/ollama pull "$model"; then
      return 0
    fi
    log "Model pull failed for $model (attempt $attempt/5); resuming after a pause..."
    docker logs "$TMP_OLLAMA" --tail 20 2>&1 | tail -20 || true
    sleep $((attempt * 5))
  done
  return 1
}

# Prefer the native host ollama binary when Docker cannot pull/run images
# (common on Docker Desktop when containerd.sock is flaky).
HOST_OLLAMA_PID=""
stop_host_ollama() {
  if [[ -n "${HOST_OLLAMA_PID:-}" ]] && kill -0 "$HOST_OLLAMA_PID" 2>/dev/null; then
    kill "$HOST_OLLAMA_PID" 2>/dev/null || true
    wait "$HOST_OLLAMA_PID" 2>/dev/null || true
  fi
  HOST_OLLAMA_PID=""
}

download_models_via_host_ollama() {
  local models=("$@")
  local store port attempt model waited
  have ollama || return 1

  store="$CACHE_DIR/host-ollama-home"
  mkdir -p "$store/models"
  port=11435

  stop_host_ollama
  # Do not overwrite the script's OLLAMA_MODELS list variable — pass env via env(1).
  env OLLAMA_MODELS="$store/models" OLLAMA_HOST="127.0.0.1:${port}" \
    ollama serve >"$WORK_DIR/host-ollama-serve.log" 2>&1 &
  HOST_OLLAMA_PID=$!

  waited=0
  while (( waited < 60 )); do
    if curl -sf "http://127.0.0.1:${port}/" >/dev/null 2>&1; then
      break
    fi
    if ! kill -0 "$HOST_OLLAMA_PID" 2>/dev/null; then
      HOST_OLLAMA_PID=""
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
  if ! curl -sf "http://127.0.0.1:${port}/" >/dev/null 2>&1; then
    stop_host_ollama
    return 1
  fi

  for model in "${models[@]}"; do
    [[ -n "$model" ]] || continue
    log "Downloading model via host ollama: $model"
    for attempt in 1 2 3; do
      if env OLLAMA_HOST="127.0.0.1:${port}" ollama pull "$model"; then
        break
      fi
      [[ "$attempt" -lt 3 ]] || { stop_host_ollama; return 1; }
      log "Host pull failed for $model (attempt $attempt/3); retrying..."
      sleep $((attempt * 3))
    done
  done

  stop_host_ollama

  log "Importing host-downloaded models into Docker volume (create+cp, no docker run)..."
  docker rm -f "${TMP_FS}-rw" >/dev/null 2>&1 || true
  docker create --name "${TMP_FS}-rw" --platform "$HELPER_PLATFORM" \
    -v "$MODEL_CACHE_VOLUME:/d" "$HELPER_IMAGE" sh >/dev/null
  docker cp "$store/." "${TMP_FS}-rw:/d/"
  docker rm -f "${TMP_FS}-rw" >/dev/null 2>&1 || true
  return 0
}

download_models_via_docker_ollama() {
  local models=("$@")
  ensure_image_platform "$OLLAMA_IMAGE" "$MODEL_PLATFORM" "$OLLAMA_ALIAS_MODEL" ||
    return 1

  log "Starting temporary Ollama container ($MODEL_PLATFORM) to download models..."
  set +e
  run_out="$(docker run -d --name "$TMP_OLLAMA" \
    --platform "$MODEL_PLATFORM" \
    -v "$MODEL_CACHE_VOLUME:/root/.ollama" \
    "$OLLAMA_ALIAS_MODEL" 2>&1)"
  run_rc=$?
  set -e
  if [[ "$run_rc" -ne 0 ]]; then
    printf '%s\n' "$run_out" >&2
    return 1
  fi
  wait_for_ollama_api "$OLLAMA_READY_SECONDS" || return 1

  for model in "${models[@]}"; do
    [[ -n "$model" ]] || continue
    log "Downloading model into cache: $model  (large download — first time only)"
    pull_model_with_retry "$model" || return 1
  done

  log "Models in cache:"
  docker exec "$TMP_OLLAMA" /bin/ollama list || true
  docker rm -f "$TMP_OLLAMA" >/dev/null 2>&1 || true
  return 0
}

link_into_bundle() {
  local src="$1" dst="$2"
  rm -f "$dst"
  ln "$src" "$dst" 2>/dev/null || cp "$src" "$dst"
}

prune_cache() {
  local dir="$1" pattern="$2" keep="$3"
  local files count
  files="$(ls -t "$dir"/$pattern 2>/dev/null || true)"
  [[ -n "$files" ]] || return 0
  count=0
  local f
  while IFS= read -r f; do
    count=$((count + 1))
    if (( count > keep )); then
      rm -f "$f"
    fi
  done <<< "$files"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)           OUTPUT_DIR="${2:-}"; shift 2 ;;
    --cache-dir)            CACHE_DIR="${2:-}"; shift 2 ;;
    --app-image)            APP_IMAGE="${2:-}"; shift 2 ;;
    --ollama-image)         OLLAMA_IMAGE="${2:-}"; shift 2 ;;
    --platform)             PLATFORM="${2:-}"; shift 2 ;;
    --model-platform)       MODEL_PLATFORM="${2:-}"; shift 2 ;;
    --ollama-models)        OLLAMA_MODELS="${2:-}"; shift 2 ;;
    --skip-ollama-image)    INCLUDE_OLLAMA_IMAGE=0; shift ;;
    --skip-ollama-models)   INCLUDE_OLLAMA_MODELS=0; shift ;;
    --archive)              MAKE_ARCHIVE=1; shift ;;
    --no-compress-images)   COMPRESS_IMAGES=0; shift ;;
    --refresh-images)       REFRESH_IMAGES=1; shift ;;
    --force)                FORCE=1; shift ;;
    --prune-stale-volumes)  PRUNE_STALE_VOLUMES=1; shift ;;
    --help|-h)              usage; exit 0 ;;
    *)                      err "Unknown argument: $1" ;;
  esac
done

have docker || err "docker not found"
docker info >/dev/null 2>&1 || err "docker daemon is not reachable (is Docker Desktop running?)"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SCRIPT="$PROJECT_ROOT/docker-run-offline.sh"
[[ -f "$RUN_SCRIPT" ]] || err "missing $RUN_SCRIPT (keep all three scripts in the repo)"
[[ -f "$PROJECT_ROOT/docker-compose.yml" ]] || err "missing $PROJECT_ROOT/docker-compose.yml"

HOST_PLATFORM="$(host_platform)"
[[ -n "$MODEL_PLATFORM" ]] || MODEL_PLATFORM="$HOST_PLATFORM"
[[ -n "$CACHE_DIR" ]] || CACHE_DIR="$PROJECT_ROOT/.offline-cache"

mkdir -p "$OUTPUT_DIR" "$CACHE_DIR/images" "$CACHE_DIR/models"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
CACHE_DIR="$(cd "$CACHE_DIR" && pwd)"

# Prevent concurrent builds from thrashing Docker Desktop / containerd.
LOCK_DIR="$CACHE_DIR/build.lock.dir"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  err "another docker-build-offline.sh is already running (lock: $LOCK_DIR). If stale, remove that directory and retry."
fi
cleanup_lock() { rmdir "$LOCK_DIR" 2>/dev/null || true; }

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BUNDLE_DIR="$OUTPUT_DIR/wargaming-offline-bundle"
TMP_OLLAMA="wargaming-offline-ollama-$$"
TMP_FS="wargaming-offline-fs-$$"
OLLAMA_ALIAS_TARGET="wargaming-offline-cache/ollama:$(sanitize "$PLATFORM")"
OLLAMA_ALIAS_MODEL="wargaming-offline-cache/ollama:$(sanitize "$MODEL_PLATFORM")"

log "Host arch       : $HOST_PLATFORM"
log "Target platform : $PLATFORM"
log "Model download  : $MODEL_PLATFORM (weights are architecture independent)"
log "Cache dir       : $CACHE_DIR"
if [[ "$HOST_PLATFORM" != "$PLATFORM" ]]; then
  log "Building $PLATFORM images on a $HOST_PLATFORM host via Docker emulation."
fi

cleanup() {
  stop_host_ollama
  docker rm -f "$TMP_OLLAMA" >/dev/null 2>&1 || true
  docker rm -f "$TMP_FS" >/dev/null 2>&1 || true
  docker rm -f "${TMP_FS}-rw" >/dev/null 2>&1 || true
  if [[ -n "${WORK_DIR:-}" ]]; then
    rm -rf "$WORK_DIR"
  fi
  cleanup_lock
}
trap cleanup EXIT

# Keep temp work outside the repo so docker build context never includes it.
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/wargaming-offline-XXXXXX")"

if [[ "$PRUNE_STALE_VOLUMES" -eq 1 ]]; then
  STALE="$(docker volume ls --format '{{.Name}}' | grep -E '^wargaming-offline-models-' || true)"
  if [[ -n "$STALE" ]]; then
    log "Removing stale per-run model volumes:"
    printf '  %s\n' $STALE
    # shellcheck disable=SC2086
    docker volume rm $STALE >/dev/null || true
  fi
fi

# ── 1. App image ────────────────────────────────────────────────────────────
if [[ "$REFRESH_IMAGES" -eq 1 ]] || ! image_matches_platform "$BASE_IMAGE" "$PLATFORM"; then
  log "Pulling base image $BASE_IMAGE ($PLATFORM) ..."
  retry_cmd 5 docker pull --platform "$PLATFORM" "$BASE_IMAGE" ||
    err "failed to pull base image $BASE_IMAGE after retries"
else
  log "Base image $BASE_IMAGE already present for $PLATFORM."
fi

log "Building app image: $APP_IMAGE ($PLATFORM) ..."
retry_cmd 3 docker build \
  --platform "$PLATFORM" \
  -t "$APP_IMAGE" \
  "$PROJECT_ROOT" || err "docker build failed after retries"
image_matches_platform "$APP_IMAGE" "$PLATFORM" ||
  err "$APP_IMAGE is not $PLATFORM — rebuild with --refresh-images"

# ── 2. Ollama image for the target server ───────────────────────────────────
if [[ "$INCLUDE_OLLAMA_IMAGE" -eq 1 ]]; then
  ensure_image_platform "$OLLAMA_IMAGE" "$PLATFORM" "$OLLAMA_ALIAS_TARGET" ||
    err "failed to pull $OLLAMA_IMAGE for $PLATFORM"
fi

# ── 3. Model weights (downloaded on the host architecture) ──────────────────
MODEL_ARCHIVE=""
if [[ "$INCLUDE_OLLAMA_MODELS" -eq 1 ]]; then
  [[ "$INCLUDE_OLLAMA_IMAGE" -eq 1 ]] || err "--skip-ollama-image cannot be used with model packing"

  # Reuse weights downloaded by older versions of this script.
  if ! docker volume inspect "$MODEL_CACHE_VOLUME" >/dev/null 2>&1; then
    LEGACY_VOLUME="$(docker volume ls --format '{{.Name}}' |
      grep -E "^${LEGACY_CACHE_VOLUME_PREFIX}-" | head -1 || true)"
    if [[ -n "$LEGACY_VOLUME" ]]; then
      MODEL_CACHE_VOLUME="$LEGACY_VOLUME"
      log "Reusing existing model cache volume: $MODEL_CACHE_VOLUME"
    else
      docker volume create "$MODEL_CACHE_VOLUME" >/dev/null
    fi
  fi
  log "Model cache volume: $MODEL_CACHE_VOLUME"

  pick_helper_image

  IFS=',' read -r -a requested_models <<< "$OLLAMA_MODELS"
  CHECK_ARGS=""
  MODEL_LIST=""
  model_count=0
  model_manifest_hash_input=""
  mkdir -p "$WORK_DIR/model-manifests"
  for model in "${requested_models[@]}"; do
    trimmed="$(echo "$model" | xargs)"
    [[ -n "$trimmed" ]] || continue
    MODEL_LIST="$MODEL_LIST $trimmed"
    CHECK_ARGS="$CHECK_ARGS $trimmed=$(model_manifest_path "$trimmed")"
    model_count=$((model_count + 1))
  done
  [[ -n "$MODEL_LIST" ]] || err "--ollama-models is empty"

  # Use create+cp instead of run for cache inspection. This works even when
  # desktop-containerd refuses run/start requests.
  docker rm -f "$TMP_FS" >/dev/null 2>&1 || true
  docker create --name "$TMP_FS" --platform "$HELPER_PLATFORM" \
    -v "$MODEL_CACHE_VOLUME:/d:ro" "$HELPER_IMAGE" sh >/dev/null

  MISSING=""
  # shellcheck disable=SC2086
  for kv in $CHECK_ARGS; do
    name="${kv%%=*}"
    path="${kv#*=}"
    out_file="$WORK_DIR/model-manifests/$name.manifest"
    if docker cp "$TMP_FS:/d/$path" "$out_file" >/dev/null 2>&1; then
      hash="$( (shasum -a 256 "$out_file" 2>/dev/null || sha256sum "$out_file") | awk '{print $1}')"
      model_manifest_hash_input="${model_manifest_hash_input}${name}:${hash}"$'\n'
    else
      MISSING="${MISSING}${name}"$'\n'
    fi
  done

  if [[ -n "$MISSING" ]]; then
    missing_arr=()
    while IFS= read -r m; do
      [[ -n "$m" ]] && missing_arr+=("$m")
    done <<< "$MISSING"

    if download_models_via_host_ollama "${missing_arr[@]}"; then
      log "Downloaded missing models via host ollama (bypassed broken docker pull/run)."
    elif download_models_via_docker_ollama "${missing_arr[@]}"; then
      log "Downloaded missing models via Docker Ollama container."
    else
      err "failed to download missing models: ${missing_arr[*]}. If Docker shows containerd.sock errors, restart Docker Desktop OR install/use host ollama (already preferred when available)."
    fi

    # Recreate fs helper so docker cp sees freshly downloaded manifests/blobs.
    docker rm -f "$TMP_FS" >/dev/null 2>&1 || true
    docker create --name "$TMP_FS" --platform "$HELPER_PLATFORM" \
      -v "$MODEL_CACHE_VOLUME:/d:ro" "$HELPER_IMAGE" sh >/dev/null
  else
    log "All requested models already in cache:$MODEL_LIST"
  fi

  # Refresh manifest hashes after any potential downloads.
  model_manifest_hash_input=""
  # shellcheck disable=SC2086
  for kv in $CHECK_ARGS; do
    name="${kv%%=*}"
    path="${kv#*=}"
    out_file="$WORK_DIR/model-manifests/$name.manifest"
    docker cp "$TMP_FS:/d/$path" "$out_file" >/dev/null 2>&1 || err "model manifest missing after sync: $name"
    hash="$( (shasum -a 256 "$out_file" 2>/dev/null || sha256sum "$out_file") | awk '{print $1}')"
    model_manifest_hash_input="${model_manifest_hash_input}${name}:${hash}"$'\n'
  done

  MODEL_KEY="$(printf '%s\n%s' "$MODEL_LIST" "$model_manifest_hash_input" |
    { shasum -a 256 2>/dev/null || sha256sum; } | cut -c1-16)"
  MODEL_ARCHIVE="$CACHE_DIR/models/ollama-models-$MODEL_KEY.tar"

  if [[ "$FORCE" -eq 0 && -s "$MODEL_ARCHIVE" ]]; then
    log "Reusing cached model archive: $(basename "$MODEL_ARCHIVE")"
  else
    log "Archiving model weights (one-time per model set, several GB)..."
    rm -rf "$WORK_DIR/ollama-data" && mkdir -p "$WORK_DIR/ollama-data"
    docker cp "$TMP_FS:/d/." "$WORK_DIR/ollama-data/"
    tar -cf "$WORK_DIR/ollama-models.tar" -C "$WORK_DIR/ollama-data" .
    mv "$WORK_DIR/ollama-models.tar" "$MODEL_ARCHIVE"
  fi
else
  log "Skipping Ollama model packing (--skip-ollama-models)."
fi

# ── 4. Image tarballs (cached by image id) ──────────────────────────────────
save_image() {
  local image="$1" out_name="$2" id short cached
  id="$(image_id "$image")"
  [[ -n "$id" ]] || err "image not found: $image"
  short="$(printf '%s' "${id#sha256:}" | cut -c1-12)"
  if [[ "$COMPRESS_IMAGES" -eq 1 ]]; then
    cached="$CACHE_DIR/images/${out_name}-${short}.tar.gz"
  else
    cached="$CACHE_DIR/images/${out_name}-${short}.tar"
  fi

  if [[ "$FORCE" -eq 0 && -s "$cached" ]]; then
    log "Reusing cached image tarball: $(basename "$cached")" >&2
  else
    log "Saving $image ..." >&2
    if [[ "$COMPRESS_IMAGES" -eq 1 ]]; then
      if have pigz; then
        docker save "$image" | pigz -6 > "$WORK_DIR/save.tmp"
      else
        docker save "$image" | gzip -1 > "$WORK_DIR/save.tmp"
      fi
    else
      docker save "$image" > "$WORK_DIR/save.tmp"
    fi
    mv "$WORK_DIR/save.tmp" "$cached"
  fi
  printf '%s' "$cached"
}

APP_TAR="$(save_image "$APP_IMAGE" "$(sanitize "$APP_IMAGE")-$(sanitize "$PLATFORM")")"
[[ -s "$APP_TAR" ]] || err "failed to save $APP_IMAGE"

OLLAMA_TAR=""
if [[ "$INCLUDE_OLLAMA_IMAGE" -eq 1 ]]; then
  # Restore the canonical tag so the bundle loads the name docker-compose expects.
  docker tag "$OLLAMA_ALIAS_TARGET" "$OLLAMA_IMAGE"
  OLLAMA_TAR="$(save_image "$OLLAMA_IMAGE" "$(sanitize "$OLLAMA_IMAGE")-$(sanitize "$PLATFORM")")"
  [[ -s "$OLLAMA_TAR" ]] || err "failed to save $OLLAMA_IMAGE"
fi

# ── 5. Assemble the bundle directory (hardlinks — no copying) ───────────────
log "Assembling bundle: $BUNDLE_DIR"
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

APP_TAR_NAME="wargaming-app.tar"
if [[ "$APP_TAR" == *.gz ]]; then
  APP_TAR_NAME="wargaming-app.tar.gz"
fi
link_into_bundle "$APP_TAR" "$BUNDLE_DIR/$APP_TAR_NAME"

if [[ -n "$OLLAMA_TAR" ]]; then
  OLLAMA_TAR_NAME="ollama.tar"
  if [[ "$OLLAMA_TAR" == *.gz ]]; then
    OLLAMA_TAR_NAME="ollama.tar.gz"
  fi
  link_into_bundle "$OLLAMA_TAR" "$BUNDLE_DIR/$OLLAMA_TAR_NAME"
fi

if [[ -n "$MODEL_ARCHIVE" ]]; then
  link_into_bundle "$MODEL_ARCHIVE" "$BUNDLE_DIR/ollama-models.tar"
fi

cp "$PROJECT_ROOT/docker-compose.yml" "$BUNDLE_DIR/docker-compose.yml"
cp "$RUN_SCRIPT" "$BUNDLE_DIR/docker-run-offline.sh"
chmod +x "$BUNDLE_DIR/docker-run-offline.sh"

cat > "$BUNDLE_DIR/manifest.env" <<EOF
BUNDLE_CREATED_AT=$TIMESTAMP
APP_IMAGE=$APP_IMAGE
OLLAMA_IMAGE=$OLLAMA_IMAGE
PLATFORM=$PLATFORM
INCLUDE_OLLAMA_IMAGE=$INCLUDE_OLLAMA_IMAGE
INCLUDE_OLLAMA_MODELS=$INCLUDE_OLLAMA_MODELS
OLLAMA_MODELS=$OLLAMA_MODELS
EOF

log "App image arch  : $(docker image inspect "$APP_IMAGE" --format '{{.Os}}/{{.Architecture}}')"
if [[ "$INCLUDE_OLLAMA_IMAGE" -eq 1 ]]; then
  log "Ollama image arch: $(docker image inspect "$OLLAMA_IMAGE" --format '{{.Os}}/{{.Architecture}}')"
fi

ARCHIVE=""
if [[ "$MAKE_ARCHIVE" -eq 1 ]]; then
  # Members are already compressed, so the outer tar is stored, not gzipped.
  ARCHIVE="$OUTPUT_DIR/wargaming-docker-offline-$TIMESTAMP.tar"
  log "Packing single-file archive: $ARCHIVE ..."
  tar -cf "$ARCHIVE" -C "$BUNDLE_DIR" .
fi

prune_cache "$CACHE_DIR/images" "$(sanitize "$APP_IMAGE")-$(sanitize "$PLATFORM")-*" "$CACHE_KEEP"
prune_cache "$CACHE_DIR/models" "ollama-models-*.tar" "$CACHE_KEEP"

log ""
log "Done."
log "Bundle dir : $BUNDLE_DIR ($(du -sh "$BUNDLE_DIR" | awk '{print $1}'))"
if [[ -n "$ARCHIVE" ]]; then
  log "Archive    : $ARCHIVE ($(du -h "$ARCHIVE" | awk '{print $1}'))"
fi
log "Cache dir  : $CACHE_DIR ($(du -sh "$CACHE_DIR" | awk '{print $1}')) — keep it to make the next build fast"
log ""
log "Next:"
if [[ -n "$ARCHIVE" ]]; then
  log "  bash docker-upload-offline.sh --bundle-file $ARCHIVE --server SERVER_IP --user root"
  log "  # then on the server:"
  log "  sudo bash docker-run-offline.sh --bundle-file ./$(basename "$ARCHIVE")"
else
  log "  bash docker-upload-offline.sh --bundle-dir $BUNDLE_DIR --server SERVER_IP --user root"
  log "  # then on the server:"
  log "  cd /opt/wargaming-offline && sudo bash docker-run-offline.sh"
fi
