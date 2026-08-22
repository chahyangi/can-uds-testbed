#!/usr/bin/env bash
set -euo pipefail

GALLIA_BIN="${GALLIA_BIN:-$(command -v gallia || true)}"
if [ -z "$GALLIA_BIN" ] && [ -x "$HOME/.local/bin/gallia" ]; then
  GALLIA_BIN="$HOME/.local/bin/gallia"
fi
if [ -z "$GALLIA_BIN" ]; then
  echo "gallia not found; run scripts/bootstrap_ubuntu.sh" >&2
  exit 1
fi
CAN_INTERFACE="${CAN_INTERFACE:-vcan0}"
ECU_TX_ID="${ECU_TX_ID:-0x7e8}"
ECU_RX_ID="${ECU_RX_ID:-0x7e0}"
exec "$GALLIA_BIN" script vecu rng \
  "isotp://$CAN_INTERFACE?tx_id=$ECU_TX_ID&rx_id=$ECU_RX_ID&is_fd=false" \
  --seed "${GALLIA_SEED:-20260822}"
