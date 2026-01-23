# Orange Pi 5에 AWS IoT Greengrass 설치

## 목차
1. [사전 준비](#사전-준비)
2. [AWS 콘솔에서 IoT Thing 생성](#aws-콘솔에서-iot-thing-생성)
3. [Greengrass Core 설치](#greengrass-core-설치)
4. [자동 프로비저닝으로 설치](#자동-프로비저닝으로-설치)
5. [수동 프로비저닝으로 설치](#수동-프로비저닝으로-설치)
6. [Greengrass 서비스 관리](#greengrass-서비스-관리)
7. [설치 확인 및 테스트](#설치-확인-및-테스트)
8. [첫 번째 컴포넌트 배포](#첫-번째-컴포넌트-배포)
9. [문제 해결](#문제-해결)

---

## 사전 준비

### Orange Pi 5 준비 상태 확인

```bash
# 1. 시스템 정보 확인
uname -a
# Linux orangepi5-greengrass 6.1.x aarch64

# 2. Python 버전 확인
python3 --version
# Python 3.11.x 이상

# 3. Java 버전 확인
java -version
# openjdk version "11.x.x"

# 4. 네트워크 연결 확인
ping -c 3 google.com

# 5. 시간 동기화 확인 (중요!)
timedatectl
# System clock synchronized: yes
```

### 시간 동기화 설정

AWS 인증에 시간 동기화가 중요합니다.

```bash
# NTP 설치 및 활성화
sudo apt install -y systemd-timesyncd
sudo timedatectl set-ntp true

# 동기화 상태 확인
timedatectl status
```

### 필수 패키지 설치

```bash
# 필수 패키지
sudo apt update
sudo apt install -y \
    curl \
    unzip \
    default-jdk \
    python3 \
    python3-pip \
    sudo
```

### AWS CLI 설치 및 구성

```bash
# AWS CLI v2 설치 (aarch64)
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 설치 확인
aws --version
# aws-cli/2.x.x Python/3.x.x Linux/aarch64

# AWS 자격 증명 구성
aws configure
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Configure 입력 값                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  AWS Access Key ID [None]: AKIA************                    │
│  AWS Secret Access Key [None]: ********                        │
│  Default region name [None]: ap-northeast-2                    │
│  Default output format [None]: json                            │
│                                                                 │
│  💡 ap-northeast-2 = 서울 리전                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 자격 증명 확인
aws sts get-caller-identity
```

---

## AWS 콘솔에서 IoT Thing 생성

### 방법 1: AWS 콘솔 (GUI)

1. [AWS IoT Console](https://console.aws.amazon.com/iot) 접속
2. **Greengrass devices** → **Core devices** 클릭
3. **Set up one core device** 클릭

```
┌─────────────────────────────────────────────────────────────────┐
│                  Step 1: Core device name                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Core device name: orangepi5-core-001                          │
│                                                                 │
│  Thing group (optional): orangepi-devices                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  Step 2: Installation method                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ○ Enter AWS credentials directly                              │
│  ● Generate a token for automatic provisioning                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 방법 2: AWS CLI (권장)

```bash
# IoT Thing 생성
aws iot create-thing \
    --thing-name "orangepi5-core-001"

# Thing Group 생성 (선택)
aws iot create-thing-group \
    --thing-group-name "orangepi-devices"

# Thing을 그룹에 추가
aws iot add-thing-to-thing-group \
    --thing-group-name "orangepi-devices" \
    --thing-name "orangepi5-core-001"
```

---

## Greengrass Core 설치

### 설치 방법 선택

| 방법 | 장점 | 단점 | 권장 상황 |
|------|------|------|----------|
| **자동 프로비저닝** | 간단, 빠름 | 일회성 토큰 필요 | 테스트, 소수 디바이스 |
| **수동 프로비저닝** | 세밀한 제어 | 복잡함 | 대규모 배포, 보안 중시 |

---

## 자동 프로비저닝으로 설치

### Step 1: 설치 스크립트 다운로드

```bash
# Greengrass Core 소프트웨어 다운로드
cd /tmp
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller
```

### Step 2: 설치 실행

```bash
# 환경 변수 설정
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_KEY"

# 설치 실행
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
    -jar /tmp/GreengrassInstaller/lib/Greengrass.jar \
    --aws-region ap-northeast-2 \
    --thing-name orangepi5-core-001 \
    --thing-group-name orangepi-devices \
    --thing-policy-name GreengrassV2IoTThingPolicy \
    --tes-role-name GreengrassV2TokenExchangeRole \
    --tes-role-alias-name GreengrassCoreTokenExchangeRoleAlias \
    --component-default-user ggc_user:ggc_group \
    --provision true \
    --setup-system-service true
```

### Step 3: 설치 확인

```bash
# 서비스 상태 확인
sudo systemctl status greengrass

# 로그 확인
sudo tail -f /greengrass/v2/logs/greengrass.log
```

---

## 수동 프로비저닝으로 설치

### Step 1: 인증서 및 키 생성

```bash
# 작업 디렉토리 생성
mkdir -p ~/greengrass-certs
cd ~/greengrass-certs

# 키 및 인증서 생성
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile device.pem.crt \
    --public-key-outfile public.pem.key \
    --private-key-outfile private.pem.key

# 출력에서 certificateArn 저장
# 예: arn:aws:iot:ap-northeast-2:123456789012:cert/abc123...
```

### Step 2: IoT 정책 생성 및 연결

```bash
# IoT 정책 생성
cat > greengrass-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Subscribe",
        "iot:Receive",
        "iot:Connect",
        "greengrass:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iot create-policy \
    --policy-name GreengrassV2IoTThingPolicy \
    --policy-document file://greengrass-policy.json

# 정책을 인증서에 연결 (certificateArn 사용)
aws iot attach-policy \
    --policy-name GreengrassV2IoTThingPolicy \
    --target "arn:aws:iot:ap-northeast-2:ACCOUNT_ID:cert/CERT_ID"

# 인증서를 Thing에 연결
aws iot attach-thing-principal \
    --thing-name orangepi5-core-001 \
    --principal "arn:aws:iot:ap-northeast-2:ACCOUNT_ID:cert/CERT_ID"
```

### Step 3: IAM 역할 생성

```bash
# Trust Policy
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "credentials.iot.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# IAM 역할 생성
aws iam create-role \
    --role-name GreengrassV2TokenExchangeRole \
    --assume-role-policy-document file://trust-policy.json

# 정책 연결
aws iam attach-role-policy \
    --role-name GreengrassV2TokenExchangeRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Role Alias 생성
aws iot create-role-alias \
    --role-alias GreengrassCoreTokenExchangeRoleAlias \
    --role-arn arn:aws:iam::ACCOUNT_ID:role/GreengrassV2TokenExchangeRole
```

### Step 4: 루트 CA 다운로드

```bash
cd ~/greengrass-certs
curl -o AmazonRootCA1.pem \
    https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

### Step 5: 인증서 배치

```bash
# Greengrass 디렉토리 생성
sudo mkdir -p /greengrass/v2/certs

# 인증서 복사
sudo cp ~/greengrass-certs/device.pem.crt /greengrass/v2/certs/
sudo cp ~/greengrass-certs/private.pem.key /greengrass/v2/certs/
sudo cp ~/greengrass-certs/AmazonRootCA1.pem /greengrass/v2/certs/

# 권한 설정
sudo chmod 644 /greengrass/v2/certs/*
sudo chmod 600 /greengrass/v2/certs/private.pem.key
```

### Step 6: 설정 파일 생성

```bash
# IoT 엔드포인트 확인
IOT_ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS --query 'endpointAddress' --output text)
echo "IoT Endpoint: $IOT_ENDPOINT"

# config.yaml 생성
sudo mkdir -p /greengrass/v2/config

sudo tee /greengrass/v2/config/config.yaml << EOF
---
system:
  certificateFilePath: "/greengrass/v2/certs/device.pem.crt"
  privateKeyPath: "/greengrass/v2/certs/private.pem.key"
  rootCaPath: "/greengrass/v2/certs/AmazonRootCA1.pem"
  rootpath: "/greengrass/v2"
  thingName: "orangepi5-core-001"
services:
  aws.greengrass.Nucleus:
    componentType: "NUCLEUS"
    version: "2.12.0"
    configuration:
      awsRegion: "ap-northeast-2"
      iotRoleAlias: "GreengrassCoreTokenExchangeRoleAlias"
      iotDataEndpoint: "$IOT_ENDPOINT"
      iotCredEndpoint: "$(echo $IOT_ENDPOINT | sed 's/data/credentials/')"
EOF
```

### Step 7: Greengrass 설치

```bash
cd /tmp
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip -o greengrass-nucleus-latest.zip -d GreengrassInstaller

sudo java -Droot="/greengrass/v2" \
    -jar /tmp/GreengrassInstaller/lib/Greengrass.jar \
    --init-config /greengrass/v2/config/config.yaml \
    --component-default-user ggc_user:ggc_group \
    --setup-system-service true
```

---

## Greengrass 서비스 관리

### 서비스 상태 확인

```bash
# 서비스 상태
sudo systemctl status greengrass

# 실행 중인 프로세스 확인
ps aux | grep greengrass
```

### 서비스 제어

```bash
# 시작
sudo systemctl start greengrass

# 중지
sudo systemctl stop greengrass

# 재시작
sudo systemctl restart greengrass

# 부팅 시 자동 시작 활성화
sudo systemctl enable greengrass

# 부팅 시 자동 시작 비활성화
sudo systemctl disable greengrass
```

### 로그 확인

```bash
# 메인 로그
sudo tail -f /greengrass/v2/logs/greengrass.log

# 특정 컴포넌트 로그
sudo tail -f /greengrass/v2/logs/com.example.MyComponent.log

# journalctl 사용
sudo journalctl -u greengrass -f
```

---

## 설치 확인 및 테스트

### AWS 콘솔에서 확인

1. [AWS IoT Greengrass Console](https://console.aws.amazon.com/greengrass) 접속
2. **Core devices** 클릭
3. `orangepi5-core-001` 상태 확인: **Healthy** 표시

```
┌─────────────────────────────────────────────────────────────────┐
│                    Core Device Status                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Name: orangepi5-core-001                                      │
│  Status: ● Healthy                                             │
│  Last status update: 2024-01-15 10:30:00 KST                   │
│                                                                 │
│  Installed components:                                          │
│  • aws.greengrass.Nucleus (2.12.0)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### CLI로 확인

```bash
# Greengrass CLI 설치 (선택)
sudo /greengrass/v2/bin/greengrass-cli component list

# 현재 설치된 컴포넌트 확인
# 출력 예:
# Component Name: aws.greengrass.Nucleus
# Version: 2.12.0
# State: RUNNING
```

### 연결 테스트

```bash
# AWS IoT Core 연결 테스트
aws iot describe-thing --thing-name orangepi5-core-001

# 응답 예:
# {
#     "thingName": "orangepi5-core-001",
#     "thingArn": "arn:aws:iot:ap-northeast-2:...",
#     ...
# }
```

---

## 첫 번째 컴포넌트 배포

### Hello World 컴포넌트 만들기

#### Step 1: 컴포넌트 코드 작성

```bash
# 로컬 컴포넌트 디렉토리 생성
mkdir -p ~/greengrass-components/com.example.HelloWorld
cd ~/greengrass-components/com.example.HelloWorld
```

```bash
# main.py 작성
cat > main.py << 'EOF'
#!/usr/bin/env python3
import time
import datetime

def main():
    while True:
        now = datetime.datetime.now()
        print(f"[{now}] Hello from Orange Pi 5 Greengrass!")
        time.sleep(10)

if __name__ == "__main__":
    main()
EOF

chmod +x main.py
```

#### Step 2: 레시피 파일 작성

```bash
# recipe.yaml 작성
cat > recipe.yaml << 'EOF'
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.HelloWorld
ComponentVersion: '1.0.0'
ComponentDescription: Hello World component for Orange Pi 5
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    message: "Hello from Orange Pi 5!"
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: |
        chmod +x {artifacts:path}/main.py
      Run: |
        python3 {artifacts:path}/main.py
    Artifacts:
      - URI: file://{artifacts:path}/main.py
EOF
```

#### Step 3: 로컬 배포

```bash
# Greengrass CLI로 로컬 배포
sudo /greengrass/v2/bin/greengrass-cli deployment create \
    --recipeDir ~/greengrass-components/com.example.HelloWorld \
    --artifactDir ~/greengrass-components/com.example.HelloWorld \
    --merge "com.example.HelloWorld=1.0.0"
```

#### Step 4: 배포 확인

```bash
# 컴포넌트 상태 확인
sudo /greengrass/v2/bin/greengrass-cli component list

# 컴포넌트 로그 확인
sudo tail -f /greengrass/v2/logs/com.example.HelloWorld.log
```

### AWS 콘솔에서 배포

#### Step 1: S3에 아티팩트 업로드

```bash
# S3 버킷 생성
aws s3 mb s3://orangepi5-greengrass-artifacts-$(aws sts get-caller-identity --query Account --output text)

# 아티팩트 업로드
aws s3 cp ~/greengrass-components/com.example.HelloWorld/main.py \
    s3://orangepi5-greengrass-artifacts-$(aws sts get-caller-identity --query Account --output text)/com.example.HelloWorld/1.0.0/main.py
```

#### Step 2: 컴포넌트 버전 등록

```bash
# 레시피 파일 수정 (S3 URI 사용)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > recipe-s3.yaml << EOF
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.HelloWorld
ComponentVersion: '1.0.0'
ComponentDescription: Hello World component for Orange Pi 5
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    message: "Hello from Orange Pi 5!"
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: |
        chmod +x {artifacts:path}/main.py
      Run: |
        python3 {artifacts:path}/main.py
    Artifacts:
      - URI: s3://orangepi5-greengrass-artifacts-${ACCOUNT_ID}/com.example.HelloWorld/1.0.0/main.py
EOF

# 컴포넌트 버전 생성
aws greengrassv2 create-component-version \
    --inline-recipe fileb://recipe-s3.yaml
```

#### Step 3: 배포 생성

```bash
# 배포 생성
cat > deployment.json << EOF
{
    "targetArn": "arn:aws:iot:ap-northeast-2:${ACCOUNT_ID}:thing/orangepi5-core-001",
    "deploymentName": "HelloWorld-Deployment",
    "components": {
        "com.example.HelloWorld": {
            "componentVersion": "1.0.0"
        }
    }
}
EOF

aws greengrassv2 create-deployment \
    --cli-input-json file://deployment.json
```

---

## 문제 해결

### 자주 발생하는 오류

#### 1. 인증서 오류

```
증상: TLS handshake failed

해결:
□ 인증서 파일 경로 확인
□ 인증서 권한 확인 (private.pem.key는 600)
□ 시간 동기화 확인 (timedatectl)
□ 인증서가 활성화 상태인지 AWS 콘솔에서 확인
```

#### 2. 연결 오류

```
증상: Unable to connect to AWS IoT Core

해결:
□ 인터넷 연결 확인
□ 방화벽에서 8883, 443 포트 허용
□ IoT 엔드포인트 주소 확인
□ AWS 리전 설정 확인
```

#### 3. 권한 오류

```
증상: Access denied

해결:
□ IAM 역할 정책 확인
□ IoT 정책 확인
□ Role Alias가 올바르게 설정되었는지 확인
```

#### 4. 컴포넌트 시작 실패

```bash
# 로그 확인
sudo tail -100 /greengrass/v2/logs/greengrass.log | grep -i error

# 컴포넌트 상태 확인
sudo /greengrass/v2/bin/greengrass-cli component list

# 특정 컴포넌트 상세 확인
sudo /greengrass/v2/bin/greengrass-cli component details \
    --name com.example.HelloWorld
```

### 로그 분석

```bash
# 에러 로그 검색
sudo grep -i "error\|exception\|fail" /greengrass/v2/logs/greengrass.log | tail -20

# 최근 배포 로그
sudo grep -i "deployment" /greengrass/v2/logs/greengrass.log | tail -20
```

### Greengrass 완전 재설치

```bash
# 서비스 중지
sudo systemctl stop greengrass

# 파일 삭제
sudo rm -rf /greengrass/v2

# 재설치 진행
# (위의 설치 단계 반복)
```

---

## 설치 완료 체크리스트

```
✅ Greengrass 설치 체크리스트

□ AWS CLI 설치 및 구성 완료
□ IoT Thing 생성 완료
□ 인증서 생성 및 활성화
□ IoT 정책 연결
□ IAM 역할 및 Role Alias 생성
□ Greengrass Core 설치
□ 서비스 실행 확인 (systemctl status greengrass)
□ AWS 콘솔에서 Healthy 상태 확인
□ 첫 번째 컴포넌트 (HelloWorld) 배포 테스트
```

---

## 다음 단계

Greengrass Core 설치가 완료되었습니다. 다음 문서에서는 S3와 MQTT를 활용한 데이터 전송 테스트를 진행합니다.

➡️ [05. S3 및 MQTT 통합 테스트](./05-s3-mqtt-integration.md)

---

## 참고 자료

- [AWS IoT Greengrass V2 설치 가이드](https://docs.aws.amazon.com/greengrass/v2/developerguide/install-greengrass-core-v2.html)
- [Greengrass Core 소프트웨어 다운로드](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-release-2023-08-04.html)
- [컴포넌트 개발 가이드](https://docs.aws.amazon.com/greengrass/v2/developerguide/develop-greengrass-components.html)
