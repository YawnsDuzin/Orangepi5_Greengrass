# Orange Pi 5 + AWS Greengrass 튜토리얼

이 튜토리얼은 Orange Pi 5 싱글보드 컴퓨터에 AWS IoT Greengrass를 설치하고, NPU를 활용한 PPE(개인보호장비) 감지 시스템을 구축하는 방법을 단계별로 안내합니다.

## 대상 독자

- Orange Pi 또는 싱글보드 컴퓨터 입문자
- AWS IoT 및 Greengrass 초보자
- 엣지 AI 및 IoT 프로젝트에 관심 있는 개발자
- 산업 현장의 안전 모니터링 시스템 구축에 관심 있는 분

## 튜토리얼 구성

| 순서 | 문서 | 내용 |
|------|------|------|
| 1 | [Orange Pi 5 소개](./01-orangepi5-introduction.md) | 하드웨어 사양, 특징, Raspberry Pi 비교 |
| 2 | [OS 설치 및 기본 설정](./02-orangepi5-os-installation.md) | Debian 설치, 초기 설정, 개발 환경 |
| 3 | [AWS Greengrass 소개](./03-aws-greengrass-introduction.md) | Greengrass 개념, 아키텍처, 비용 |
| 4 | [Greengrass 설치](./04-greengrass-edge-device-setup.md) | 코어 디바이스 설치 및 연결 |
| 5 | [S3 및 MQTT 통합](./05-s3-mqtt-integration.md) | 데이터 전송 테스트 |
| 6 | [NPU + PPE 감지](./06-npu-rtsp-ppe-detection.md) | RTSP 카메라, AI 추론, 알림 시스템 |

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        전체 시스템                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌─────────────────────────────────────────┐   │
│  │  RTSP    │───▶│           Orange Pi 5                   │   │
│  │  카메라  │    │  ┌────────────────────────────────────┐ │   │
│  └──────────┘    │  │         Greengrass Core           │ │   │
│                  │  │  ┌──────────────────────────────┐ │ │   │
│                  │  │  │  PPE Detection Component     │ │ │   │
│                  │  │  │  (RKNN NPU 6 TOPS)          │ │ │   │
│                  │  │  └──────────────────────────────┘ │ │   │
│                  │  └────────────────────────────────────┘ │   │
│                  └────────────────────┬────────────────────┘   │
│                                       │                        │
│                                       │ MQTT/HTTPS             │
│                                       ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     AWS Cloud                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │  IoT Core  │  │     S3     │  │ CloudWatch │        │   │
│  │  │   (알림)   │  │  (이미지)  │  │   (로그)   │        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 필수 준비물

### 하드웨어
- Orange Pi 5 (8GB RAM 권장)
- 5V/4A USB-C 전원 어댑터
- MicroSD 카드 (32GB 이상)
- 이더넷 케이블
- (선택) RTSP 지원 IP 카메라

### 소프트웨어/서비스
- AWS 계정
- Debian 12 또는 Ubuntu 22.04 이미지
- Python 3.10+

## 빠른 시작

```bash
# 1. 튜토리얼 문서 읽기
cat _docs/01-orangepi5-introduction.md

# 2. 소스 코드 테스트 (시뮬레이션 모드)
cd src
python3 -c "
from ppe_detector import PPEDetector
import numpy as np

detector = PPEDetector(use_simulation=True)
frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
detections = detector.detect(frame)
print(f'감지 결과: {len(detections)}개')
for d in detections:
    print(f'  - {d.class_name}: {d.confidence:.2f}')
detector.release()
"

# 3. 전체 시스템 테스트
export USE_SIMULATION=true
python3 main.py
```

## 디렉토리 구조

```
Orangepi5_Greengrass/
├── _docs/                          # 튜토리얼 문서
│   ├── README.md                   # 이 파일
│   ├── 01-orangepi5-introduction.md
│   ├── 02-orangepi5-os-installation.md
│   ├── 03-aws-greengrass-introduction.md
│   ├── 04-greengrass-edge-device-setup.md
│   ├── 05-s3-mqtt-integration.md
│   └── 06-npu-rtsp-ppe-detection.md
├── src/                            # 소스 코드
│   ├── __init__.py
│   ├── rtsp_reader.py              # RTSP 카메라 리더
│   ├── ppe_detector.py             # PPE 감지기
│   └── main.py                     # 메인 애플리케이션
├── tests/                          # 테스트 코드
│   └── test_ppe_detection.py
├── requirements.txt                # Python 의존성
└── README.md                       # 프로젝트 README
```

## 주요 기능

### 1. PPE 감지 (개인보호장비)
- 안전모 착용/미착용 감지
- 안전조끼 착용/미착용 감지
- 마스크 착용/미착용 감지
- 보안경, 안전장갑 감지

### 2. 실시간 알림
- PPE 위반 발생 시 MQTT 알림
- 위반 이미지 S3 자동 업로드
- 쿨다운으로 중복 알림 방지

### 3. 시뮬레이션 모드
- 실제 카메라/모델 없이 테스트 가능
- 개발 및 디버깅에 유용

## 문의 및 기여

문제가 있거나 개선 제안이 있으시면 이슈를 등록해 주세요.

## 라이선스

이 튜토리얼은 교육 목적으로 제공됩니다.
