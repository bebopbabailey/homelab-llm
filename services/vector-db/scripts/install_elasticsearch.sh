#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${MEMORY_ELASTIC_RUNTIME_DIR:-$ROOT_DIR/runtime}"
ELASTIC_VERSION="${MEMORY_ELASTIC_VERSION:-9.3.3}"
ELASTIC_ARCHIVE="elasticsearch-${ELASTIC_VERSION}-darwin-aarch64.tar.gz"
ELASTIC_BASE_URL="${MEMORY_ELASTIC_ARTIFACT_BASE:-https://artifacts.elastic.co/downloads/elasticsearch}"
ELASTIC_URL="${ELASTIC_BASE_URL}/${ELASTIC_ARCHIVE}"
ELASTIC_SHA_URL="${ELASTIC_URL}.sha512"
DOWNLOAD_DIR="${RUNTIME_DIR}/downloads"
INSTALL_DIR="${RUNTIME_DIR}/elasticsearch-${ELASTIC_VERSION}"
CURRENT_LINK="${RUNTIME_DIR}/elasticsearch-current"
CONFIG_DIR="${RUNTIME_DIR}/elasticsearch-config"
JVM_OPTIONS_DIR="${CONFIG_DIR}/jvm.options.d"
DATA_DIR="${RUNTIME_DIR}/elasticsearch-data"
LOG_DIR="${RUNTIME_DIR}/elasticsearch-logs"
SNAPSHOT_DIR="${RUNTIME_DIR}/elasticsearch-snapshots"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "unsupported Studio architecture: $ARCH (expected arm64)" >&2
  exit 2
fi

mkdir -p "$DOWNLOAD_DIR" "$CONFIG_DIR" "$JVM_OPTIONS_DIR" "$DATA_DIR" "$LOG_DIR" "$SNAPSHOT_DIR"

ARCHIVE_PATH="${DOWNLOAD_DIR}/${ELASTIC_ARCHIVE}"
SHA_PATH="${DOWNLOAD_DIR}/${ELASTIC_ARCHIVE}.sha512"

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  curl -fsSL "$ELASTIC_URL" -o "$ARCHIVE_PATH"
fi
curl -fsSL "$ELASTIC_SHA_URL" -o "$SHA_PATH"
(cd "$DOWNLOAD_DIR" && shasum -a 512 -c "$(basename "$SHA_PATH")")

if [[ ! -d "$INSTALL_DIR" ]]; then
  tar -xzf "$ARCHIVE_PATH" -C "$RUNTIME_DIR"
fi
ln -sfn "$INSTALL_DIR" "$CURRENT_LINK"
rsync -a --ignore-existing "${INSTALL_DIR}/config/" "$CONFIG_DIR/"

cat > "${CONFIG_DIR}/elasticsearch.yml" <<EOF
cluster.name: memory-main
node.name: studio-memory-main
network.host: 127.0.0.1
http.host: 127.0.0.1
transport.host: 127.0.0.1
discovery.type: single-node
xpack.security.enabled: false
xpack.security.autoconfiguration.enabled: false
path.data: ${DATA_DIR}
path.logs: ${LOG_DIR}
path.repo: ["${SNAPSHOT_DIR}"]
EOF

cat > "${JVM_OPTIONS_DIR}/memory-main.options" <<'EOF'
-Xms2g
-Xmx2g
EOF

python3 - <<PY
import json
print(json.dumps({
    "ok": True,
    "arch": "${ARCH}",
    "elastic_version": "${ELASTIC_VERSION}",
    "artifact_url": "${ELASTIC_URL}",
    "sha512_url": "${ELASTIC_SHA_URL}",
    "install_dir": "${INSTALL_DIR}",
    "config_dir": "${CONFIG_DIR}",
    "data_dir": "${DATA_DIR}",
    "log_dir": "${LOG_DIR}",
    "snapshot_dir": "${SNAPSHOT_DIR}",
}, indent=2))
PY
