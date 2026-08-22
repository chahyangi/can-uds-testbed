#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT_DIR" submodule update --init --recursive
fi
if [ ! -f "$ROOT_DIR/third_party/iso14229/examples/linux_server/Makefile" ]; then
  echo "iso14229 source missing; clone the repository or initialize the submodule" >&2
  exit 1
fi
make -C "$ROOT_DIR/third_party/iso14229/examples/linux_server" clean all
make -C "$ROOT_DIR/third_party/iso14229/examples/linux_rdbi_wdbi" clean all
echo "[PASS] iso14229 Linux ECU examples built"
