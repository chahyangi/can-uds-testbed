#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAN_INTERFACE="${CAN_INTERFACE:-vcan0}"
exec python3 "$ROOT_DIR/stateful_ecu.py" \
  --interface "$CAN_INTERFACE" \
  --legit-rx-id "${LEGIT_RX_ID:-0x7e0}" \
  --legit-tx-id "${LEGIT_TX_ID:-0x7e8}" \
  --attacker-rx-id "${ATTACKER_RX_ID:-0x7e1}" \
  --attacker-tx-id "${ATTACKER_TX_ID:-0x7e9}"
