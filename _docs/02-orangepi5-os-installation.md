# Orange Pi 5 OS 설치 및 기본 설정

## 목차
1. [준비물](#준비물)
2. [OS 이미지 다운로드](#os-이미지-다운로드)
3. [부팅 미디어 만들기](#부팅-미디어-만들기)
4. [첫 부팅 및 초기 설정](#첫-부팅-및-초기-설정)
5. [시스템 기본 설정](#시스템-기본-설정)
6. [개발 환경 구성](#개발-환경-구성)
7. [NPU 환경 설정](#npu-환경-설정)
8. [네트워크 설정](#네트워크-설정)
9. [문제 해결](#문제-해결)

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

### 권장 OS: Debian 12 (Bookworm) 또는 Ubuntu 22.04

이 튜토리얼에서는 **Debian 12**를 기준으로 진행합니다.

### 다운로드 방법

#### 방법 1: 공식 Orange Pi 사이트

1. [Orange Pi 다운로드 페이지](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-5.html) 접속
2. "Official Images" 섹션에서 다운로드
3. `Orangepi5_x.x.x_debian_bookworm_server_linux6.1.xx.7z` 선택

#### 방법 2: 직접 다운로드 (명령줄)

```bash
# 작업 디렉토리 생성
mkdir -p ~/orangepi5-images
cd ~/orangepi5-images

# 이미지 다운로드 (예시 URL - 실제 최신 버전 확인 필요)
wget https://github.com/orangepi-xunlong/orangepi-build/releases/download/v1.0.0/Orangepi5_1.0.0_debian_bookworm_server_linux6.1.43.img.xz

# 압축 해제
unxz Orangepi5_1.0.0_debian_bookworm_server_linux6.1.43.img.xz
```

### 이미지 종류 선택 가이드

| 이미지 종류 | 용도 | 권장 상황 |
|------------|------|----------|
| **Server** | CLI 전용, 경량 | ✅ IoT/Greengrass 용도 |
| **Desktop** | GUI 포함 | 데스크톱 사용 |
| **Minimal** | 최소 설치 | 커스텀 빌드 |

```
💡 이 튜토리얼에서는 Server 이미지를 권장합니다.
   - 불필요한 GUI 패키지 없음
   - 메모리 효율적
   - AWS Greengrass 실행에 적합
```

---

## 부팅 미디어 만들기

### 방법 1: balenaEtcher 사용 (권장, GUI)

#### Windows / macOS / Linux

1. [balenaEtcher 다운로드](https://www.balena.io/etcher/)
2. 설치 및 실행
3. "Flash from file" → 다운로드한 이미지 선택
4. "Select target" → MicroSD 카드 선택
5. "Flash!" 클릭

```
┌─────────────────────────────────────────────────────────┐
│                    balenaEtcher                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │  1️⃣    │    │  2️⃣    │    │  3️⃣    │            │
│  │ Flash   │ ─▶ │ Select  │ ─▶ │ Flash!  │            │
│  │ from    │    │ target  │    │         │            │
│  │ file    │    │         │    │         │            │
│  └─────────┘    └─────────┘    └─────────┘            │
└─────────────────────────────────────────────────────────┘
```

### 방법 2: dd 명령어 사용 (Linux/macOS CLI)

```bash
# MicroSD 카드 장치 확인
lsblk

# 예: /dev/sdb가 MicroSD인 경우
# ⚠️ 주의: 잘못된 장치 선택 시 데이터 손실!

# 이미지 굽기 (sudo 필요)
sudo dd if=Orangepi5_1.0.0_debian_bookworm_server_linux6.1.43.img of=/dev/sdb bs=4M status=progress conv=fsync

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
2. "CHOOSE OS" → "Use custom" → 이미지 파일 선택
3. "CHOOSE STORAGE" → MicroSD 선택
4. "WRITE" 클릭

---

## 첫 부팅 및 초기 설정

### 하드웨어 연결

```
┌──────────────────────────────────────────────────────────┐
│                   Orange Pi 5 연결도                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    ┌─────────────────┐                                  │
│    │   HDMI 모니터   │◀──── HDMI 케이블                 │
│    └─────────────────┘                                  │
│                                                          │
│    ┌─────────────────┐      ┌─────────────────┐        │
│    │   Orange Pi 5   │◀─────│  전원 5V/4A    │        │
│    │                 │      │  USB-C          │        │
│    │  [SD카드 삽입]  │      └─────────────────┘        │
│    │                 │                                  │
│    │  [이더넷]───────│──────▶ 공유기/스위치            │
│    └─────────────────┘                                  │
│             │                                           │
│             ▼                                           │
│    ┌─────────────────┐                                  │
│    │   USB 키보드    │ (선택)                           │
│    └─────────────────┘                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 첫 부팅

1. MicroSD 카드를 Orange Pi 5에 삽입
2. 이더넷 케이블 연결
3. HDMI 모니터 연결 (선택)
4. 전원 연결 → 자동 부팅

### 기본 로그인 정보

| 항목 | 값 |
|------|-----|
| **사용자명** | `orangepi` 또는 `root` |
| **비밀번호** | `orangepi` |

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

# 비밀번호: orangepi
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
# Python 3.11.x 이상 권장
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

### RKNN (Rockchip Neural Network) 환경 구성

Orange Pi 5의 NPU를 사용하려면 RKNN 관련 라이브러리를 설치해야 합니다.

### 1. 시스템 종속성 설치

```bash
# 필수 라이브러리
sudo apt install -y \
    libopencv-dev \
    libdrm-dev \
    librga-dev \
    libjpeg-dev \
    libpng-dev
```

### 2. RKNN Lite 런타임 설치

```bash
# 작업 디렉토리
cd ~

# RKNN Toolkit Lite 다운로드
git clone https://github.com/rockchip-linux/rknn-toolkit2.git
cd rknn-toolkit2

# rknn_toolkit_lite2 설치 (Orange Pi 5용)
cd rknn_toolkit_lite2/packages
pip install rknn_toolkit_lite2-*-cp311-cp311-linux_aarch64.whl

# 설치 확인
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite OK')"
```

### 3. RKNPU2 드라이버 확인

```bash
# NPU 드라이버 확인
ls /dev/dri/
# renderD128, renderD129 등이 보여야 함

# NPU 상태 확인
cat /sys/kernel/debug/rknpu/version
```

### 4. 권한 설정

```bash
# NPU 장치 접근 권한
sudo usermod -aG video $USER
sudo usermod -aG render $USER

# 재로그인 필요
exit
# 다시 SSH 접속
```

### NPU 동작 테스트

```bash
cd ~/rknn-toolkit2/rknn_toolkit_lite2/examples/inference_with_lite
python3 test.py
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

### 자주 발생하는 문제

#### 1. 부팅 안됨

```
증상: 전원 LED만 켜지고 화면 출력 없음

해결:
□ SD카드가 제대로 삽입되었는지 확인
□ SD카드를 다른 리더기로 다시 굽기
□ 전원 어댑터가 5V/4A 이상인지 확인
□ HDMI 케이블 교체 시도
```

#### 2. SSH 접속 불가

```
증상: Connection refused 또는 timeout

해결:
□ Orange Pi와 PC가 같은 네트워크인지 확인
□ IP 주소가 올바른지 확인 (공유기 DHCP 목록 확인)
□ 방화벽 설정 확인
□ SSH 서비스 상태: sudo systemctl status ssh
```

#### 3. NPU 인식 안됨

```bash
# 증상: RKNN 초기화 실패

# 확인사항
ls -la /dev/dri/
# renderD128이 없으면 드라이버 문제

# 해결
sudo apt update
sudo apt install -y rockchip-multimedia-config
sudo reboot
```

#### 4. 발열 문제

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

#### 5. 저장공간 부족

```bash
# 디스크 사용량 확인
df -h

# SD카드 파티션 확장
sudo orangepi-config
# System → Resize filesystem

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

# 시스템 로그
sudo journalctl -xe

# 부팅 로그
dmesg | tail -50
```

---

## 설정 완료 체크리스트

```
✅ 시스템 설정 체크리스트

□ OS 이미지 굽기 완료
□ 첫 부팅 성공
□ SSH 접속 가능
□ 시스템 업데이트 완료
□ 호스트네임 설정
□ 타임존 설정 (Asia/Seoul)
□ Python 3.11+ 설치
□ Java 11 설치
□ RKNN Lite 설치
□ NPU 동작 확인
□ 네트워크 설정 완료
□ 방화벽 설정
```

---

## 다음 단계

Orange Pi 5의 기본 설정이 완료되었습니다. 다음 문서에서는 AWS IoT Greengrass에 대해 알아보고 설치를 준비합니다.

➡️ [03. AWS Greengrass 소개](./03-aws-greengrass-introduction.md)

---

## 참고 자료

- [Orange Pi 5 사용자 매뉴얼](http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_5)
- [Debian 공식 문서](https://www.debian.org/doc/)
- [RKNN Toolkit2 GitHub](https://github.com/rockchip-linux/rknn-toolkit2)
