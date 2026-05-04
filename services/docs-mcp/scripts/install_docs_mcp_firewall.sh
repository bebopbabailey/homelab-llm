#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "install_docs_mcp_firewall.sh must run as root" >&2
  exit 2
fi

LAN_IP="${DOCS_MCP_LAN_IP:-192.168.1.72}"
ALLOW_IP="${DOCS_MCP_ALLOWED_SOURCE_IP:-192.168.1.71}"
PORT="${DOCS_MCP_PORT:-8013}"
ANCHOR_NAME="com.bebop.docs-mcp-main"
ANCHOR_FILE="/etc/pf.anchors/${ANCHOR_NAME}"
PF_CONF="/etc/pf.conf"

if ! grep -q "anchor \"${ANCHOR_NAME}\"" "$PF_CONF"; then
  cat >> "$PF_CONF" <<EOF

anchor "${ANCHOR_NAME}"
load anchor "${ANCHOR_NAME}" from "${ANCHOR_FILE}"
EOF
fi

cat > "$ANCHOR_FILE" <<EOF
pass in quick proto tcp from ${LAN_IP} to ${LAN_IP} port ${PORT}
pass in quick proto tcp from ${ALLOW_IP} to ${LAN_IP} port ${PORT}
block in quick proto tcp from any to ${LAN_IP} port ${PORT}
EOF

pfctl -E >/dev/null 2>&1 || true
pfctl -f "$PF_CONF"
pfctl -a "$ANCHOR_NAME" -f "$ANCHOR_FILE"
pfctl -a "$ANCHOR_NAME" -s rules
