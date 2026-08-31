"""State-aware in-process fuzzer for UDS ECU handlers.

Combines three signals to decide whether a mutated input is "interesting"
enough to keep in the corpus, per the project's core technique (NRC,
response history, coverage):

  1. NRC / response signature — the response's first byte (0x7F for a
     negative response, or SID+0x40 for positive) plus the NRC code when
     negative.
  2. Response-history state — a short window of prior signatures, so the
     fuzzer notices *new transitions*, not just new individual responses.
  3. Code coverage — (filename, lineno) pairs actually executed inside the
     target module during the call, via sys.settrace. No external
     dependency (no `coverage` package, no vcan/network needed).

Oracles (bugs the fuzzer flags):
  - CRASH: the handler raises anything other than the one documented,
    input-validation ValueError("empty UDS request").
  - MALFORMED: a non-empty response whose first byte is neither 0x7F
    (negative response) nor (request_sid + 0x40) (positive response).
  - BAD_NRC_LEN: a negative response (0x7F ...) that isn't exactly 3 bytes
    (0x7F, sid, nrc).

Usage (against stateful_ecu.SessionState):
    python3 fuzzers/state_fuzzer.py --target stateful --duration 30
Usage (against fake_ecu.handle_request):
    python3 fuzzers/state_fuzzer.py --target fake --duration 30
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Coverage: minimal line-coverage tracer, no external deps.
# ---------------------------------------------------------------------------

class LineCoverage:
    def __init__(self, target_filename: str) -> None:
        self.target_filename = os.path.abspath(target_filename)
        self.seen: set[tuple[str, int]] = set()
        self._armed = False

    def _trace(self, frame, event, arg):
        if event == "line" and os.path.abspath(frame.f_code.co_filename) == self.target_filename:
            self.seen.add((frame.f_code.co_name, frame.f_lineno))
        return self._trace

    def __enter__(self):
        self._prev = sys.gettrace()
        sys.settrace(self._trace)
        self._armed = True
        return self

    def __exit__(self, *exc):
        sys.settrace(self._prev)
        self._armed = False


# ---------------------------------------------------------------------------
# Mutation-based random input generation for raw UDS request bytes.
# ---------------------------------------------------------------------------

KNOWN_SIDS = [0x10, 0x11, 0x22, 0x3E, 0x00, 0x27, 0x2E, 0xFF]
BOUNDARY_LENS = [0, 1, 2, 3, 4, 8]


def random_request(rng: random.Random) -> bytes:
    sid = rng.choice(KNOWN_SIDS)
    length = rng.choice(BOUNDARY_LENS)
    body = bytes(rng.randrange(256) for _ in range(max(0, length - 1)))
    return bytes([sid]) + body


def mutate(data: bytes, rng: random.Random) -> bytes:
    if not data:
        return random_request(rng)
    data = bytearray(data)
    choice = rng.random()
    if choice < 0.4 and data:
        i = rng.randrange(len(data))
        data[i] ^= 1 << rng.randrange(8)
    elif choice < 0.6:
        data.append(rng.randrange(256))
    elif choice < 0.8 and len(data) > 1:
        del data[rng.randrange(len(data))]
    else:
        data[0] = rng.choice(KNOWN_SIDS)
    return bytes(data)


REQUESTERS = ["legit", "attacker", "ghost", ""]
TIME_DELTAS = [0.0, 0.01, 1.0, 4.99, 5.0, 5.01, 30.0]


@dataclass
class Seed:
    data: bytes
    requester: str
    dt: float


@dataclass
class Stats:
    iterations: int = 0
    corpus_size: int = 0
    coverage_lines: int = 0
    unique_signatures: int = 0
    findings: list = field(default_factory=list)


def response_signature(sid: int, response: bytes) -> tuple:
    if not response:
        return ("EMPTY",)
    if response[0] == 0x7F:
        nrc = response[2] if len(response) > 2 else None
        return ("NRC", response[1] if len(response) > 1 else None, nrc)
    return ("POS", response[0])


def check_oracles(sid: int, data: bytes, response: bytes) -> list[str]:
    findings = []
    if response:
        if response[0] == 0x7F:
            if len(response) != 3:
                findings.append(f"BAD_NRC_LEN resp={response.hex()} for req={data.hex()}")
        elif response[0] != (sid + 0x40) & 0xFF:
            findings.append(
                f"MALFORMED resp[0]=0x{response[0]:02X} expected 0x{(sid+0x40)&0xFF:02X} "
                f"for req={data.hex()}"
            )
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["fake", "stateful", "udsoncan"], default="stateful")
    parser.add_argument("--duration", type=float, default=30.0, help="seconds to fuzz")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--repo", default=str(Path.home() / "can-uds-testbed"))
    parser.add_argument("--out", default=None, help="write JSON report here")
    args = parser.parse_args()

    sys.path.insert(0, args.repo)
    rng = random.Random(args.seed)

    if args.target == "fake":
        mod = importlib.import_module("fake_ecu")
        target_file = mod.__file__
    elif args.target == "stateful":
        mod = importlib.import_module("stateful_ecu")
        target_file = mod.__file__
    else:
        mod = importlib.import_module("udsoncan")
        target_file = mod.Response.from_payload.__func__.__code__.co_filename

    coverage = LineCoverage(target_file)
    corpus: list[Seed] = [Seed(random_request(rng), rng.choice(REQUESTERS), rng.choice(TIME_DELTAS)) for _ in range(16)]
    if args.target == "udsoncan":
        # Seed with well-formed positive (SID+0x40) and negative (0x7F, sid, nrc) response
        # shapes so the fuzzer starts past the "unknown service id" early-exit branch.
        for sid in KNOWN_SIDS:
            pos_id = (sid + 0x40) & 0xFF
            corpus.append(Seed(bytes([pos_id, 0x00, 0x00, 0x00]), "", 0.0))
            corpus.append(Seed(bytes([0x7F, sid, 0x11]), "", 0.0))
    seen_signatures: set[tuple] = set()
    seen_transitions: set[tuple] = set()
    last_sig = None
    findings: list[str] = []
    stats = Stats()

    state = mod.SessionState() if args.target == "stateful" else None
    now = 0.0

    deadline = time.monotonic() + args.duration
    with coverage:
        while time.monotonic() < deadline:
            stats.iterations += 1
            base = rng.choice(corpus)
            data = mutate(base.data, rng)
            requester = rng.choice(REQUESTERS)
            dt = rng.choice(TIME_DELTAS)
            now += dt
            sid = data[0] if data else None

            before_cov = len(coverage.seen)
            try:
                if args.target == "fake":
                    response = mod.handle_request(data)
                elif args.target == "stateful":
                    response = state.handle(data, requester, now)
                else:
                    response = mod.Response.from_payload(data)
            except ValueError as e:
                if args.target != "udsoncan" and (str(e) != "empty UDS request" or data):
                    findings.append(f"CRASH ValueError({e!r}) for req={data.hex()} requester={requester}")
                elif args.target == "udsoncan":
                    findings.append(f"CRASH ValueError({e!r}) for payload={data.hex()} (should never raise)")
                continue
            except Exception as e:  # noqa: BLE001 - this *is* the crash oracle
                findings.append(
                    f"CRASH {type(e).__name__}({e!r}) for req={data.hex()} requester={requester} dt={dt}"
                )
                continue

            if args.target == "udsoncan":
                sig = (response.valid, response.positive, response.code)
            else:
                findings.extend(check_oracles(sid, data, response))
                sig = response_signature(sid, response)
            transition = (last_sig, sig)
            last_sig = sig
            new_cov = len(coverage.seen) > before_cov
            new_sig = sig not in seen_signatures
            new_transition = transition not in seen_transitions
            seen_signatures.add(sig)
            seen_transitions.add(transition)

            if new_cov or new_sig or new_transition:
                corpus.append(Seed(data, requester, dt))

    stats.corpus_size = len(corpus)
    stats.coverage_lines = len(coverage.seen)
    stats.unique_signatures = len(seen_signatures)
    stats.findings = sorted(set(findings))

    report = {
        "target": args.target,
        "iterations": stats.iterations,
        "corpus_size": stats.corpus_size,
        "coverage_lines_hit": stats.coverage_lines,
        "unique_response_signatures": stats.unique_signatures,
        "unique_transitions": len(seen_transitions),
        "findings_count": len(stats.findings),
        "findings": stats.findings,
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
