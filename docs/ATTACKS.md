# Attack labs: 0x22 overload and session denial

Reproduces two of the three UDS/ISO-TP attacks from *Exploiting Diagnostic
Protocol Vulnerabilities on Embedded Networks in Commercial Vehicles*
(VehicleSec 2024, Chatterjee, Green, Daily) against this testbed's virtual
ECUs. The paper's third attack, Diagnostics Jam (ISO 15765-2 Flow Control
Wait/CTS abuse), is out of scope here.

## V-A. 0x22 ReadDataByIdentifier overload — `attacks/overload_0x22.py`

**Paper's method**: flood the target with 0x22 requests at the lowest J1939
priority (to rule out CAN arbitration effects) at 0.1-0.6ms intervals, and
watch the ECU's *periodic broadcast* traffic drop or stop.

**This testbed's adaptation**: the reference ECUs (`fake_ecu.py`,
`stateful_ecu.py`) don't emit periodic broadcast traffic — they only answer
requests — so there's no background signal to watch collapse. Instead the
script floods 0x22 at each interval in a sweep and measures the 0x22
response rate and round-trip latency directly on the request/response
channel. A falling response rate or growing latency as the interval
shrinks is the same "diagnostic processing crowds out other work" effect,
observed from the other side of the exchange.

```bash
python3 attacks/overload_0x22.py --interface vcan0 --sweep-ms 0.1,0.2,0.5,1,5 --duration 2
```

Works against either `fake_ecu.py` or `stateful_ecu.py` — this attack
doesn't depend on session state.

**Paper's mitigation**: rate-limit high-frequency 0x22 requests. The paper
notes this as an observed-cause hypothesis (ISR-level processing), not a
verified defense mechanism.

## V-B. Session denial — `attacks/session_denial.py`

**Paper's method**: spoof a source address, send 0x10 Diagnostic Session
Control to seize a session, keep it alive with periodic 0x3E Tester
Present, and show a legitimate diagnostic tool can no longer connect.

**This testbed's adaptation**: SocketCAN's `isotp` module addresses peers
by CAN ID pair, not an in-payload source byte, so there's no single socket
that can receive from "any sender" and distinguish them after the fact.
Two tester identities are modeled as two distinct ID pairs (default: legit
tester 0x7E0/0x7E8, attacker 0x7E1/0x7E9), both served by
`stateful_ecu.py`, which is the part of this lab that had to be built —
`fake_ecu.py` has no session state, so every request succeeds regardless
of sender and there's nothing to seize. `stateful_ecu.py` adds the ISO
14229-1 rule the attack targets: exactly one non-default session may be
active, and only its holder's 0x3E frames refresh the S3 timeout; a
different identity's 0x10 is answered with NRC 0x22
(conditionsNotCorrect) until the holder releases it or the timeout lapses.

Terminal 1 — stateful ECU:

```bash
./scripts/run_stateful_ecu.sh
```

Terminal 2 — attacker, with a live probe from the legit identity:

```bash
python3 attacks/session_denial.py --interface vcan0 --duration 20 --probe
```

Expect the attacker's first `0x10 -> granted`, then repeated
`[legit probe] ... -> denied(nrc=0x22)` lines until the attack ends and the
lock is released or times out.

**Paper's mitigation**: session request queueing plus source-address /
tester authentication before session establishment.

## Automated evidence

```bash
./setup_vcan.sh
make attack-test
```

Runs both scripts against `stateful_ecu.py` on a short timer and saves
`ecu.log`, `overload_0x22.log`, `session_denial.log` under
`artifacts/attacks/<timestamp>/`, following the same evidence convention
as `make gallia-test` (see [REPORT_EVIDENCE.md](REPORT_EVIDENCE.md)).
