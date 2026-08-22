#!/usr/bin/env bash
set -euo pipefail

QEMU_BIN="$(command -v qemu-system-x86_64 || true)"
if [ -z "$QEMU_BIN" ]; then
  echo "qemu-system-x86_64 not found; install qemu-system-x86" >&2
  exit 1
fi
"$QEMU_BIN" --version | head -n 1

set +e
timeout 2s "$QEMU_BIN" \
  -accel tcg \
  -machine pc \
  -m 128M \
  -nodefaults \
  -display none \
  -monitor none \
  -serial none
status=$?
set -e

if [ "$status" -ne 124 ]; then
  echo "QEMU smoke test exited unexpectedly with status $status" >&2
  exit 1
fi
echo "[PASS] QEMU TCG guest machine stayed running for the smoke-test window"
