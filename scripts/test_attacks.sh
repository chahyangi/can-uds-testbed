#!/usr/bin/env bash
# Runs both attack demos against stateful_ecu.py and saves evidence logs.
# Needs vcan0 (./setup_vcan.sh) and the can-isotp Python module; not part of
# the CI unit-test job, which only exercises the socket-free pure functions.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ARTIFACT_DIR:-$ROOT_DIR/artifacts/attacks/$STAMP}"
mkdir -p "$OUT_DIR"
CAN_INTERFACE="${CAN_INTERFACE:-vcan0}"
ip link show "$CAN_INTERFACE" >/dev/null

cleanup() {
  kill "${ECU_PID:-}" 2>/dev/null || true
  wait "${ECU_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

CAN_INTERFACE="$CAN_INTERFACE" "$ROOT_DIR/scripts/run_stateful_ecu.sh" >"$OUT_DIR/ecu.log" 2>&1 &
ECU_PID=$!
sleep 1

echo "[*] running 0x22 overload attack"
python3 "$ROOT_DIR/attacks/overload_0x22.py" \
  --interface "$CAN_INTERFACE" --sweep-ms 1,5 --duration 1 \
  >"$OUT_DIR/overload_0x22.log" 2>&1
grep -q "interval(ms)" "$OUT_DIR/overload_0x22.log"

echo "[*] running session denial attack"
python3 "$ROOT_DIR/attacks/session_denial.py" \
  --interface "$CAN_INTERFACE" --duration 3 --keepalive-interval 1 \
  --probe --probe-interval 0.5 \
  >"$OUT_DIR/session_denial.log" 2>&1
grep -q "attacker\] 0x10 -> granted" "$OUT_DIR/session_denial.log"
grep -q "legit probe\] .* -> denied(nrc=0x22)" "$OUT_DIR/session_denial.log"

echo "[PASS] attack demos completed"
echo "[INFO] evidence: $OUT_DIR"
