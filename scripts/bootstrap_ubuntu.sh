#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential can-utils docker.io docker-compose-v2 git iproute2 pipx \
  python3 python3-venv qemu-system-x86

if ! command -v gallia >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/gallia" ]; then
  pipx install gallia==2.1.1
fi
pipx ensurepath
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
echo "[+] bootstrap complete"
echo "[i] Re-login once if 'gallia' is not found on PATH."
