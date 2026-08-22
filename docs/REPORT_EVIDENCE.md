# Report evidence guide

The three open shells can be used directly as report screenshots. Arrange them
so the command, timestamp and result are visible:

1. **Virtual ECU** — `scripts/run_gallia_vecu.sh`; capture the generated service
   table and the running server.
2. **Tester** — `gallia primitive uds pdu ...`; capture a positive response,
   negative response (NRC), and a stateful request sequence.
3. **Logger** — `candump -L vcan0`; capture matching 0x7E0 requests and 0x7E8
   responses.

Use `make gallia-test` for repeatable evidence. It writes `vecu.log`,
`positive.log`, `negative.log`, `stateful.log`, and `candump.log` below
`artifacts/gallia-vecu/<timestamp>/`. Screenshots explain the process; the raw
logs provide reproducible evidence and allow exact frame comparison.

Expected frames:

```text
7E0#021001   -> default-session request
7E8#025001   -> positive response
7E0#029900   -> unsupported service request
7E8#037F9911 -> NRC 0x11 (serviceNotSupported)
7E0#023E00   -> TesterPresent request
7E8#027E00   -> TesterPresent response
```

For an open-source C ECU implementation, run `make iso14229-test`. The test
saves an RDBI positive response (`62 F1 90 00 00`) and an unsupported-DID NRC
(`7F 22 31`) below `artifacts/iso14229/<timestamp>/`.

For the container boundary, build with `make docker-build` and run
`make docker-test`. The Dockerized Gallia vECU and the host Gallia tester use a
dedicated `vcan_docker` interface and save matching frames below
`artifacts/docker-gallia/<timestamp>/`.
