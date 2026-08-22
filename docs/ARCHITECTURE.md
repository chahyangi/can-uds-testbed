# Testbed architecture

```text
Gallia Tester                 Linux SocketCAN                  Virtual ECU
tx=0x7E0, rx=0x7E8   <->   vcan0 + kernel ISO-TP   <->   tx=0x7E8, rx=0x7E0
                                   |
                                candump
```

The IDs are described from the process that owns the socket. Therefore the
tester and ECU use opposite `tx_id`/`rx_id` values.

## ECU choices

- `Gallia script vecu rng`: quickest reproducible virtual ECU; useful for UDS
  state, NRC, scanner and fuzzing experiments.
- `fake_ecu.py`: small readable reference ECU with deterministic responses.
- `third_party/iso14229`: embedded-oriented C implementation, pinned as a Git
  submodule. This is the preferred next step when implementation behavior and
  source-level instrumentation matter.

## QEMU boundary

VirtualBox currently provides the Ubuntu x86_64 host for SocketCAN experiments.
QEMU is installed and smoke-tested as a shared skill, but it is not in the CAN
request/response path yet. On a Windows x86_64 PC, an amd64 Ubuntu image is
correct. ARM64 is needed only when an ARM board or firmware is deliberately
emulated.
