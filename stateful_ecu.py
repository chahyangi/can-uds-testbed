"""UDS ECU with a real single-active-session lock, for attack demos.

`fake_ecu.py` answers every request the same way regardless of who sent it,
so there is nothing for a session-hijack attack to actually seize. This ECU
adds the ISO 14229-1 rule the paper's V-B attack targets: exactly one
non-default diagnostic session may be active at a time, and TesterPresent
(0x3E) from the session holder keeps it alive past the S3 timeout.

SocketCAN's isotp module addresses peers by CAN ID pair, not by an
in-payload source byte, so two distinct tester identities on the same bus
need two distinct ID pairs. This ECU binds one isotp socket per identity
("legit" and "attacker" by default) and serializes both through one shared
SessionState so a session opened on one socket blocks the other.
"""

from __future__ import annotations

import argparse
import threading
import time


class SessionState:
    """Pure, socket-free session lock so it can be unit tested directly."""

    def __init__(self, s3_timeout: float = 5.0) -> None:
        self.s3_timeout = s3_timeout
        self.session = 0x01
        self.holder: str | None = None
        self.last_seen = 0.0

    def _release_if_expired(self, now: float) -> None:
        if self.holder is not None and (now - self.last_seen) > self.s3_timeout:
            self.session = 0x01
            self.holder = None

    def handle(self, data: bytes, requester: str, now: float) -> bytes:
        if not data:
            raise ValueError("empty UDS request")
        sid = data[0]
        self._release_if_expired(now)
        if sid == 0x10:
            if len(data) < 2:
                return bytes([0x7F, sid, 0x13])
            requested = data[1]
            if self.holder is not None and self.holder != requester:
                return bytes([0x7F, sid, 0x22])
            if requested == 0x01:
                self.session, self.holder = 0x01, None
            else:
                self.session, self.holder, self.last_seen = requested, requester, now
            return bytes([0x50, requested, 0x00, 0x32, 0x01, 0xF4])
        if sid == 0x3E:
            if self.holder == requester:
                self.last_seen = now
            return bytes([0x7E, data[1] if len(data) > 1 else 0x00])
        if sid == 0x22:
            if len(data) < 3:
                return bytes([0x7F, sid, 0x13])
            return bytes([0x62]) + data[1:3] + b"\x01\x02\x03\x04"
        if sid == 0x11:
            if len(data) < 2:
                return bytes([0x7F, sid, 0x13])
            return bytes([0x51, data[1]])
        return bytes([0x7F, sid, 0x11])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", default="vcan0")
    parser.add_argument("--legit-rx-id", type=lambda x: int(x, 0), default=0x7E0)
    parser.add_argument("--legit-tx-id", type=lambda x: int(x, 0), default=0x7E8)
    parser.add_argument("--attacker-rx-id", type=lambda x: int(x, 0), default=0x7E1)
    parser.add_argument("--attacker-tx-id", type=lambda x: int(x, 0), default=0x7E9)
    parser.add_argument("--s3-timeout", type=float, default=5.0)
    return parser.parse_args()


def _serve(interface: str, rx_id: int, tx_id: int, label: str, state: SessionState, lock: threading.Lock) -> None:
    import isotp

    sock = isotp.socket()
    sock.set_fc_opts(stmin=5, bs=10)
    sock.bind(interface, isotp.Address(rxid=rx_id, txid=tx_id))
    print(f"[{label}] listening on {interface} (rx=0x{rx_id:03X}, tx=0x{tx_id:03X})", flush=True)
    while True:
        data = sock.recv()
        if not data:
            continue
        with lock:
            response = state.handle(data, label, time.monotonic())
        print(f"[{label}] REQ : {data.hex(' ')}", flush=True)
        print(f"[{label}] RESP: {response.hex(' ')}", flush=True)
        sock.send(response)


def main() -> None:
    args = parse_args()
    state = SessionState(s3_timeout=args.s3_timeout)
    lock = threading.Lock()
    legit = threading.Thread(
        target=_serve,
        args=(args.interface, args.legit_rx_id, args.legit_tx_id, "legit", state, lock),
        daemon=True,
    )
    attacker = threading.Thread(
        target=_serve,
        args=(args.interface, args.attacker_rx_id, args.attacker_tx_id, "attacker", state, lock),
        daemon=True,
    )
    legit.start()
    attacker.start()
    legit.join()
    attacker.join()


if __name__ == "__main__":
    main()
