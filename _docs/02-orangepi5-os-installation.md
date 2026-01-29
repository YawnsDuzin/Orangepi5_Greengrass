# Orange Pi 5 OS 설치 및 NPU 환경 설정

## 목차
1. [NPU 소프트웨어 스택 이해](#npu-소프트웨어-스택-이해)
2. [호환성 매트릭스](#호환성-매트릭스)
3. [OS 선택 가이드](#os-선택-가이드)
4. [준비물](#준비물)
5. [OS 이미지 다운로드](#os-이미지-다운로드)
6. [부팅 미디어 만들기](#부팅-미디어-만들기)
7. [첫 부팅 및 초기 설정](#첫-부팅-및-초기-설정)
8. [시스템 기본 설정](#시스템-기본-설정)
9. [개발 환경 구성](#개발-환경-구성)
10. [NPU 환경 설정](#npu-환경-설정)
11. [NPU 동작 검증](#npu-동작-검증)
12. [네트워크 설정](#네트워크-설정)
13. [문제 해결](#문제-해결)

---

## NPU 소프트웨어 스택 이해

Orange Pi 5의 NPU를 사용하려면 **4개의 소프트웨어 구성요소가 모두 호환되는 버전**으로 맞춰져야 합니다. 이 중 하나라도 버전이 맞지 않으면 NPU가 동작하지 않습니다.

```
 PC (x86_64)                              Orange Pi 5 (aarch64)
+----------------------------+           +-------------------------------------+
|                            |           |                                     |
|  rknn-toolkit2             |           |  rknn-toolkit-lite2                 |
|  (모델 변환, 양자화,       |  .rknn    |  (Python 추론 API)                  |
|   시뮬레이션, 프로파일링)  | -------> |                                     |
|                            |  모델     |  librknnrt.so                       |
|  pip install rknn-toolkit2 |  파일     |  (C/C++ 런타임 라이브러리)          |
|                            |           |                                     |
+----------------------------+           |  RKNPU 커널 드라이버                |
                                         |  (rknpu.ko 또는 커널 내장)          |
                                         |                                     |
                                         |  Linux Kernel (BSP 5.10 / 6.1)     |
                                         +-------------------------------------+
                                         |  NPU 하드웨어 (6 TOPS)             |
                                         +-------------------------------------+
```

### 4가지 핵심 구성요소

| 구성요소 | 위치 | 역할 | 확인 방법 |
|----------|------|------|-----------|
| **RKNPU 커널 드라이버** | 커널 내장/모듈 | NPU 하드웨어 제어 | `cat /sys/kernel/debug/rknpu/version` |
| **librknnrt.so** | `/usr/lib/` | C/C++ NPU 런타임 | `strings /usr/lib/librknnrt.so \| grep "librknnrt version"` |
| **rknn-toolkit-lite2** | Python 패키지 | 보드에서 Python 추론 API | `pip3 show rknn-toolkit-lite2` |
| **rknn-toolkit2** | Python 패키지 (PC) | PC에서 모델 변환/양자화 | `pip3 show rknn-toolkit2` |

### 왜 호환성이 중요한가?

```
흔한 오류 시나리오:

 PC (rknn-toolkit2 v2.3.0)              Orange Pi 5
+---------------------------+          +---------------------------+
|  모델 변환 → model.rknn   |  ------> |  RKNPU 드라이버 v0.9.2   |  <-- 버전 불일치!
|  (모델 버전 6)            |          |  librknnrt v1.5.2        |  <-- 구버전!
+---------------------------+          |                           |
                                       |  오류: "Invalid RKNN     |
                                       |   model version 6"       |
                                       +---------------------------+
```

**모델을 변환한 rknn-toolkit2 버전과 보드의 런타임(librknnrt) 및 드라이버(RKNPU) 버전이 호환되어야 합니다.**

---

## 호환성 매트릭스

### RKNN 소프트웨어 버전 호환표

| rknn-toolkit2 (PC) | rknn-toolkit-lite2 (보드) | librknnrt (보드) | RKNPU 드라이버 (보드) | 지원 커널 | Python |
|---|---|---|---|---|---|
| 1.5.2 | 1.5.2 | 1.5.2 | v0.9.2 | 5.10 / 6.1 | 3.6-3.11 |
| 1.6.0 | 1.6.0 | 1.6.0 | v0.9.2-0.9.5 | 5.10 / 6.1 | 3.6-3.11 |
| 2.0.0b0 | 2.0.0b0 | 2.0.0b0 | v0.9.5 | 5.10 / 6.1 | 3.6-3.11 |
| 2.1.0 | 2.1.0 | 2.1.0 | v0.9.6+ | 5.10 / 6.1 | 3.6-3.11 |
| 2.2.0 | 2.2.0 | 2.2.0 | v0.9.6+ | 5.10 / 6.1 | 3.6-3.12 |
| 2.3.0 | 2.3.0 | 2.3.0 | v0.9.6-0.9.8 | 5.10 / 6.1 | 3.6-3.12 |
| **2.3.2 (최신)** | **2.3.2** | **2.3.2** | **v0.9.8** | **5.10 / 6.1** | **3.6-3.12** |

### 커널 버전 요구사항 (가장 중요)

RKNPU 드라이버는 **Rockchip BSP 커널에서만 동작**합니다.

| 커널 종류 | 버전 | NPU 지원 | 비고 |
|-----------|------|----------|------|
| **Rockchip BSP** | **5.10.x** | **지원** | 가장 안정적, 대부분의 보드 벤더 기본값 |
| **Rockchip BSP** | **6.1.x** | **지원** | 최신 BSP, 일부 배포판에서 사용 |
| Mainline | 6.6+ | **미지원** | RKNPU 드라이버 없음 |
| Mainline | 6.11+ | **미지원** | accel/rocket 드라이버 개발 중 (미완성) |

### OS별 NPU 호환성

| OS 배포판 | 커널 | RKNPU 드라이버 | NPU 사용 가능 | 비고 |
|-----------|------|----------------|--------------|------|
| **Orange Pi 공식 Ubuntu 22.04** | 5.10.160 BSP | v0.9.2~0.9.6 | **가능 (업그레이드 필요)** | 드라이버/런타임 수동 업그레이드 필요 |
| **Orange Pi 공식 Debian 12** | 6.1.43 BSP | v0.9.2~0.9.6 | **가능 (업그레이드 필요)** | 드라이버/런타임 수동 업그레이드 필요 |
| **Armbian (Rockchip BSP)** | 6.1.x BSP | v0.9.8 | **바로 가능 (권장)** | 최신 NPU 드라이버 포함 |
| Joshua Riek Ubuntu 22.04 | 5.10.x BSP | v0.9.5 이하 | **제한적** | NPU 지원 미보장, 드라이버 오래됨 |
| Joshua Riek Ubuntu 24.04 | 6.1.x BSP | v0.9.5 이하 | **제한적** | NPU 공식 미지원, 드라이버 업데이트 거절됨 |
| Joshua Riek Ubuntu 24.10 | 6.11.x Mainline | **없음** | **불가능** | Mainline 커널, RKNPU 드라이버 없음 |

### Joshua Riek Ubuntu Rockchip의 NPU 문제

[Joshua Riek의 Ubuntu Rockchip](https://github.com/Joshua-Riek/ubuntu-rockchip)은 **GPU 가속(panfork/panthor)과 데스크톱 환경에 초점**을 맞춘 프로젝트로, NPU 지원은 우선순위가 아닙니다.

- RKNPU 드라이버 v0.9.8 업데이트 요청([Issue #1093](https://github.com/Joshua-Riek/ubuntu-rockchip/issues/1093))이 **"NOT_PLANNED"으로 종료**됨
- Mainline 커널 이미지(24.10)는 RKNPU 드라이버가 아예 없음
- NPU 활성화를 위한 Device Tree Overlay를 제공하지 않음
- 커널 5.10에서 6.1로의 업그레이드가 불가능 (완전 재설치 필요)

### Python 버전 호환표

| Ubuntu 버전 | 기본 Python | rknn-toolkit-lite2 호환 | 비고 |
|-------------|-------------|------------------------|------|
| Ubuntu 20.04 | 3.8 | 지원 | 오래된 OS |
| **Ubuntu 22.04** | **3.10** | **지원** | **권장** |
| Ubuntu 24.04 | 3.12 | 지원 | 가능 |
| Debian 11 | 3.9 | 지원 | - |
| **Debian 12** | **3.11** | **지원** | **권장** |

---

## OS 선택 가이드

### 권장 OS 순위 (NPU 사용 기준)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    NPU 사용을 위한 OS 선택 가이드                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1순위: Armbian (Rockchip BSP 커널)                                     │
│  ────────────────────────────────────                                    │
│  - RKNPU 드라이버 v0.9.8 기본 포함                                      │
│  - 별도 드라이버 설치/컴파일 불필요                                      │
│  - 커뮤니티 NPU 지원 활발                                               │
│  - rsetup 도구로 시스템 업데이트 지원                                    │
│  - 다운로드: https://www.armbian.com/orangepi-5/                        │
│                                                                          │
│  2순위: Orange Pi 공식 Ubuntu 22.04 / Debian 12                         │
│  ────────────────────────────────────────────────                        │
│  - BSP 커널 포함 (5.10 또는 6.1)                                        │
│  - RKNPU 드라이버 포함 (구버전 → 수동 업그레이드 필요)                   │
│  - librknnrt.so 수동 업데이트 필요                                       │
│  - 공식 지원이므로 안정적                                                │
│                                                                          │
│  비권장: Joshua Riek Ubuntu Rockchip                                    │
│  ──────────────────────────────────────                                  │
│  - NPU 지원 미보장                                                      │
│  - 드라이버 업데이트 계획 없음 (NOT_PLANNED)                             │
│  - Mainline 커널 이미지는 NPU 불가                                      │
│  - GPU/데스크톱 환경 중심 프로젝트                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 이 튜토리얼의 권장 구성

| 구성요소 | 권장 버전 | 이유 |
|----------|-----------|------|
| **OS** | **Armbian Bookworm (server)** 또는 **Orange Pi 공식 Ubuntu 22.04** | BSP 커널 + NPU 드라이버 포함 |
| **커널** | **6.1.x (Rockchip BSP)** 또는 **5.10.x (Rockchip BSP)** | RKNPU 드라이버 지원 |
| **RKNPU 드라이버** | **v0.9.8** | 최신 RKNN 모델 호환, 멀티스레드 버그 수정 |
| **librknnrt** | **v2.3.0 이상** | 최신 모델 포맷 지원 |
| **rknn-toolkit-lite2** | **v2.3.0 이상** | librknnrt와 동일 버전 |
| **rknn-toolkit2** (PC) | **v2.3.0 이상** | 모델 변환 시 사용 |
| **Python** | **3.10 (Ubuntu 22.04) / 3.11 (Debian 12)** | RKNN 패키지 호환 |

---

## 준비물

### 필수 항목

| 항목 | 권장 사양 | 비고 |
|------|----------|------|
| **Orange Pi 5** | 8GB RAM 이상 권장 | AI 추론 시 메모리 필요 |
| **전원 어댑터** | 5V/4A USB-C | 정격 전원 중요 |
| **MicroSD 카드** | 32GB 이상, Class 10 | 부팅용 |
| **MicroSD 리더기** | USB 타입 | PC 연결용 |
| **이더넷 케이블** | Cat5e 이상 | 초기 설정용 |
| **HDMI 케이블** | HDMI 2.0 이상 | 모니터 연결 |

### 선택 항목

| 항목 | 용도 |
|------|------|
| NVMe SSD | 빠른 스토리지 (M.2 2280) |
| USB 키보드/마우스 | 직접 조작 |
| 방열판/쿨러 | 발열 관리 |
| 케이스 | 보호 및 방열 |
| WiFi/BT 모듈 | 무선 연결 (미내장 모델) |

---

## OS 이미지 다운로드

### 방법 A: Armbian (1순위 권장)

Armbian은 NPU 드라이버 v0.9.8이 기본 포함되어 가장 간편합니다.

1. [Armbian Orange Pi 5 다운로드 페이지](https://www.armbian.com/orangepi-5/) 접속
2. **Bookworm (server)** 이미지 선택
3. 커널 타입에서 **"Rockchip BSP"** (vendor kernel) 선택

```bash
# 명령줄 다운로드 (예시 - 실제 최신 버전 URL 확인 필요)
mkdir -p ~/orangepi5-images
cd ~/orangepi5-images

# Armbian Bookworm Server (Rockchip BSP 커널)
# 공식 사이트에서 최신 URL 확인 후 다운로드
wget https://dl.armbian.com/orangepi5/Bookworm_vendor_server

# 압축 해제
xz -d Armbian_*.img.xz
```

### 방법 B: Orange Pi 공식 이미지 (2순위)

1. [Orange Pi 다운로드 페이지](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-5.html) 접속
2. "Official Images" 섹션에서 다운로드
3. `Orangepi5_x.x.x_ubuntu_jammy_server_linux5.10.xxx.7z` 또는 `linux6.1.xx` 선택

```bash
mkdir -p ~/orangepi5-images
cd ~/orangepi5-images

# Orange Pi 공식 이미지 다운로드 (예시)
wget https://github.com/orangepi-xunlong/orangepi-build/releases/download/v1.0.0/Orangepi5_1.0.0_ubuntu_jammy_server_linux5.10.160.img.xz

# 압축 해제
unxz Orangepi5_*.img.xz
```

### 이미지 종류 선택 가이드

| 이미지 종류 | 용도 | 권장 상황 |
|------------|------|----------|
| **Server** | CLI 전용, 경량 | IoT/Greengrass 용도 (권장) |
| **Desktop** | GUI 포함 | 데스크톱 사용 |
| **Minimal** | 최소 설치 | 커스텀 빌드 |

> Server 이미지를 권장합니다. 불필요한 GUI 패키지 없이 메모리 효율적이며 AWS Greengrass 실행에 적합합니다.

### 이미지 선택 시 반드시 확인할 사항

```
이미지 파일명에서 커널 버전을 반드시 확인하세요:

 Orangepi5_1.0.0_ubuntu_jammy_server_linux5.10.160.img
                                       ^^^^^^^^^^
                                       BSP 커널 5.10 -> NPU 지원 O

 Orangepi5_1.0.0_ubuntu_jammy_server_linux6.1.43.img
                                       ^^^^^^^^
                                       BSP 커널 6.1 -> NPU 지원 O

 ubuntu-24.10-desktop-arm64-orangepi5.img  (Joshua Riek)
                                       -> Mainline 커널일 가능성 높음
                                       -> NPU 지원 불확실!

확인 방법: 부팅 후 uname -r 로 커널 버전 확인
  5.10.xxx-rockchip-rk3588  -> BSP 커널 (NPU O)
  6.1.xxx-rockchip-rk3588   -> BSP 커널 (NPU O)
  6.6.xxx 이상 (mainline)   -> NPU 사용 불가
```

---

## 부팅 미디어 만들기

### 방법 1: balenaEtcher 사용 (권장, GUI)

#### Windows / macOS / Linux

1. [balenaEtcher 다운로드](https://www.balena.io/etcher/)
2. 설치 및 실행
3. "Flash from file" -> 다운로드한 이미지 선택
4. "Select target" -> MicroSD 카드 선택
5. "Flash!" 클릭

```
+-------------------------------------------------------------+
|                    balenaEtcher                               |
+-------------------------------------------------------------+
|  +-----------+    +-----------+    +-----------+             |
|  |  1.       |    |  2.       |    |  3.       |             |
|  | Flash     | -> | Select    | -> | Flash!    |             |
|  | from      |    | target    |    |           |             |
|  | file      |    |           |    |           |             |
|  +-----------+    +-----------+    +-----------+             |
+-------------------------------------------------------------+
```

### 방법 2: dd 명령어 사용 (Linux/macOS CLI)

```bash
# MicroSD 카드 장치 확인
lsblk

# 예: /dev/sdb가 MicroSD인 경우
# 주의: 잘못된 장치 선택 시 데이터 손실!

# 이미지 굽기 (sudo 필요)
sudo dd if=Orangepi5_1.0.0_ubuntu_jammy_server_linux5.10.160.img of=/dev/sdb bs=4M status=progress conv=fsync

# 완료 후 sync
sync
```

### 방법 3: Raspberry Pi Imager 사용

```bash
# Ubuntu/Debian
sudo apt install rpi-imager

# 또는 공식 사이트에서 다운로드
```

1. Raspberry Pi Imager 실행
2. "CHOOSE OS" -> "Use custom" -> 이미지 파일 선택
3. "CHOOSE STORAGE" -> MicroSD 선택
4. "WRITE" 클릭

---

## 첫 부팅 및 초기 설정

### 하드웨어 연결

```
+--------------------------------------------------------------+
|                   Orange Pi 5 연결도                           |
+--------------------------------------------------------------+
|                                                                |
|    +-------------------+                                      |
|    |   HDMI 모니터     |<---- HDMI 케이블                     |
|    +-------------------+                                      |
|                                                                |
|    +-------------------+      +-------------------+           |
|    |   Orange Pi 5     |<-----|  전원 5V/4A       |           |
|    |                   |      |  USB-C             |           |
|    |  [SD카드 삽입]    |      +-------------------+           |
|    |                   |                                      |
|    |  [이더넷]---------|----------> 공유기/스위치             |
|    +-------------------+                                      |
|             |                                                 |
|             v                                                 |
|    +-------------------+                                      |
|    |   USB 키보드      | (선택)                               |
|    +-------------------+                                      |
|                                                                |
+--------------------------------------------------------------+
```

### 첫 부팅

1. MicroSD 카드를 Orange Pi 5에 삽입
2. 이더넷 케이블 연결
3. HDMI 모니터 연결 (선택)
4. 전원 연결 -> 자동 부팅

### 기본 로그인 정보

| OS | 사용자명 | 비밀번호 |
|----|---------|---------|
| **Orange Pi 공식** | `orangepi` 또는 `root` | `orangepi` |
| **Armbian** | `root` | 첫 부팅 시 설정 |

```bash
# 첫 로그인 후 비밀번호 변경 권장
passwd
```

### SSH 접속 (헤드리스 설정)

모니터 없이 설정하려면 SSH로 접속합니다.

```bash
# 1. 공유기에서 Orange Pi 5의 IP 주소 확인
# 또는 nmap으로 스캔
nmap -sn 192.168.1.0/24

# 2. SSH 접속
ssh orangepi@<IP주소>
# 예: ssh orangepi@192.168.1.100
```

### 부팅 직후 커널 버전 확인 (중요!)

```bash
# 커널 버전 확인 - NPU 사용 가능 여부 판단
uname -r

# 기대하는 결과 (둘 중 하나):
# 5.10.xxx-rockchip-rk3588    <- BSP 커널 (NPU O)
# 6.1.xxx-rockchip-rk3588     <- BSP 커널 (NPU O)

# 이런 결과가 나오면 NPU 사용 불가:
# 6.6.xxx 이상               <- Mainline 커널 (NPU X)
# 6.11.xxx                   <- Mainline 커널 (NPU X)
```

---

## 시스템 기본 설정

### 1. 시스템 업데이트

```bash
# 패키지 목록 업데이트
sudo apt update

# 시스템 업그레이드
sudo apt upgrade -y

# 재부팅 (커널 업데이트 시)
sudo reboot
```

> **주의**: `apt upgrade`로 커널이 업데이트될 경우 RKNPU 드라이버 호환성을 다시 확인하세요. Armbian의 경우 BSP 커널 트랙을 유지하므로 안전합니다.

### 2. 호스트네임 변경

```bash
# 호스트네임 변경
sudo hostnamectl set-hostname orangepi5-greengrass

# /etc/hosts 수정
sudo nano /etc/hosts
```

`/etc/hosts` 내용:
```
127.0.0.1       localhost
127.0.1.1       orangepi5-greengrass

# IPv6
::1             localhost ip6-localhost ip6-loopback
```

### 3. 타임존 설정

```bash
# 타임존 설정 (한국)
sudo timedatectl set-timezone Asia/Seoul

# 확인
timedatectl
```

### 4. 로케일 설정

```bash
# 로케일 설정
sudo dpkg-reconfigure locales

# en_US.UTF-8 과 ko_KR.UTF-8 선택
# 기본 로케일: en_US.UTF-8 권장
```

### 5. 새 사용자 생성 (선택)

```bash
# 새 사용자 생성
sudo adduser ggc_user

# sudo 권한 부여
sudo usermod -aG sudo ggc_user
```

### 6. 스왑 메모리 설정

```bash
# 현재 스왑 확인
free -h

# 스왑 파일 생성 (4GB)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 확인
free -h
```

---

## 개발 환경 구성

### 필수 패키지 설치

```bash
# 기본 개발 도구
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    tree \
    unzip \
    software-properties-common

# Python 개발 환경
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev

# Python 버전 확인
python3 --version
# Ubuntu 22.04: Python 3.10.x
# Debian 12: Python 3.11.x
```

### Python 가상환경 설정

```bash
# 프로젝트 디렉토리 생성
mkdir -p ~/greengrass-project
cd ~/greengrass-project

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 기본 패키지 설치
pip install \
    boto3 \
    awsiotsdk \
    numpy \
    opencv-python-headless \
    Pillow
```

### Java 설치 (Greengrass 요구사항)

```bash
# Java 11 설치 (Greengrass Core 요구사항)
sudo apt install -y default-jdk

# 버전 확인
java -version
```

---

## NPU 환경 설정

이 섹션이 가장 중요합니다. OS에 따라 설정 방법이 다릅니다.

### Step 1: RKNPU 커널 드라이버 확인

```bash
# RKNPU 드라이버 버전 확인
cat /sys/kernel/debug/rknpu/version

# 기대하는 결과:
# RKNPU driver: v0.9.8

# 또는 dmesg에서 확인
dmesg | grep -i rknpu
# 기대하는 결과:
# [    x.xxx] RKNPU xxx: Initialized rknpu 0.9.8 ...

# NPU 장치 파일 확인
ls -la /dev/dri/
# renderD128 이 있어야 NPU 사용 가능
```

#### 경우 A: Armbian을 사용하는 경우

Armbian BSP 이미지는 RKNPU 드라이버 v0.9.8이 기본 포함됩니다. 추가 작업 없이 Step 2로 진행하세요.

```bash
# Armbian에서 시스템 전체 업데이트 (NPU 드라이버 포함)
sudo armbian-config
# System -> System update 선택
```

#### 경우 B: Orange Pi 공식 이미지를 사용하는 경우

공식 이미지의 RKNPU 드라이버가 v0.9.8 미만이면 수동 업그레이드가 필요합니다.

**방법 1: librknnrt 런타임만 업데이트 (간편, 대부분의 경우 충분)**

```bash
# 기존 런타임 버전 확인
strings /usr/lib/librknnrt.so | grep "librknnrt version" 2>/dev/null || echo "librknnrt not found"

# 최신 런타임 다운로드
cd /tmp
git clone --depth 1 https://github.com/airockchip/rknn-toolkit2.git

# 런타임 라이브러리 복사 (aarch64)
sudo cp /tmp/rknn-toolkit2/rknpu2/runtime/Linux/librknn_api/aarch64/librknnrt.so /usr/lib/
sudo cp /tmp/rknn-toolkit2/rknpu2/runtime/Linux/librknn_api/aarch64/librknn_api.so /usr/lib/

# 라이브러리 캐시 갱신
sudo ldconfig

# 업데이트 확인
strings /usr/lib/librknnrt.so | grep "librknnrt version"
# 기대 결과: librknnrt version: 2.3.x

# 정리
rm -rf /tmp/rknn-toolkit2
```

**방법 2: RKNPU 커널 드라이버까지 업그레이드 (고급, 커널 재빌드 필요)**

이 방법은 커널 소스 컴파일이 필요하며, 20GB 이상의 디스크 공간과 상당한 빌드 시간이 소요됩니다. 방법 1로 충분하지 않은 경우에만 진행하세요.

```bash
# 현재 커널 소스가 필요 (Orange Pi build 시스템 사용)
# 참고: https://github.com/cse-repon/orangepi-5b-rknpu-0.9.8-update

# 1. 빌드 도구 설치
sudo apt install -y build-essential gcc-aarch64-linux-gnu \
    bc flex bison libssl-dev libncurses-dev

# 2. 최신 RKNPU 드라이버 소스 다운로드
git clone https://github.com/airockchip/rknn-llm.git
cd rknn-llm/rknpu-driver

# 3. 커널 소스에 드라이버 소스 교체 후 재빌드
# (상세 절차는 사용 중인 커널 빌드 시스템에 따라 다름)

# 4. 빌드된 커널 패키지 설치
# sudo dpkg -i linux-image-xxx.deb

# 5. 재부팅 후 확인
# sudo reboot
# cat /sys/kernel/debug/rknpu/version
```

#### 경우 C: Joshua Riek Ubuntu Rockchip을 사용 중인 경우

**NPU를 사용해야 한다면 OS를 Armbian 또는 Orange Pi 공식 이미지로 교체하는 것을 권장합니다.**

이유:
- Joshua Riek 프로젝트는 NPU 지원에 대한 업데이트 계획이 없음 (NOT_PLANNED)
- Mainline 커널 이미지(24.10+)는 RKNPU 드라이버를 포함하지 않음
- BSP 커널 이미지(22.04, 24.04)도 드라이버 버전이 오래되어 있을 수 있음

만약 Joshua Riek 이미지를 유지해야 한다면:
```bash
# 1. 먼저 커널이 BSP인지 확인
uname -r
# 5.10.x-rockchip 또는 6.1.x-rockchip이어야 함
# mainline 6.6+ 이면 NPU 사용 불가 -> OS 교체 필요

# 2. BSP 커널이라면, 런타임 라이브러리만 수동 업데이트 시도
# (위의 "방법 1: librknnrt 런타임만 업데이트" 참조)

# 3. RKNPU 드라이버 확인
cat /sys/kernel/debug/rknpu/version
# 파일이 없거나 v0.9.2 이하면 커널 드라이버도 업데이트 필요
# -> 이 경우 OS 교체가 더 간편함
```

### Step 2: rknn-toolkit-lite2 설치 (보드에서 Python 추론)

```bash
# 가상환경 활성화 (아직 안 했다면)
source ~/greengrass-project/venv/bin/activate

# 방법 1: pip으로 설치 (v2.3.0+ 부터 지원, 권장)
pip install rknn-toolkit-lite2

# 설치 확인
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite OK'); print(f'Version: {RKNNLite.__version__}' if hasattr(RKNNLite, '__version__') else '')"
```

만약 pip 설치가 실패하는 경우 (구버전 또는 네트워크 문제):

```bash
# 방법 2: GitHub에서 wheel 직접 설치
cd /tmp
git clone --depth 1 https://github.com/airockchip/rknn-toolkit2.git

# Python 버전에 맞는 wheel 설치
# Python 3.10 (Ubuntu 22.04)
pip install /tmp/rknn-toolkit2/rknn_toolkit_lite2/packages/rknn_toolkit_lite2-*-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

# Python 3.11 (Debian 12)
pip install /tmp/rknn-toolkit2/rknn_toolkit_lite2/packages/rknn_toolkit_lite2-*-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

# Python 3.12 (Ubuntu 24.04)
pip install /tmp/rknn-toolkit2/rknn_toolkit_lite2/packages/rknn_toolkit_lite2-*-cp312-cp312-manylinux_2_17_aarch64.manylinux2014_aarch64.whl

# 설치 확인
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite OK')"

# 정리
rm -rf /tmp/rknn-toolkit2
```

### Step 3: 시스템 종속 라이브러리 설치

```bash
# NPU 관련 시스템 라이브러리
sudo apt install -y \
    libopencv-dev \
    libdrm-dev \
    librga-dev \
    libjpeg-dev \
    libpng-dev

# Python OpenCV (headless - 서버용)
pip install opencv-python-headless numpy
```

### Step 4: 권한 설정

```bash
# NPU 장치 접근 권한
sudo usermod -aG video $USER
sudo usermod -aG render $USER

# 재로그인 필요
exit
# 다시 SSH 접속
```

### Step 5: PC에서 rknn-toolkit2 설치 (모델 변환용, 선택)

PC(x86_64)에서 모델을 RKNN 형식으로 변환할 때 필요합니다.

```bash
# PC (x86_64, Ubuntu 22.04/24.04)에서 실행
pip install rknn-toolkit2

# 설치 확인
python3 -c "from rknn.api import RKNN; print('RKNN Toolkit2 OK')"
```

---

## NPU 동작 검증

### 전체 NPU 스택 검증 스크립트

아래 스크립트를 Orange Pi 5에서 실행하여 NPU 환경을 종합 검증합니다.

```bash
#!/bin/bash
echo "=========================================="
echo "  Orange Pi 5 NPU 환경 검증"
echo "=========================================="

echo ""
echo "[1/7] 커널 버전 확인"
echo "  커널: $(uname -r)"
KERNEL=$(uname -r)
if echo "$KERNEL" | grep -q "rockchip"; then
    echo "  상태: BSP 커널 (NPU 지원 O)"
else
    echo "  상태: WARNING - BSP 커널이 아닐 수 있음 (NPU 미지원 가능)"
fi

echo ""
echo "[2/7] RKNPU 커널 드라이버 확인"
if [ -f /sys/kernel/debug/rknpu/version ]; then
    echo "  드라이버: $(cat /sys/kernel/debug/rknpu/version)"
else
    echo "  상태: WARNING - RKNPU 드라이버를 찾을 수 없음"
    echo "  -> debugfs 마운트 확인: mount -t debugfs debugfs /sys/kernel/debug"
    echo "  -> 또는 dmesg에서 확인: dmesg | grep rknpu"
fi

echo ""
echo "[3/7] NPU 장치 파일 확인"
if [ -e /dev/dri/renderD128 ]; then
    echo "  /dev/dri/renderD128: 존재 (NPU 접근 가능)"
    ls -la /dev/dri/renderD128
else
    echo "  상태: WARNING - /dev/dri/renderD128 없음"
fi

echo ""
echo "[4/7] librknnrt 런타임 확인"
if [ -f /usr/lib/librknnrt.so ]; then
    VERSION=$(strings /usr/lib/librknnrt.so | grep "librknnrt version" | head -1)
    echo "  $VERSION"
else
    echo "  상태: WARNING - librknnrt.so 없음"
    echo "  -> 런타임 라이브러리 설치 필요"
fi

echo ""
echo "[5/7] Python 버전 확인"
echo "  Python: $(python3 --version 2>&1)"

echo ""
echo "[6/7] rknn-toolkit-lite2 확인"
python3 -c "
try:
    from rknnlite.api import RKNNLite
    print('  rknn-toolkit-lite2: 설치됨')
    try:
        import importlib.metadata
        ver = importlib.metadata.version('rknn-toolkit-lite2')
        print(f'  버전: {ver}')
    except:
        print('  버전: 확인 불가')
except ImportError as e:
    print(f'  상태: WARNING - rknn-toolkit-lite2 미설치')
    print(f'  오류: {e}')
" 2>&1

echo ""
echo "[7/7] NPU 부하 확인"
if [ -f /sys/kernel/debug/rknpu/load ]; then
    echo "  NPU 부하: $(cat /sys/kernel/debug/rknpu/load)"
else
    echo "  NPU 부하 모니터링 불가 (debugfs 미마운트)"
fi

echo ""
echo "=========================================="
echo "  검증 완료"
echo "=========================================="
```

위 스크립트를 저장하고 실행:

```bash
chmod +x npu_check.sh
./npu_check.sh
```

### RKNN 추론 테스트

```bash
# 예제 다운로드 및 테스트
cd /tmp
git clone --depth 1 https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2/rknn_toolkit_lite2/examples/inference_with_lite

# 가상환경 활성화 후 실행
source ~/greengrass-project/venv/bin/activate
python3 test.py

# 정상 결과: 모델 로드 -> 추론 -> 결과 출력
```

### 기대하는 정상 검증 결과

```
==========================================
  Orange Pi 5 NPU 환경 검증
==========================================

[1/7] 커널 버전 확인
  커널: 6.1.43-rockchip-rk3588
  상태: BSP 커널 (NPU 지원 O)

[2/7] RKNPU 커널 드라이버 확인
  드라이버: RKNPU driver: v0.9.8

[3/7] NPU 장치 파일 확인
  /dev/dri/renderD128: 존재 (NPU 접근 가능)

[4/7] librknnrt 런타임 확인
  librknnrt version: 2.3.0 (또는 2.3.2)

[5/7] Python 버전 확인
  Python: Python 3.10.12

[6/7] rknn-toolkit-lite2 확인
  rknn-toolkit-lite2: 설치됨
  버전: 2.3.0

[7/7] NPU 부하 확인
  NPU 부하: 0%

==========================================
  검증 완료
==========================================
```

---

## 네트워크 설정

### 고정 IP 설정 (선택)

#### NetworkManager 사용 (권장)

```bash
# 현재 연결 확인
nmcli connection show

# 고정 IP 설정 (예: eth0)
sudo nmcli connection modify "Wired connection 1" \
    ipv4.method manual \
    ipv4.addresses 192.168.1.100/24 \
    ipv4.gateway 192.168.1.1 \
    ipv4.dns "8.8.8.8,8.8.4.4"

# 연결 재시작
sudo nmcli connection down "Wired connection 1"
sudo nmcli connection up "Wired connection 1"
```

#### /etc/network/interfaces 사용

```bash
sudo nano /etc/network/interfaces
```

```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8 8.8.4.4
```

### WiFi 설정 (WiFi 모듈 장착 시)

```bash
# WiFi 네트워크 스캔
sudo nmcli device wifi list

# WiFi 연결
sudo nmcli device wifi connect "SSID이름" password "비밀번호"

# 연결 확인
nmcli connection show
```

### 방화벽 설정

```bash
# ufw 설치
sudo apt install -y ufw

# 기본 정책
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 허용
sudo ufw allow ssh

# Greengrass 관련 포트 (MQTT)
sudo ufw allow 8883/tcp
sudo ufw allow 443/tcp

# 방화벽 활성화
sudo ufw enable

# 상태 확인
sudo ufw status
```

---

## 문제 해결

### NPU 관련 문제

#### 1. "Invalid RKNN model version" 오류

```
증상: E RKNN: Invalid RKNN model version 6
      rknn_init, load model failed!

원인: 모델을 변환한 rknn-toolkit2 버전(신버전)과
      보드의 librknnrt 버전(구버전)이 불일치

해결:
1. librknnrt.so를 최신 버전으로 업데이트
   -> "NPU 환경 설정 > Step 1 > 방법 1" 참조
2. 또는 모델을 보드의 런타임 버전에 맞게 재변환
   -> PC에서 보드와 동일한 버전의 rknn-toolkit2로 모델 변환
```

#### 2. "failed to open rknpu module" 오류

```
증상: E RKNN: failed to open rknpu module
      E RKNN: failed to open rknn device!

원인: RKNPU 커널 드라이버가 로드되지 않음

해결:
1. 커널이 BSP인지 확인: uname -r
   -> rockchip이 포함되어야 함
   -> Mainline 커널이면 OS 교체 필요

2. 드라이버 로드 확인:
   dmesg | grep rknpu
   lsmod | grep rknpu

3. debugfs 마운트:
   sudo mount -t debugfs debugfs /sys/kernel/debug
   cat /sys/kernel/debug/rknpu/version

4. 장치 파일 확인:
   ls -la /dev/dri/renderD128
```

#### 3. Spinlock 커널 크래시 (멀티스레드 NPU)

```
증상: BUG: spinlock recursion on CPU#0
      (멀티스레드에서 NPU 자동 코어 배정 시)

원인: RKNPU 드라이버 v0.9.2의 알려진 버그

해결:
1. 드라이버를 v0.9.8로 업그레이드 (근본 해결)
2. 임시 해결: 단일 NPU 코어만 사용
   rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
   # NPU_CORE_0_1_2 대신 NPU_CORE_0 사용
```

#### 4. NPU 인식 안됨

```bash
# 증상: RKNN 초기화 실패, /dev/dri/renderD128 없음

# 확인사항
ls -la /dev/dri/
# renderD128이 없으면 드라이버 문제

# BSP 커널인지 확인
uname -r
# rockchip이 포함되어 있는지 확인

# 드라이버 로드 상태
dmesg | grep rknpu

# Armbian의 경우 시스템 업데이트로 해결 가능
sudo armbian-config
# System -> System update

# 그 외의 경우 OS 재설치 고려 (Armbian BSP 권장)
```

#### 5. Python import 오류

```
증상: ModuleNotFoundError: No module named 'rknnlite'

해결:
1. 가상환경이 활성화되어 있는지 확인:
   which python3  # 가상환경 경로여야 함

2. Python 버전 확인:
   python3 --version
   # rknn-toolkit-lite2는 Python 3.7-3.12 지원

3. 재설치:
   pip install rknn-toolkit-lite2

4. 아키텍처 확인 (반드시 aarch64):
   uname -m  # aarch64 이어야 함
```

### 일반적인 문제

#### 6. 부팅 안됨

```
증상: 전원 LED만 켜지고 화면 출력 없음

해결:
- SD카드가 제대로 삽입되었는지 확인
- SD카드를 다른 리더기로 다시 굽기
- 전원 어댑터가 5V/4A 이상인지 확인
- HDMI 케이블 교체 시도
```

#### 7. SSH 접속 불가

```
증상: Connection refused 또는 timeout

해결:
- Orange Pi와 PC가 같은 네트워크인지 확인
- IP 주소가 올바른지 확인 (공유기 DHCP 목록 확인)
- 방화벽 설정 확인
- SSH 서비스 상태: sudo systemctl status ssh
```

#### 8. 발열 문제

```bash
# 현재 온도 확인
cat /sys/class/thermal/thermal_zone0/temp
# 결과를 1000으로 나누면 섭씨 온도

# 온도 모니터링 스크립트
watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp'

# 해결책:
# - 방열판 부착
# - 쿨링 팬 설치
# - 케이스 통풍 확인
```

#### 9. 저장공간 부족

```bash
# 디스크 사용량 확인
df -h

# SD카드 파티션 확장
# Orange Pi 공식 이미지:
sudo orangepi-config
# System -> Resize filesystem

# Armbian:
sudo armbian-config
# System -> Resize filesystem

# 또는 수동으로
sudo resize2fs /dev/mmcblk0p2
```

### 시스템 정보 확인 명령어

```bash
# CPU 정보
lscpu

# 메모리 정보
free -h

# 저장장치 정보
lsblk

# 네트워크 정보
ip addr

# 커널 버전
uname -r

# RKNPU 드라이버 버전
cat /sys/kernel/debug/rknpu/version

# NPU 부하
cat /sys/kernel/debug/rknpu/load

# 시스템 로그
sudo journalctl -xe

# 부팅 로그
dmesg | tail -50
```

---

## 설정 완료 체크리스트

```
OS 및 기본 설정
  [ ] OS 이미지 굽기 완료 (BSP 커널 확인!)
  [ ] 첫 부팅 성공
  [ ] SSH 접속 가능
  [ ] 시스템 업데이트 완료
  [ ] 호스트네임 설정
  [ ] 타임존 설정 (Asia/Seoul)

개발 환경
  [ ] Python 3.10+ 설치 확인
  [ ] Java 11 설치
  [ ] 가상환경 생성 및 기본 패키지 설치

NPU 환경 (모두 통과해야 NPU 사용 가능)
  [ ] 커널이 BSP (5.10.x 또는 6.1.x rockchip)
  [ ] RKNPU 드라이버 v0.9.6 이상 (v0.9.8 권장)
  [ ] librknnrt.so v2.3.0 이상 설치
  [ ] rknn-toolkit-lite2 설치 확인
  [ ] /dev/dri/renderD128 존재 확인
  [ ] video, render 그룹 권한 설정
  [ ] NPU 검증 스크립트 통과
  [ ] RKNN 추론 테스트 성공

네트워크
  [ ] 네트워크 설정 완료
  [ ] 방화벽 설정
```

---

## 다음 단계

Orange Pi 5의 OS 설치와 NPU 환경 설정이 완료되었습니다. 다음 문서에서는 AWS IoT Greengrass에 대해 알아보고 설치를 준비합니다.

-> [03. AWS Greengrass 소개](./03-aws-greengrass-introduction.md)

---

## 참고 자료

- [Orange Pi 5 사용자 매뉴얼](http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_5)
- [RKNN Toolkit2 GitHub (airockchip, 최신)](https://github.com/airockchip/rknn-toolkit2)
- [RKNN Toolkit2 릴리스](https://github.com/airockchip/rknn-toolkit2/releases)
- [RKNN Model Zoo](https://github.com/airockchip/rknn_model_zoo)
- [rknn-toolkit-lite2 (PyPI)](https://pypi.org/project/rknn-toolkit-lite2/)
- [rknn-toolkit2 (PyPI)](https://pypi.org/project/rknn-toolkit2/)
- [Armbian Orange Pi 5](https://www.armbian.com/orangepi-5/)
- [Joshua Riek Ubuntu Rockchip (참고)](https://github.com/Joshua-Riek/ubuntu-rockchip)
- [RKNPU 드라이버 업그레이드 가이드](https://github.com/cse-repon/orangepi-5b-rknpu-0.9.8-update)
- [ezrknpu - Easy RKNPU 설정](https://github.com/Pelochus/ezrknpu)
- [Debian 공식 문서](https://www.debian.org/doc/)
