#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${MEMORY_ELASTIC_RUNTIME_DIR:-$ROOT_DIR/runtime}"
KIBANA_VERSION="${MEMORY_KIBANA_VERSION:-${MEMORY_ELASTIC_VERSION:-9.3.3}}"
KIBANA_ARCHIVE="kibana-${KIBANA_VERSION}-darwin-aarch64.tar.gz"
KIBANA_BASE_URL="${MEMORY_KIBANA_ARTIFACT_BASE:-https://artifacts.elastic.co/downloads/kibana}"
KIBANA_URL="${KIBANA_BASE_URL}/${KIBANA_ARCHIVE}"
KIBANA_SHA_URL="${KIBANA_URL}.sha512"
DOWNLOAD_DIR="${RUNTIME_DIR}/downloads"
INSTALL_DIR="${RUNTIME_DIR}/kibana-${KIBANA_VERSION}"
CURRENT_LINK="${RUNTIME_DIR}/kibana-current"
CONFIG_DIR="${RUNTIME_DIR}/kibana-config"
DATA_DIR="${RUNTIME_DIR}/kibana-data"

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
  echo "unsupported Studio architecture: $ARCH (expected arm64)" >&2
  exit 2
fi

mkdir -p "$DOWNLOAD_DIR" "$CONFIG_DIR" "$DATA_DIR"

ARCHIVE_PATH="${DOWNLOAD_DIR}/${KIBANA_ARCHIVE}"
SHA_PATH="${DOWNLOAD_DIR}/${KIBANA_ARCHIVE}.sha512"

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  curl -fsSL "$KIBANA_URL" -o "$ARCHIVE_PATH"
fi
curl -fsSL "$KIBANA_SHA_URL" -o "$SHA_PATH"
(cd "$DOWNLOAD_DIR" && shasum -a 512 -c "$(basename "$SHA_PATH")")

if [[ ! -d "$INSTALL_DIR" ]]; then
  tar -xzf "$ARCHIVE_PATH" -C "$RUNTIME_DIR"
fi
ln -sfn "$INSTALL_DIR" "$CURRENT_LINK"
rsync -a --ignore-existing "${INSTALL_DIR}/config/" "$CONFIG_DIR/"
xattr -d -r com.apple.quarantine "$INSTALL_DIR" >/dev/null 2>&1 || true

cat > "${CONFIG_DIR}/kibana.yml" <<EOF
server.host: "127.0.0.1"
server.port: 5601
server.shutdownTimeout: "5s"
elasticsearch.hosts: ["http://127.0.0.1:9200"]
path.data: ${DATA_DIR}
EOF

python3 - <<PY
import json
print(json.dumps({
    "ok": True,
    "arch": "${ARCH}",
    "kibana_version": "${KIBANA_VERSION}",
    "artifact_url": "${KIBANA_URL}",
    "sha512_url": "${KIBANA_SHA_URL}",
    "install_dir": "${INSTALL_DIR}",
    "config_dir": "${CONFIG_DIR}",
    "data_dir": "${DATA_DIR}",
}, indent=2))
PY
