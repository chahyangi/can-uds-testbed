"""State/coverage-aware fuzzer for udsoncan's ReadDataByIdentifier response parser.

Deeper than fuzzers/state_fuzzer.py's --target udsoncan (which only exercises
Response.from_payload's top-level framing). This targets the actual per-DID
parsing loop in ReadDataByIdentifier.interpret_response, which manually walks
response.data with struct.unpack and codec-defined lengths -- exactly the
kind of hand-rolled offset arithmetic that tends to hide off-by-one bugs.

Oracle: interpret_response's docstring says it only raises ValueError,
ConfigError, or InvalidResponseException for bad input. Anything else
(IndexError, struct.error, KeyError, ...) escaping the parsing loop is a
genuine bug, not documented behavior.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.home() / "can-uds-testbed"))
sys.path.insert(0, str(Path.home() / "can-uds-testbed" / "fuzzers"))

from state_fuzzer import LineCoverage  # noqa: E402

from udsoncan import Response, AsciiCodec  # noqa: E402
from udsoncan.services import ReadDataByIdentifier  # noqa: E402
from udsoncan.exceptions import InvalidResponseException, ConfigError  # noqa: E402

DIDCONFIG = {
    0x1234: ">H",       # 2-byte unsigned short
    0x5678: ">I",       # 4-byte unsigned int
    0xF190: AsciiCodec(17),  # 17-byte ASCII (VIN-like)
    0x0001: ">B",       # 1 byte
}
DIDLIST = list(DIDCONFIG.keys())
EXPECTED_EXC = (ValueError, ConfigError, InvalidResponseException)


def random_data(rng: random.Random) -> bytes:
    out = bytearray()
    for _ in range(rng.randrange(0, 4)):
        did = rng.choice(DIDLIST + [0x0000, 0xDEAD, 0xBEEF])
        out += did.to_bytes(2, "big")
        out += bytes(rng.randrange(256) for _ in range(rng.randrange(0, 20)))
    if rng.random() < 0.3:
        out += bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))
    return bytes(out)


def mutate(data: bytes, rng: random.Random) -> bytes:
    if not data or rng.random() < 0.3:
        return random_data(rng)
    data = bytearray(data)
    choice = rng.random()
    if choice < 0.4:
        i = rng.randrange(len(data))
        data[i] ^= 1 << rng.randrange(8)
    elif choice < 0.6:
        data.append(rng.randrange(256))
    elif choice < 0.8 and len(data) > 1:
        del data[rng.randrange(len(data))]
    else:
        return random_data(rng)
    return bytes(data)


def make_response(data: bytes) -> Response:
    resp = Response()
    resp.positive = True
    resp.service = ReadDataByIdentifier
    resp.data = data
    return resp


def main() -> None:
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    rng = random.Random(2)
    target_file = ReadDataByIdentifier.interpret_response.__func__.__code__.co_filename
    coverage = LineCoverage(target_file)

    corpus = [random_data(rng) for _ in range(16)]
    seen_sigs: set = set()
    findings: list[str] = []
    iterations = 0

    deadline = time.monotonic() + duration
    with coverage:
        while time.monotonic() < deadline:
            iterations += 1
            data = mutate(rng.choice(corpus), rng)
            resp = make_response(data)
            before_cov = len(coverage.seen)
            try:
                ReadDataByIdentifier.interpret_response(resp, DIDLIST, DIDCONFIG)
                sig = ("OK", tuple(sorted(resp.service_data.values.keys())) if resp.service_data else ())
            except EXPECTED_EXC as e:
                sig = ("EXPECTED", type(e).__name__)
            except Exception as e:  # noqa: BLE001 - this is the crash oracle
                findings.append(f"CRASH {type(e).__name__}({e!r}) for data={data.hex()}")
                sig = ("CRASH", type(e).__name__)

            new_cov = len(coverage.seen) > before_cov
            new_sig = sig not in seen_sigs
            seen_sigs.add(sig)
            if new_cov or new_sig:
                corpus.append(data)

    print(f"iterations={iterations} corpus={len(corpus)} coverage_lines={len(coverage.seen)} "
          f"unique_signatures={len(seen_sigs)} findings={len(set(findings))}")
    for f in sorted(set(findings))[:20]:
        print(" -", f)


if __name__ == "__main__":
    main()
