#!/usr/bin/env bash
# Build and run iso14229's own libFuzzer harness (third_party/iso14229/fuzz/fuzz_server.cc)
# without needing bazel: clang for the C library (keeps C semantics -- compiling it
# with clang++ instead breaks on C-only idioms like goto-past-initialization), clang++
# for the C++ harness (uses FuzzedDataProvider), then linked together as one binary.
#
# Usage: ./scripts/fuzz_iso14229.sh [seconds]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_DIR="$REPO_ROOT/third_party/iso14229"
BUILD_DIR="/tmp/fuzzbuild"
DURATION="${1:-60}"

mkdir -p "$BUILD_DIR/corpus" "$BUILD_DIR/artifacts"

# fuzz_server.cc includes "src/iso14229.h", but the checked-out submodule only has
# the amalgamated header at the repo root (src/ has the split-up originals it was
# generated from). Symlink so the include resolves without patching the vendored source.
ln -sf ../iso14229.h "$ISO_DIR/src/iso14229.h"

clang -g -O0 -DUDS_TP_ISOTP_MOCK -DUDS_CUSTOM_MILLIS -DUDS_LINES \
    -I"$ISO_DIR" -fsanitize=fuzzer-no-link,address \
    -c "$ISO_DIR/iso14229.c" -o "$BUILD_DIR/iso14229.o"

clang++ -g -O0 -std=c++17 -DUDS_TP_ISOTP_MOCK -DUDS_CUSTOM_MILLIS -DUDS_LINES \
    -I"$ISO_DIR" -fsanitize=fuzzer,address \
    -c "$ISO_DIR/fuzz/fuzz_server.cc" -o "$BUILD_DIR/fuzz_server.o"

clang++ -g -O0 -fsanitize=fuzzer,address \
    "$BUILD_DIR/iso14229.o" "$BUILD_DIR/fuzz_server.o" \
    -o "$BUILD_DIR/fuzz_iso14229"

echo "Built $BUILD_DIR/fuzz_iso14229 -- running for ${DURATION}s"
"$BUILD_DIR/fuzz_iso14229" -max_total_time="$DURATION" \
    -artifact_prefix="$BUILD_DIR/artifacts/" "$BUILD_DIR/corpus"
