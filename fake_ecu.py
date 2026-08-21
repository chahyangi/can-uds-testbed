import isotp

# vcan0에서 요청 수신(0x7E0) → 응답 송신(0x7E8)
s = isotp.socket()
s.set_fc_opts(stmin=5, bs=10)
s.bind("vcan0", isotp.Address(rxid=0x7E0, txid=0x7E8))

print("Fake ECU listening on vcan0 (rx=0x7E0, tx=0x7E8)")

while True:
    data = s.recv()
    if not data:
        continue
    print("REQ :", data.hex())
    sid = data[0]

    if sid == 0x10:                       # Diagnostic Session Control
        resp = bytes([0x50, data[1], 0x00, 0x32, 0x01, 0xF4])
    elif sid == 0x3E:                     # Tester Present
        resp = bytes([0x7E, data[1] if len(data) > 1 else 0x00])
    elif sid == 0x22:                     # Read Data By Identifier
        resp = bytes([0x62]) + data[1:3] + b'\x01\x02\x03\x04'
    elif sid == 0x11:                     # ECU Reset
        resp = bytes([0x51, data[1]])
    else:                                 # Negative Response (serviceNotSupported)
        resp = bytes([0x7F, sid, 0x11])

    print("RESP:", resp.hex())
    s.send(resp)
