# Orange Pi 5 + AWS Greengrass 튜토리얼

Orange Pi 5 싱글보드 컴퓨터에 AWS IoT Greengrass를 설치하고, NPU를 활용한 실시간 PPE(개인보호장비) 감지 시스템을 구축하는 튜토리얼입니다.

## 개요

이 프로젝트는 다음을 다룹니다:

- **Orange Pi 5** 소개 및 Debian OS 설치
- **AWS IoT Greengrass V2** 설치 및 구성
- **MQTT/S3** 통합 테스트
- **NPU 기반 AI 추론**: RTSP 카메라 + PPE 감지
- 완전한 Python 소스 코드 및 테스트

## 시스템 요구사항

### 하드웨어
| 항목 | 권장 사양 |
|------|----------|
| Orange Pi 5 | 8GB RAM |
| 전원 | 5V/4A USB-C |
| 저장장치 | 32GB+ MicroSD |
| 네트워크 | 이더넷 또는 WiFi |

### 소프트웨어
- Debian 12 (Bookworm) 또는 Ubuntu 22.04
- Python 3.10+
- AWS 계정

## 빠른 시작

```bash
# 1. 저장소 클론
git clone <repository-url>
cd Orangepi5_Greengrass

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 시뮬레이션 모드로 테스트
export USE_SIMULATION=true
python src/main.py

# 4. 테스트 실행
python tests/test_ppe_detection.py
```

## 프로젝트 구조

```
Orangepi5_Greengrass/
├── _docs/                    # 튜토리얼 문서 (6개 챕터)
│   ├── 01-orangepi5-introduction.md
│   ├── 02-orangepi5-os-installation.md
│   ├── 03-aws-greengrass-introduction.md
│   ├── 04-greengrass-edge-device-setup.md
│   ├── 05-s3-mqtt-integration.md
│   └── 06-npu-rtsp-ppe-detection.md
├── src/                      # Python 소스 코드
│   ├── rtsp_reader.py        # RTSP/시뮬레이션 카메라
│   ├── ppe_detector.py       # PPE 감지기 (RKNN NPU)
│   └── main.py               # 메인 애플리케이션
├── tests/                    # 테스트 코드
└── requirements.txt          # Python 의존성
```

## 튜토리얼 목차

1. **[Orange Pi 5 소개](_docs/01-orangepi5-introduction.md)**
   - 하드웨어 사양, NPU 설명
   - Raspberry Pi와의 비교

2. **[OS 설치 및 기본 설정](_docs/02-orangepi5-os-installation.md)**
   - Debian/Ubuntu 설치
   - 개발 환경 구성

3. **[AWS Greengrass 소개](_docs/03-aws-greengrass-introduction.md)**
   - 아키텍처 및 개념
   - 사용 사례

4. **[Greengrass 설치](_docs/04-greengrass-edge-device-setup.md)**
   - 코어 디바이스 설정
   - 첫 번째 컴포넌트 배포

5. **[S3 및 MQTT 통합](_docs/05-s3-mqtt-integration.md)**
   - MQTT 메시징 테스트
   - S3 업로드 구현

6. **[NPU + PPE 감지](_docs/06-npu-rtsp-ppe-detection.md)**
   - RKNN 모델 설정
   - 실시간 영상 분석
   - Greengrass 컴포넌트 배포

## 주요 기능

### PPE 감지 항목
- 안전모 (착용/미착용)
- 안전조끼 (착용/미착용)
- 마스크 (착용/미착용)
- 보안경, 안전장갑

### 시스템 기능
- 실시간 RTSP 영상 처리
- NPU 가속 AI 추론 (6 TOPS)
- MQTT 위반 알림
- S3 이미지 업로드
- 시뮬레이션 모드 (개발/테스트용)

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `THING_NAME` | IoT Thing 이름 | orangepi5-core-001 |
| `RTSP_URL` | RTSP 카메라 URL | (시뮬레이션) |
| `MODEL_PATH` | RKNN 모델 경로 | (시뮬레이션) |
| `S3_BUCKET` | S3 버킷 이름 | orangepi5-greengrass-data |
| `USE_SIMULATION` | 시뮬레이션 모드 | true |

## 라이선스

이 프로젝트는 교육 목적으로 제공됩니다.
