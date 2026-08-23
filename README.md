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

## 다른 Linux 컴퓨터에서 Docker로 한 번에 재현

Docker Engine과 Compose plugin이 설치된 Linux 컴퓨터에서는 다음 한 줄로
컨테이너 이미지 빌드, 가상 CAN 버스 생성, Gallia ECU 기동, Tester 검증을
한 번에 실행할 수 있습니다.

```bash
make docker-portable-test
```

기존 Docker 실습은 Ubuntu 호스트에 만들어 둔 `vcan0`를 `--network host`로
컨테이너가 빌려 쓰는 방식이었습니다. 새 Compose 구성은 `can-bus` 컨테이너의
네트워크 namespace 안에 `vcan0`를 만들고, `gallia-vecu`와 `tester` 컨테이너가
그 namespace를 공유합니다. 따라서 호스트에 미리 `vcan0`를 만들 필요가 없고,
테스트가 끝나면 컨테이너와 함께 인터페이스도 사라집니다.

단, 컨테이너도 호스트 커널을 사용하므로 Linux 호스트가 `vcan`과 `can-isotp`
커널 모듈을 제공해야 합니다. 실행 스크립트가 두 모듈을 `modprobe`하며 sudo
권한이 필요합니다. Windows/macOS Docker Desktop은 SocketCAN 커널 지원을
보장하지 않으므로 이 경로의 지원 대상이 아닙니다.

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

## 공격 실습 (0x22 과부하 · 세션 거부)

VehicleSec 2024 논문(Exploiting Diagnostic Protocol Vulnerabilities on
Embedded Networks in Commercial Vehicles)의 V-A, V-B 공격을 이 테스트베드의
가상 ECU에 재현합니다.

```bash
./setup_vcan.sh
./scripts/run_stateful_ecu.sh &          # 터미널 1: 세션 잠금이 있는 ECU
python3 attacks/overload_0x22.py --interface vcan0 --sweep-ms 0.1,0.5,2 --duration 2
python3 attacks/session_denial.py --interface vcan0 --duration 20 --probe
```

`make attack-test`로 두 공격을 자동 실행하고 증빙 로그를
`artifacts/attacks/<timestamp>/`에 저장할 수 있습니다. 공격 원리와
`fake_ecu.py` 대신 세션 상태를 갖는 `stateful_ecu.py`를 새로 둔 이유는
[docs/ATTACKS.md](docs/ATTACKS.md)를 참고하세요.

## 저장소 구성

- `fake_ecu.py`: 읽기 쉬운 Python UDS ECU
- `stateful_ecu.py`: 단일 활성 세션 잠금이 있는 Python UDS ECU (세션 거부 공격 대상)
- `attacks/overload_0x22.py`: 0x22 ReadDataByIdentifier 과부하 공격
- `attacks/session_denial.py`: 0x10 세션 선점 + 0x3E 유지로 정상 접속을 막는 공격
- `scripts/run_gallia_vecu.sh`: seed가 고정된 Gallia 랜덤 ECU
- `scripts/test_gallia_vecu.sh`: 자동 Request/Response/NRC 검증
- `scripts/run_stateful_ecu.sh`, `scripts/test_attacks.sh`: 공격 실습용 ECU 기동과 자동 증빙 수집
- `third_party/iso14229`: C 기반 ECU 구현(고정된 Git submodule)
- `Dockerfile.gallia`, `compose.yaml`: 컨테이너 실행 환경
- `docs/`: 구조, 공격 실습, 보고서 증빙, 문제 해결 문서

구조와 도구 선택은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), 공격
실습은 [docs/ATTACKS.md](docs/ATTACKS.md), 보고서용 스크린샷과 로그 기준은
[docs/REPORT_EVIDENCE.md](docs/REPORT_EVIDENCE.md)를 참고하세요.
