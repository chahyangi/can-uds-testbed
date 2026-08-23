#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ "$(uname -s)" != "Linux" ]; then
  echo "This SocketCAN testbed requires a Linux Docker host." >&2
  echo "Docker Desktop on Windows/macOS does not guarantee vcan or CAN_ISOTP kernel support." >&2
  exit 1
fi

command -v docker >/dev/null 2>&1 || {
  echo "docker not found; install Docker Engine and the Compose plugin first" >&2
  exit 1
}

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
fi

"${DOCKER[@]}" compose version >/dev/null 2>&1 || {
  echo "docker compose not found; install the Docker Compose plugin first" >&2
  exit 1
}

echo "[*] loading the Linux host's SocketCAN kernel modules"
sudo modprobe vcan
sudo modprobe can-isotp

cleanup() {
  "${DOCKER[@]}" compose --profile test down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[*] building the self-contained Docker testbed"
"${DOCKER[@]}" compose --profile test up \
  --build \
  --abort-on-container-exit \
  --exit-code-from tester
