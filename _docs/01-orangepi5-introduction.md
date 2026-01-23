# Orange Pi 5 소개

## 목차
1. [Orange Pi 5란?](#orange-pi-5란)
2. [하드웨어 사양](#하드웨어-사양)
3. [주요 특징](#주요-특징)
4. [지원 운영체제](#지원-운영체제)
5. [Raspberry Pi와의 비교](#raspberry-pi와의-비교)
6. [NPU (Neural Processing Unit)](#npu-neural-processing-unit)
7. [사용 사례](#사용-사례)

---

## Orange Pi 5란?

Orange Pi 5는 중국의 Shenzhen Xunlong Software에서 개발한 싱글보드 컴퓨터(SBC)입니다. Rockchip RK3588S 프로세서를 탑재하여 고성능 컴퓨팅과 AI 추론이 가능한 강력한 임베디드 플랫폼입니다.

### 왜 Orange Pi 5인가?

- **가격 대비 성능**: Raspberry Pi 대비 높은 성능을 합리적인 가격에 제공
- **NPU 내장**: 6 TOPS AI 가속기로 엣지 AI 애플리케이션에 최적화
- **다양한 인터페이스**: PCIe, USB 3.0, HDMI 2.1 등 현대적 인터페이스 지원
- **산업용 적합성**: IoT, 엣지 컴퓨팅, 스마트 팩토리 등에 활용 가능

---

## 하드웨어 사양

### Orange Pi 5 기본 사양

| 항목 | 사양 |
|------|------|
| **프로세서** | Rockchip RK3588S |
| **CPU** | 4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz |
| **GPU** | Mali-G610 MP4 |
| **NPU** | 6 TOPS (INT8) |
| **RAM** | 4GB / 8GB / 16GB LPDDR4X |
| **저장장치** | eMMC 슬롯, M.2 NVMe SSD 슬롯, MicroSD |
| **네트워크** | 기가비트 이더넷 |
| **무선** | WiFi 6 + BT 5.0 (선택사양) |
| **USB** | 1x USB 3.0, 2x USB 2.0, 1x USB Type-C |
| **영상출력** | 1x HDMI 2.1 (8K@60Hz) |
| **카메라** | MIPI CSI (2-lane, 4-lane) |
| **GPIO** | 26핀 헤더 |
| **전원** | 5V/4A Type-C |
| **크기** | 100mm x 62mm |

### Orange Pi 5 Plus / Pro 비교

| 항목 | Orange Pi 5 | Orange Pi 5 Plus | Orange Pi 5 Pro |
|------|-------------|------------------|-----------------|
| SoC | RK3588S | RK3588 | RK3588S |
| RAM 최대 | 16GB | 32GB | 16GB |
| PCIe | M.2 M-key | M.2 M-key + E-key | M.2 M-key |
| 이더넷 | 1x GbE | 2x 2.5GbE | 1x GbE |
| HDMI | 1x | 2x | 1x |

---

## 주요 특징

### 1. 고성능 8코어 CPU
```
┌─────────────────────────────────────────┐
│           RK3588S CPU 구성               │
├─────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐               │
│  │ A76     │ │ A76     │  Big Cores    │
│  │ 2.4GHz  │ │ 2.4GHz  │  (고성능)      │
│  └─────────┘ └─────────┘               │
│  ┌─────────┐ ┌─────────┐               │
│  │ A76     │ │ A76     │               │
│  │ 2.4GHz  │ │ 2.4GHz  │               │
│  └─────────┘ └─────────┘               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  │ A55     │ │ A55     │ │ A55     │ │ A55     │
│  │ 1.8GHz  │ │ 1.8GHz  │ │ 1.8GHz  │ │ 1.8GHz  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘
│           Little Cores (저전력)          │
└─────────────────────────────────────────┘
```

### 2. NPU (Neural Processing Unit)
- **6 TOPS** (Tera Operations Per Second) 성능
- INT8/INT16/FP16 연산 지원
- RKNN (Rockchip Neural Network) SDK 제공
- 실시간 객체 감지, 얼굴 인식, 포즈 추정 등 AI 작업 가속

### 3. 멀티미디어 지원
- 8K@60Hz 또는 4K@120Hz 비디오 디코딩
- 8K@30Hz 비디오 인코딩
- H.265/H.264/VP9/AV1 코덱 지원

### 4. 확장성
- M.2 NVMe SSD 지원 (PCIe 3.0 x4)
- 26핀 GPIO 헤더
- MIPI CSI 카메라 인터페이스
- MIPI DSI 디스플레이 인터페이스

---

## 지원 운영체제

### 공식 지원 OS

| OS | 버전 | 특징 |
|----|------|------|
| **Orange Pi OS (Arch)** | 최신 | 공식 지원, Arch Linux 기반 |
| **Orange Pi OS (Droid)** | Android 12 | 안드로이드 환경 |
| **Debian** | 11/12 (Bullseye/Bookworm) | 안정적, 서버/IoT용 권장 |
| **Ubuntu** | 22.04/24.04 LTS | 데스크톱/개발 환경 권장 |

### 커뮤니티 지원 OS

| OS | 특징 |
|----|------|
| **Armbian** | 다양한 SBC 지원, 커뮤니티 활성화 |
| **Manjaro ARM** | Arch 기반, 롤링 릴리스 |
| **DietPi** | 경량 OS, 서버 최적화 |

### 권장 OS (이 튜토리얼 기준)

```
┌────────────────────────────────────────────────────────┐
│  권장: Debian 12 (Bookworm) 또는 Ubuntu 22.04 LTS     │
├────────────────────────────────────────────────────────┤
│  이유:                                                 │
│  • AWS Greengrass Core 공식 지원                      │
│  • apt 패키지 관리자 사용                              │
│  • 안정적인 장기 지원                                  │
│  • Python 3.10+ 기본 포함                             │
│  • RKNN SDK 호환성 우수                               │
└────────────────────────────────────────────────────────┘
```

---

## Raspberry Pi와의 비교

### 스펙 비교표

| 항목 | Orange Pi 5 | Raspberry Pi 5 | Raspberry Pi 4B |
|------|-------------|----------------|-----------------|
| **SoC** | RK3588S | BCM2712 | BCM2711 |
| **CPU** | 4xA76 + 4xA55 | 4xA76 | 4xA72 |
| **클럭** | 2.4/1.8 GHz | 2.4 GHz | 1.8 GHz |
| **GPU** | Mali-G610 MP4 | VideoCore VII | VideoCore VI |
| **NPU** | 6 TOPS | ❌ 없음 | ❌ 없음 |
| **RAM** | 최대 16GB | 최대 8GB | 최대 8GB |
| **NVMe** | ✅ M.2 슬롯 | 외장 HAT 필요 | ❌ 없음 |
| **가격** | ~$90 (8GB) | ~$80 (8GB) | ~$75 (8GB) |

### 성능 비교

```
CPU 벤치마크 (Geekbench 5 기준, 추정치)
┌─────────────────────────────────────────────────────────┐
│ Orange Pi 5      ████████████████████████████  ~1100   │
│ Raspberry Pi 5   ████████████████████████      ~900    │
│ Raspberry Pi 4B  ████████████████              ~600    │
└─────────────────────────────────────────────────────────┘

AI 추론 성능 (TOPS)
┌─────────────────────────────────────────────────────────┐
│ Orange Pi 5      ██████████████████████████████  6.0   │
│ Raspberry Pi 5   (NPU 없음, CPU로 추론)          ~0.2  │
│ Raspberry Pi 4B  (NPU 없음, CPU로 추론)          ~0.1  │
└─────────────────────────────────────────────────────────┘
```

### 장단점 비교

#### Orange Pi 5 장점
- ✅ 내장 NPU로 AI 추론 가속
- ✅ M.2 NVMe SSD 직접 연결 가능
- ✅ 더 높은 CPU 성능
- ✅ 8K 비디오 지원
- ✅ 가격 대비 성능 우수

#### Orange Pi 5 단점
- ❌ 커뮤니티 규모가 작음
- ❌ 공식 문서 부족
- ❌ 일부 액세서리 호환성 제한
- ❌ 전력 소비가 더 높음 (5V/4A 권장)

#### Raspberry Pi 장점
- ✅ 방대한 커뮤니티와 문서
- ✅ 다양한 액세서리 생태계
- ✅ 공식 지원 우수
- ✅ GPIO 라이브러리 완성도

#### Raspberry Pi 단점
- ❌ NPU 없음 (AI 작업 시 불리)
- ❌ 상대적으로 낮은 성능
- ❌ NVMe 지원을 위해 추가 HAT 필요

---

## NPU (Neural Processing Unit)

### NPU란?

NPU(Neural Processing Unit)는 신경망 연산에 최적화된 전용 프로세서입니다. Orange Pi 5의 RK3588S에 내장된 NPU는 딥러닝 추론 작업을 CPU/GPU보다 훨씬 효율적으로 처리합니다.

### RK3588S NPU 사양

```
┌────────────────────────────────────────────────────────┐
│                    RKNN NPU                            │
├────────────────────────────────────────────────────────┤
│  성능: 6 TOPS (INT8)                                  │
│  지원 정밀도: INT4, INT8, INT16, FP16, BF16           │
│  지원 프레임워크:                                      │
│    • TensorFlow / TensorFlow Lite                     │
│    • PyTorch                                          │
│    • ONNX                                             │
│    • Caffe                                            │
│    • MXNet                                            │
└────────────────────────────────────────────────────────┘
```

### RKNN 개발 흐름

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   학습된     │    │   RKNN      │    │   Orange    │
│   모델      │───▶│   Toolkit   │───▶│   Pi 5     │
│ (.pt/.onnx) │    │  (변환/양자화)│    │  (추론실행) │
└──────────────┘    └──────────────┘    └──────────────┘
     PC/서버            PC              Orange Pi 5

모델 변환 과정:
1. PyTorch/TensorFlow 모델 학습 (PC)
2. ONNX 형식으로 내보내기
3. RKNN Toolkit으로 .rknn 형식 변환
4. Orange Pi 5에서 RKNN Lite로 추론
```

### 지원 모델 예시

| 분류 | 모델 | 용도 |
|------|------|------|
| 객체 감지 | YOLOv5/v7/v8 | 물체 인식 |
| 포즈 추정 | MoveNet | 사람 자세 분석 |
| 얼굴 인식 | RetinaFace | 얼굴 검출 |
| 분류 | MobileNet, ResNet | 이미지 분류 |
| 세그멘테이션 | DeepLabV3 | 영역 분할 |
| PPE 감지 | Custom YOLO | 안전장비 감지 |

---

## 사용 사례

### 1. 엣지 AI / IoT
```
┌─────────────────────────────────────────────────────────┐
│  카메라 ──▶ Orange Pi 5 (NPU) ──▶ AWS IoT Greengrass  │
│                    │                                    │
│                    ▼                                    │
│            실시간 객체 감지                             │
│            • PPE 감지 (안전모, 조끼)                   │
│            • 침입 감지                                  │
│            • 불량품 검출                               │
└─────────────────────────────────────────────────────────┘
```

### 2. 스마트 팩토리
- 생산 라인 품질 검사
- 작업자 안전 모니터링
- 설비 이상 감지

### 3. 스마트 시티
- 교통량 분석
- 주차장 관리
- 환경 모니터링

### 4. 스마트 홈
- 홈 오토메이션 서버
- 미디어 서버 (Plex, Jellyfin)
- NAS 구성

---

## 다음 단계

이제 Orange Pi 5에 대한 기본적인 이해를 마쳤습니다. 다음 문서에서는 실제로 Orange Pi 5에 운영체제를 설치하고 기본 설정을 진행합니다.

➡️ [02. OS 설치 및 기본 설정](./02-orangepi5-os-installation.md)

---

## 참고 자료

- [Orange Pi 공식 사이트](http://www.orangepi.org/)
- [Orange Pi 5 Wiki](http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_5)
- [Rockchip RK3588S 데이터시트](https://www.rock-chips.com/a/en/products/RK35_Series/2022/0926/1660.html)
- [RKNN Toolkit GitHub](https://github.com/rockchip-linux/rknn-toolkit2)
