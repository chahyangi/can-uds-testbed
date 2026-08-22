# 공통 테스트베드 진행 현황

검증일: 2026-08-22

| 항목 | 상태 | 검증 근거 |
|---|---|---|
| Ubuntu 및 Docker | 완료 | Ubuntu 24.04 VM, Gallia 2.1.1 Docker 이미지 재현 빌드 |
| SocketCAN과 vCAN | 완료 | `vcan0`, `vcan_codex`, `vcan_docker` 인터페이스 기동 |
| CAN 송수신 및 로깅 | 완료 | `candump -L` 요청/응답 프레임 저장 |
| ISO-TP 기본 통신 | 완료 | 0x7E0/0x7E8 ISO-TP 양방향 통신 |
| UDS 기본 통신 | 완료 | 0x10, 0x3E 및 NRC 0x11/0x31 검증 |
| Tester와 가상 ECU | 완료 | Gallia Tester ↔ Gallia vECU |
| 오픈소스 ECU | 완료 | Gallia Tester ↔ iso14229 C ECU 예제 |
| Docker 통신 | 완료 | 호스트 Tester ↔ Docker Gallia vECU |
| QEMU 기본 구성 | 완료 | QEMU 8.2.2 x86_64 TCG machine 기동 |
| GitHub 실행 환경 공유 | 완료 | 재현 스크립트·테스트·문서 커밋 및 원격 저장소 업로드 |

## 전체 회귀 검증 결과

아래 항목을 한 번에 재검증했다.

1. Python 가상 ECU 단위 테스트 5개
2. Gallia vECU의 정상 응답, NRC, 상태 전이
3. iso14229 ECU의 RDBI 정상 응답과 RequestOutOfRange NRC
4. QEMU TCG 가상 머신 기동
5. Docker Gallia ECU와 호스트 Tester 통신

모든 항목이 PASS였다. 실행별 원본 로그는 VM의
`~/can-uds-testbed-codex-51b00ca/artifacts/` 아래에 시간별로 보존된다.

## 보고서 화면 구성

세 개 셸을 다음처럼 배치하면 진행 과정이 가장 분명하다.

1. 왼쪽: Gallia 또는 iso14229 가상 ECU 실행 화면
2. 오른쪽 위: Gallia Tester 요청 및 해석된 응답
3. 오른쪽 아래: `candump -L`의 동일 시점 0x7E0/0x7E8 프레임

화면 캡처는 과정 설명에 쓰고, `artifacts` 원본 로그는 결과의 재현성과
정확성을 뒷받침하는 자료로 사용한다.
