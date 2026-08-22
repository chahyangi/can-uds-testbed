"""Minimal deterministic UDS ECU for a SocketCAN ISO-TP socket."""

from __future__ import annotations

import argparse


def handle_request(data: bytes) -> bytes:
    """Return a small, deterministic UDS response for *data*."""
    if not data:
        raise ValueError("empty UDS request")
    sid = data[0]
    if sid == 0x10:
        if len(data) < 2:
            return bytes([0x7F, sid, 0x13])
        return bytes([0x50, data[1], 0x00, 0x32, 0x01, 0xF4])
    if sid == 0x3E:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", default="vcan0")
    parser.add_argument("--rx-id", type=lambda x: int(x, 0), default=0x7E0)
    parser.add_argument("--tx-id", type=lambda x: int(x, 0), default=0x7E8)
    return parser.parse_args()


def main() -> None:
    import isotp

    args = parse_args()
    sock = isotp.socket()
    sock.set_fc_opts(stmin=5, bs=10)
    sock.bind(args.interface, isotp.Address(rxid=args.rx_id, txid=args.tx_id))
    print(
        f"Fake ECU listening on {args.interface} "
        f"(rx=0x{args.rx_id:03X}, tx=0x{args.tx_id:03X})",
        flush=True,
    )
    while True:
        data = sock.recv()
        if not data:
            continue
        response = handle_request(data)
        print(f"REQ : {data.hex(' ')}", flush=True)
        print(f"RESP: {response.hex(' ')}", flush=True)
        sock.send(response)


if __name__ == "__main__":
    main()
