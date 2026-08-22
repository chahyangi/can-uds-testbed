#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ARTIFACTS_DIR:-$ROOT_DIR/artifacts/iso14229}/$STAMP"
mkdir -p "$OUT_DIR"

GALLIA_BIN="${GALLIA_BIN:-$(command -v gallia || true)}"
if [ -z "$GALLIA_BIN" ] && [ -x "$HOME/.local/bin/gallia" ]; then
  GALLIA_BIN="$HOME/.local/bin/gallia"
fi
if [ -z "$GALLIA_BIN" ]; then
  echo "gallia not found" >&2
  exit 1
fi

ip link show vcan0 >/dev/null
SERVER="$ROOT_DIR/third_party/iso14229/examples/linux_rdbi_wdbi/server"
TARGET="isotp://vcan0?tx_id=0x7e0&rx_id=0x7e8&is_fd=false"
COMMON=(--target "$TARGET" --no-ping --no-tester-present --no-dumpcap)

server_pid=""
dump_pid=""
cleanup() {
  [ -z "$server_pid" ] || kill "$server_pid" 2>/dev/null || true
  [ -z "$dump_pid" ] || kill "$dump_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$ROOT_DIR/scripts/build_iso14229.sh" >"$OUT_DIR/build.log" 2>&1
candump -L vcan0 >"$OUT_DIR/candump.log" 2>&1 &
dump_pid=$!
"$SERVER" >"$OUT_DIR/ecu.log" 2>&1 &
server_pid=$!
sleep 1

"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 22f190 >"$OUT_DIR/rdbi.log" 2>&1
"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 22f199 >"$OUT_DIR/out-of-range.log" 2>&1
sleep 1

grep -q "ReadDataByIdentifierResponse" "$OUT_DIR/rdbi.log"
grep -q "requestOutOfRange" "$OUT_DIR/out-of-range.log"
grep -qi "7E0#0322F190" "$OUT_DIR/candump.log"
grep -qi "7E8#0562F1900000" "$OUT_DIR/candump.log"
grep -qi "7E8#037F2231" "$OUT_DIR/candump.log"

echo "[PASS] iso14229 ECU answered Gallia RDBI and NRC tests"
echo "Evidence: $OUT_DIR"
