#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAN_INTERFACE="${CAN_INTERFACE:-vcan_docker}"
IMAGE="${GALLIA_IMAGE:-can-uds-gallia:2.1.1}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ARTIFACTS_DIR:-$ROOT_DIR/artifacts/docker-gallia}/$STAMP"
mkdir -p "$OUT_DIR"

GALLIA_BIN="${GALLIA_BIN:-$(command -v gallia || true)}"
if [ -z "$GALLIA_BIN" ] && [ -x "$HOME/.local/bin/gallia" ]; then
  GALLIA_BIN="$HOME/.local/bin/gallia"
fi
[ -n "$GALLIA_BIN" ] || { echo "gallia not found" >&2; exit 1; }

if ! ip link show "$CAN_INTERFACE" >/dev/null 2>&1; then
  sudo ip link add dev "$CAN_INTERFACE" type vcan
fi
sudo ip link set "$CAN_INTERFACE" up

container_name="can-uds-gallia-$STAMP"
dump_pid=""
cleanup() {
  [ -z "$dump_pid" ] || kill "$dump_pid" 2>/dev/null || true
  sudo docker rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

candump -L "$CAN_INTERFACE" >"$OUT_DIR/candump.log" 2>&1 &
dump_pid=$!
sudo docker run -d --rm \
  --name "$container_name" \
  --network host \
  -e CAN_INTERFACE="$CAN_INTERFACE" \
  -e GALLIA_SEED=20260822 \
  "$IMAGE" >"$OUT_DIR/container-id.log"
sleep 2

TARGET="isotp://$CAN_INTERFACE?tx_id=0x7e0&rx_id=0x7e8&is_fd=false"
"$GALLIA_BIN" primitive uds pdu \
  --target "$TARGET" --no-ping --no-tester-present --no-dumpcap 1001 \
  >"$OUT_DIR/tester.log" 2>&1
sudo docker logs "$container_name" >"$OUT_DIR/vecu.log" 2>&1
sleep 1

grep -q "DiagnosticSessionControlResponse" "$OUT_DIR/tester.log"
grep -qi "7E0#021001" "$OUT_DIR/candump.log"
grep -qi "7E8#025001" "$OUT_DIR/candump.log"
echo "[PASS] Dockerized Gallia ECU answered host Gallia tester"
echo "Evidence: $OUT_DIR"
