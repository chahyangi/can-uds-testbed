#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ARTIFACT_DIR:-$ROOT_DIR/artifacts/gallia-vecu/$STAMP}"
mkdir -p "$OUT_DIR"
GALLIA_BIN="${GALLIA_BIN:-$(command -v gallia || true)}"
if [ -z "$GALLIA_BIN" ] && [ -x "$HOME/.local/bin/gallia" ]; then
  GALLIA_BIN="$HOME/.local/bin/gallia"
fi
test -n "$GALLIA_BIN"
CAN_INTERFACE="${CAN_INTERFACE:-vcan0}"
ip link show "$CAN_INTERFACE" >/dev/null
TARGET="isotp://$CAN_INTERFACE?tx_id=0x7e0&rx_id=0x7e8&is_fd=false"
COMMON=(--target "$TARGET" --no-ping --no-tester-present --no-dumpcap)

cleanup() {
  kill "${ECU_PID:-}" "${DUMP_PID:-}" 2>/dev/null || true
  wait "${ECU_PID:-}" "${DUMP_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT
stdbuf -oL candump -L "$CAN_INTERFACE" >"$OUT_DIR/candump.log" 2>&1 &
DUMP_PID=$!
"$ROOT_DIR/scripts/run_gallia_vecu.sh" >"$OUT_DIR/vecu.log" 2>&1 &
ECU_PID=$!
sleep 1
"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 1001 >"$OUT_DIR/positive.log" 2>&1
"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 9900 >"$OUT_DIR/negative.log" 2>&1
"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 1047 >"$OUT_DIR/stateful.log" 2>&1
"$GALLIA_BIN" primitive uds pdu "${COMMON[@]}" 3e00 >>"$OUT_DIR/stateful.log" 2>&1
sleep 1
grep -q "DiagnosticSessionControlResponse" "$OUT_DIR/positive.log"
grep -q "serviceNotSupported" "$OUT_DIR/negative.log"
grep -q "TesterPresentResponse" "$OUT_DIR/stateful.log"
grep -qi "7E0#021001" "$OUT_DIR/candump.log"
grep -qi "7E8#025001" "$OUT_DIR/candump.log"
grep -qi "7E8#037F9911" "$OUT_DIR/candump.log"
grep -qi "7E8#027E00" "$OUT_DIR/candump.log"
echo "[PASS] Gallia virtual ECU request/response and NRC checks"
echo "[INFO] evidence: $OUT_DIR"
