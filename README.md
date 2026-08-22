# CAN/UDS Virtual Testbed

Ubuntu 24.04의 SocketCAN/vCAN 위에서 Tester와 가상 ECU 사이의 ISO-TP 및
UDS Request/Response를 재현하는 공통 실습 환경입니다. Windows x86_64
호스트의 VirtualBox Ubuntu Server에서 검증하며, 동일한 Linux 명령으로
다른 조가 재현할 수 있도록 구성했습니다.

## 현재 완료 범위

- Ubuntu, Docker, SocketCAN/vCAN 구성
- CAN 송수신 및 `candump` 로깅
- ISO-TP 송수신
- Gallia 2.1.1 가상 ECU와 Tester의 UDS 통신
- Positive Response, NRC 0x11, 세션 전환과 TesterPresent 검증
- iso14229 C ECU 소스 고정 및 Linux 예제 빌드
- QEMU x86_64 TCG 가상 머신 기동 smoke test
- GitHub Actions 단위시험·빌드 검증

## 빠른 재현

```bash
git clone --recurse-submodules https://github.com/chahyangi/can-uds-testbed.git
cd can-uds-testbed
./scripts/bootstrap_ubuntu.sh
./setup_vcan.sh
make unit
make gallia-test
make iso14229-build
make qemu-check
```

`make gallia-test`는 Gallia 가상 ECU, Tester, `candump`를 자동으로 실행하고
결과를 `artifacts/gallia-vecu/<timestamp>/`에 저장합니다.

## 수동 3-터미널 실습

터미널 1 — 가상 ECU:

```bash
./scripts/run_gallia_vecu.sh
```

터미널 2 — Tester:

```bash
gallia primitive uds pdu \
  --target "isotp://vcan0?tx_id=0x7e0&rx_id=0x7e8&is_fd=false" \
  --no-ping --no-tester-present --no-dumpcap 1001
```

터미널 3 — 로거:

```bash
candump -L vcan0
```

## 저장소 구성

- `fake_ecu.py`: 읽기 쉬운 Python UDS ECU
- `scripts/run_gallia_vecu.sh`: seed가 고정된 Gallia 랜덤 ECU
- `scripts/test_gallia_vecu.sh`: 자동 Request/Response/NRC 검증
- `third_party/iso14229`: C 기반 ECU 구현(고정된 Git submodule)
- `Dockerfile.gallia`, `compose.yaml`: 컨테이너 실행 환경
- `docs/`: 구조, 보고서 증빙, 문제 해결 문서

구조와 도구 선택은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), 보고서용
스크린샷과 로그 기준은 [docs/REPORT_EVIDENCE.md](docs/REPORT_EVIDENCE.md)를
참고하세요.
