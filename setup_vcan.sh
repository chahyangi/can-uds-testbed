#!/usr/bin/env bash
# vcan0 인터페이스 생성 및 활성화 (재부팅 시마다 필요)
set -e
sudo modprobe vcan
sudo modprobe can-isotp
if ! ip link show vcan0 &>/dev/null; then
    sudo ip link add dev vcan0 type vcan
fi
sudo ip link set vcan0 up
ip -details link show vcan0
echo "[+] vcan0 ready"
