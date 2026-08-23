#!/usr/bin/env bash
set -euo pipefail

mode="${1:-vecu}"
interface="${CAN_INTERFACE:-vcan0}"

wait_for_interface() {
  for _ in $(seq 1 20); do
    if ip link show "$interface" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "CAN interface $interface did not become available" >&2
  return 1
}

case "$mode" in
  bus)
    if ! ip link show "$interface" >/dev/null 2>&1; then
      ip link add dev "$interface" type vcan
    fi
    ip link set "$interface" up
    ip -details link show "$interface"
    echo "[+] $interface created inside the container network namespace"
    exec sleep infinity
    ;;

  vecu)
    wait_for_interface
    exec /usr/local/bin/run-gallia-vecu
    ;;

  test)
    wait_for_interface
    evidence_dir="/tmp/can-uds-evidence"
    mkdir -p "$evidence_dir"
    dump_pid=""
    cleanup() {
      if [ -n "$dump_pid" ]; then
        kill "$dump_pid" 2>/dev/null || true
        wait "$dump_pid" 2>/dev/null || true
      fi
    }
    trap cleanup EXIT

    candump -L "$interface" >"$evidence_dir/candump.log" 2>&1 &
    dump_pid=$!
    sleep 2

    target="isotp://$interface?tx_id=0x7e0&rx_id=0x7e8&is_fd=false"
    gallia primitive uds pdu \
      --target "$target" \
      --no-ping --no-tester-present --no-dumpcap \
      1001 >"$evidence_dir/tester.log" 2>&1
    sleep 1

    grep -q "DiagnosticSessionControlResponse" "$evidence_dir/tester.log"
    grep -qi "7E0#021001" "$evidence_dir/candump.log"
    grep -qi "7E8#025001" "$evidence_dir/candump.log"
    cat "$evidence_dir/tester.log"
    echo "[PASS] portable Docker Tester reached the Gallia ECU over $interface"
    ;;

  *)
    exec "$@"
    ;;
esac
