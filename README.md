# CAN/UDS Virtual Testbed

SocketCAN 가상 인터페이스(vcan0) 위에서 가상 ECU와 UDS Tester(Gallia) 간
Request/Response를 재현하는 최소 구현물(PoC).

## 환경
- Ubuntu 24.04 (VirtualBox / UTM)
- SocketCAN, vcan, can-isotp
- Python 3.12 (can-isotp, udsoncan)
- Gallia (UDS Tester)

## 구성
- `fake_ecu.py` : vcan0에서 UDS 요청을 받아 응답하는 가상 ECU
- `setup_vcan.sh` : vcan0 인터페이스 생성/활성화 스크립트

## 실행 방법

### 1. vcan0 준비
```bash
./setup_vcan.sh
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 가상 ECU 실행 (터미널 1)
```bash
python fake_ecu.py
```
`rx=0x7E0` 요청 수신, `tx=0x7E8` 응답 송신.

### 4. Gallia로 UDS 서비스 스캔 (터미널 2)
```bash
gallia scan uds services --target "isotp://vcan0?tx_id=0x7E0&rx_id=0x7E8&is_fd=false"
```

## 지원 UDS 서비스 (가상 ECU)
| SID  | 서비스 |
|------|--------|
| 0x10 | DiagnosticSessionControl |
| 0x11 | ECUReset |
| 0x22 | ReadDataByIdentifier |
| 0x3E | TesterPresent |
| 그 외 | Negative Response (0x7F, serviceNotSupported) |

## 결과 예시
```
[0x10] DiagnosticSessionControl: ...
[0x11] EcuReset: ...
[0x22] ReadDataByIdentifier: data_records=[020304]
[0x3e] TesterPresent
```

## 트러블슈팅
- `gallia: command not found` → `export PATH="$HOME/.local/bin:$PATH"`
- Gallia target 파라미터는 `tx_id`/`rx_id` 사용 (구버전 `src_addr`/`dst_addr` 아님)
- Tester 기준 tx/rx는 ECU와 반대 (ECU rx=0x7E0 → Tester tx=0x7E0)
