# S3 및 MQTT 통합 테스트

## 목차
1. [개요](#개요)
2. [MQTT 통신 이해](#mqtt-통신-이해)
3. [MQTT 테스트 컴포넌트 작성](#mqtt-테스트-컴포넌트-작성)
4. [AWS IoT Core에서 MQTT 테스트](#aws-iot-core에서-mqtt-테스트)
5. [S3 통합 이해](#s3-통합-이해)
6. [S3 업로드 컴포넌트 작성](#s3-업로드-컴포넌트-작성)
7. [Stream Manager 사용](#stream-manager-사용)
8. [통합 테스트 시나리오](#통합-테스트-시나리오)
9. [문제 해결](#문제-해결)

---

## 개요

이 문서에서는 Orange Pi 5의 Greengrass에서 **MQTT 메시징**과 **S3 데이터 업로드**를 테스트합니다.

### 학습 목표

```
┌─────────────────────────────────────────────────────────────────┐
│                    이 문서에서 배울 내용                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. MQTT 메시지 발행/구독                                      │
│     • 로컬 IPC를 통한 MQTT 통신                               │
│     • AWS IoT Core로 메시지 전송                              │
│                                                                 │
│  2. S3 데이터 업로드                                           │
│     • boto3를 사용한 직접 업로드                              │
│     • Stream Manager를 통한 배치 업로드                       │
│                                                                 │
│  3. 실제 IoT 시나리오 구현                                     │
│     • 센서 데이터 수집 및 전송                                │
│     • 파일 동기화                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## MQTT 통신 이해

### MQTT 메시지 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MQTT 메시지 흐름                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐                                                      │
│  │  컴포넌트 A  │ ─┐                                                   │
│  │  (발행자)    │  │ IPC                                               │
│  └──────────────┘  │                                                   │
│                    ▼                                                    │
│               ┌───────────────────┐       ┌────────────────────┐       │
│               │  Greengrass Core  │ MQTT  │   AWS IoT Core     │       │
│               │  (MQTT Broker)    │──────▶│   (클라우드)       │       │
│               └───────────────────┘       └────────────────────┘       │
│                    ▲                                                    │
│                    │ IPC                                               │
│  ┌──────────────┐  │                                                   │
│  │  컴포넌트 B  │ ─┘                                                   │
│  │  (구독자)    │                                                      │
│  └──────────────┘                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### MQTT 토픽 구조

```
토픽 명명 규칙 (권장):

{thing_name}/{category}/{type}

예시:
• orangepi5-core-001/sensors/temperature
• orangepi5-core-001/sensors/humidity
• orangepi5-core-001/alerts/ppe_violation
• orangepi5-core-001/status/heartbeat
```

---

## MQTT 테스트 컴포넌트 작성

### 프로젝트 구조

```
~/greengrass-components/com.example.MqttTest/
├── mqtt_publisher.py      # MQTT 발행 코드
├── mqtt_subscriber.py     # MQTT 구독 코드
├── recipe.yaml            # 컴포넌트 레시피
└── requirements.txt       # Python 의존성
```

### Step 1: 컴포넌트 디렉토리 생성

```bash
mkdir -p ~/greengrass-components/com.example.MqttTest
cd ~/greengrass-components/com.example.MqttTest
```

### Step 2: MQTT 발행자 작성

```bash
cat > mqtt_publisher.py << 'EOF'
#!/usr/bin/env python3
"""
MQTT Publisher Component
AWS IoT Greengrass IPC를 사용하여 MQTT 메시지를 발행합니다.
"""

import json
import time
import random
import datetime
import traceback

import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    PublishToIoTCoreRequest,
    QOS
)

# 설정
THING_NAME = "orangepi5-core-001"
TOPIC_SENSORS = f"{THING_NAME}/sensors/data"
TOPIC_STATUS = f"{THING_NAME}/status/heartbeat"
PUBLISH_INTERVAL = 5  # 초

def get_sensor_data():
    """시뮬레이션된 센서 데이터 생성"""
    return {
        "device_id": THING_NAME,
        "timestamp": datetime.datetime.now().isoformat(),
        "sensors": {
            "temperature": round(random.uniform(20.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "pressure": round(random.uniform(1000.0, 1020.0), 2),
            "cpu_temp": round(random.uniform(40.0, 60.0), 2)
        }
    }

def publish_to_iot_core(ipc_client, topic, message):
    """AWS IoT Core로 MQTT 메시지 발행"""
    try:
        request = PublishToIoTCoreRequest()
        request.topic_name = topic
        request.payload = json.dumps(message).encode()
        request.qos = QOS.AT_LEAST_ONCE

        operation = ipc_client.new_publish_to_iot_core()
        operation.activate(request)
        future = operation.get_response()
        future.result(timeout=10)

        print(f"[PUBLISHED] Topic: {topic}")
        print(f"  Payload: {json.dumps(message, indent=2)}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to publish: {e}")
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("MQTT Publisher Started")
    print(f"Publishing to topics: {TOPIC_SENSORS}, {TOPIC_STATUS}")
    print("=" * 60)

    try:
        # IPC 클라이언트 연결
        ipc_client = awsiot.greengrasscoreipc.connect()
        print("[INFO] Connected to Greengrass IPC")

        message_count = 0
        while True:
            message_count += 1

            # 센서 데이터 발행
            sensor_data = get_sensor_data()
            sensor_data["message_id"] = message_count
            publish_to_iot_core(ipc_client, TOPIC_SENSORS, sensor_data)

            # Heartbeat 발행 (매 10번째 메시지)
            if message_count % 10 == 0:
                heartbeat = {
                    "device_id": THING_NAME,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "healthy",
                    "messages_sent": message_count
                }
                publish_to_iot_core(ipc_client, TOPIC_STATUS, heartbeat)

            time.sleep(PUBLISH_INTERVAL)

    except Exception as e:
        print(f"[FATAL] Error in main loop: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
EOF
```

### Step 3: MQTT 구독자 작성

```bash
cat > mqtt_subscriber.py << 'EOF'
#!/usr/bin/env python3
"""
MQTT Subscriber Component
AWS IoT Greengrass IPC를 사용하여 MQTT 메시지를 구독합니다.
"""

import json
import traceback
import concurrent.futures

import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    SubscribeToIoTCoreRequest,
    QOS,
    IoTCoreMessage
)

# 설정
THING_NAME = "orangepi5-core-001"
SUBSCRIBE_TOPIC = f"{THING_NAME}/+/+"  # 와일드카드 구독

class MessageHandler:
    """MQTT 메시지 핸들러"""

    def __init__(self):
        self.message_count = 0

    def on_stream_event(self, event: IoTCoreMessage):
        """메시지 수신 시 호출"""
        try:
            self.message_count += 1
            topic = event.message.topic_name
            payload = event.message.payload.decode()

            print(f"\n[RECEIVED #{self.message_count}]")
            print(f"  Topic: {topic}")

            try:
                data = json.loads(payload)
                print(f"  Payload: {json.dumps(data, indent=4)}")

                # 온도 경고 체크
                if "sensors" in data:
                    temp = data["sensors"].get("temperature", 0)
                    if temp > 28:
                        print(f"  ⚠️ WARNING: High temperature detected: {temp}°C")
            except json.JSONDecodeError:
                print(f"  Payload (raw): {payload}")

        except Exception as e:
            print(f"[ERROR] Error processing message: {e}")
            traceback.print_exc()

    def on_stream_error(self, error):
        """스트림 에러 시 호출"""
        print(f"[ERROR] Stream error: {error}")
        return False

    def on_stream_closed(self):
        """스트림 종료 시 호출"""
        print("[INFO] Stream closed")

def main():
    print("=" * 60)
    print("MQTT Subscriber Started")
    print(f"Subscribing to topic: {SUBSCRIBE_TOPIC}")
    print("=" * 60)

    try:
        # IPC 클라이언트 연결
        ipc_client = awsiot.greengrasscoreipc.connect()
        print("[INFO] Connected to Greengrass IPC")

        # 구독 요청
        request = SubscribeToIoTCoreRequest()
        request.topic_name = SUBSCRIBE_TOPIC
        request.qos = QOS.AT_LEAST_ONCE

        handler = MessageHandler()
        operation = ipc_client.new_subscribe_to_iot_core(handler)
        operation.activate(request)

        future = operation.get_response()
        future.result(timeout=10)

        print(f"[INFO] Successfully subscribed to {SUBSCRIBE_TOPIC}")
        print("[INFO] Waiting for messages...")

        # 무한 대기 (종료될 때까지)
        while True:
            pass

    except Exception as e:
        print(f"[FATAL] Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
EOF
```

### Step 4: 의존성 파일 작성

```bash
cat > requirements.txt << 'EOF'
awsiotsdk>=1.17.0
EOF
```

### Step 5: 레시피 파일 작성

```bash
cat > recipe.yaml << 'EOF'
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.MqttTest
ComponentVersion: '1.0.0'
ComponentDescription: MQTT Publisher/Subscriber test component
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    accessControl:
      aws.greengrass.ipc.mqttproxy:
        com.example.MqttTest:mqttproxy:1:
          operations:
            - "aws.greengrass#PublishToIoTCore"
            - "aws.greengrass#SubscribeToIoTCore"
          resources:
            - "orangepi5-core-001/*"
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: pip3 install awsiotsdk
      Run: |
        python3 -u {artifacts:path}/mqtt_publisher.py
    Artifacts:
      - URI: file://{artifacts:path}/mqtt_publisher.py
      - URI: file://{artifacts:path}/mqtt_subscriber.py
EOF
```

### Step 6: 로컬 배포

```bash
sudo /greengrass/v2/bin/greengrass-cli deployment create \
    --recipeDir ~/greengrass-components/com.example.MqttTest \
    --artifactDir ~/greengrass-components/com.example.MqttTest \
    --merge "com.example.MqttTest=1.0.0"

# 로그 확인
sudo tail -f /greengrass/v2/logs/com.example.MqttTest.log
```

---

## AWS IoT Core에서 MQTT 테스트

### MQTT Test Client 사용

1. [AWS IoT Console](https://console.aws.amazon.com/iot) 접속
2. **Test** → **MQTT test client** 클릭

```
┌─────────────────────────────────────────────────────────────────┐
│                    MQTT Test Client                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Subscribe to a topic:                                          │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  orangepi5-core-001/#                                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│  [Subscribe]                                                    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Publish to a topic:                                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  orangepi5-core-001/commands/led                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  {"action": "on", "color": "red"}                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│  [Publish]                                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### CLI로 테스트

```bash
# AWS CLI로 MQTT 발행 (테스트용)
aws iot-data publish \
    --topic "orangepi5-core-001/commands/test" \
    --payload '{"message": "Hello from AWS CLI"}' \
    --cli-binary-format raw-in-base64-out
```

---

## S3 통합 이해

### S3 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         S3 데이터 흐름                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Orange Pi 5                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  [센서 데이터] ──▶ [컴포넌트] ──┬──▶ [직접 업로드 (boto3)]     │   │
│  │                                │                                │   │
│  │                                └──▶ [Stream Manager]           │   │
│  │                                      ↓                          │   │
│  │                              [배치/버퍼링]                       │   │
│  │                                      ↓                          │   │
│  └──────────────────────────────────────┼──────────────────────────┘   │
│                                         │                              │
│                                         ▼                              │
│  AWS Cloud                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                       Amazon S3                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  s3://my-bucket/                                         │   │   │
│  │  │  ├── sensor-data/                                        │   │   │
│  │  │  │   ├── 2024/01/15/data-001.json                       │   │   │
│  │  │  │   └── 2024/01/15/data-002.json                       │   │   │
│  │  │  └── images/                                             │   │   │
│  │  │      └── alerts/alert-001.jpg                           │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## S3 업로드 컴포넌트 작성

### Step 1: S3 버킷 생성 및 권한 설정

```bash
# S3 버킷 생성
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="orangepi5-greengrass-data-${ACCOUNT_ID}"

aws s3 mb s3://${BUCKET_NAME}

# IAM 정책 업데이트 (Token Exchange Role에 S3 권한 추가)
cat > s3-access-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name GreengrassV2TokenExchangeRole \
    --policy-name S3AccessPolicy \
    --policy-document file://s3-access-policy.json
```

### Step 2: S3 업로드 컴포넌트 생성

```bash
mkdir -p ~/greengrass-components/com.example.S3Upload
cd ~/greengrass-components/com.example.S3Upload
```

```bash
cat > s3_uploader.py << 'EOF'
#!/usr/bin/env python3
"""
S3 Uploader Component
센서 데이터를 수집하여 S3에 업로드합니다.
"""

import os
import json
import time
import random
import datetime
import traceback
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

# 설정
THING_NAME = "orangepi5-core-001"
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "orangepi5-greengrass-data")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
UPLOAD_INTERVAL = 30  # 30초마다 업로드

# 데이터 버퍼
data_buffer = []
BUFFER_SIZE = 10  # 10개씩 배치 업로드

def get_sensor_data():
    """시뮬레이션된 센서 데이터 생성"""
    return {
        "device_id": THING_NAME,
        "timestamp": datetime.datetime.now().isoformat(),
        "sensors": {
            "temperature": round(random.uniform(20.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "pressure": round(random.uniform(1000.0, 1020.0), 2)
        }
    }

def upload_to_s3(s3_client, data, key):
    """S3에 데이터 업로드"""
    try:
        json_data = json.dumps(data, indent=2)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
        print(f"[UPLOADED] s3://{BUCKET_NAME}/{key}")
        return True
    except ClientError as e:
        print(f"[ERROR] Failed to upload to S3: {e}")
        traceback.print_exc()
        return False

def upload_batch(s3_client, batch_data):
    """배치 데이터 업로드"""
    now = datetime.datetime.now()
    key = f"sensor-data/{now.strftime('%Y/%m/%d')}/batch-{now.strftime('%H%M%S')}.json"

    batch_payload = {
        "device_id": THING_NAME,
        "upload_time": now.isoformat(),
        "record_count": len(batch_data),
        "records": batch_data
    }

    return upload_to_s3(s3_client, batch_payload, key)

def main():
    print("=" * 60)
    print("S3 Uploader Started")
    print(f"Bucket: s3://{BUCKET_NAME}")
    print(f"Upload interval: {UPLOAD_INTERVAL}s")
    print(f"Batch size: {BUFFER_SIZE}")
    print("=" * 60)

    try:
        # S3 클라이언트 생성
        s3_client = boto3.client('s3', region_name=REGION)
        print("[INFO] S3 client created")

        # 버킷 존재 확인
        try:
            s3_client.head_bucket(Bucket=BUCKET_NAME)
            print(f"[INFO] Bucket {BUCKET_NAME} exists")
        except ClientError:
            print(f"[INFO] Creating bucket {BUCKET_NAME}")
            if REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=BUCKET_NAME)
            else:
                s3_client.create_bucket(
                    Bucket=BUCKET_NAME,
                    CreateBucketConfiguration={'LocationConstraint': REGION}
                )

        global data_buffer
        collect_count = 0

        while True:
            # 데이터 수집
            collect_count += 1
            sensor_data = get_sensor_data()
            sensor_data["sequence"] = collect_count
            data_buffer.append(sensor_data)

            print(f"[COLLECT #{collect_count}] Temperature: {sensor_data['sensors']['temperature']}°C")

            # 버퍼가 가득 차면 업로드
            if len(data_buffer) >= BUFFER_SIZE:
                print(f"\n[BATCH UPLOAD] Uploading {len(data_buffer)} records...")
                if upload_batch(s3_client, data_buffer):
                    data_buffer = []  # 버퍼 초기화
                else:
                    print("[WARNING] Upload failed, keeping data in buffer")

            time.sleep(UPLOAD_INTERVAL / BUFFER_SIZE)

    except Exception as e:
        print(f"[FATAL] Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
EOF
```

### Step 3: 레시피 파일 작성

```bash
cat > recipe.yaml << 'EOF'
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.S3Upload
ComponentVersion: '1.0.0'
ComponentDescription: S3 upload component with batch processing
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    S3BucketName: "orangepi5-greengrass-data"
    UploadInterval: 30
    BatchSize: 10
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: pip3 install boto3
      Setenv:
        S3_BUCKET_NAME: "{configuration:/S3BucketName}"
        AWS_REGION: "ap-northeast-2"
      Run: |
        python3 -u {artifacts:path}/s3_uploader.py
    Artifacts:
      - URI: file://{artifacts:path}/s3_uploader.py
EOF
```

### Step 4: 배포 및 테스트

```bash
# 배포
sudo /greengrass/v2/bin/greengrass-cli deployment create \
    --recipeDir ~/greengrass-components/com.example.S3Upload \
    --artifactDir ~/greengrass-components/com.example.S3Upload \
    --merge "com.example.S3Upload=1.0.0"

# 로그 확인
sudo tail -f /greengrass/v2/logs/com.example.S3Upload.log

# S3 업로드 확인
aws s3 ls s3://${BUCKET_NAME}/sensor-data/ --recursive
```

---

## Stream Manager 사용

Stream Manager는 대용량 데이터 스트림을 효율적으로 관리하고 AWS 서비스로 내보내는 Greengrass 컴포넌트입니다.

### Stream Manager 컴포넌트 설치

```bash
# Stream Manager 컴포넌트 배포
cat > stream-manager-deployment.json << EOF
{
    "targetArn": "arn:aws:iot:ap-northeast-2:${ACCOUNT_ID}:thing/orangepi5-core-001",
    "deploymentName": "StreamManager-Deployment",
    "components": {
        "aws.greengrass.StreamManager": {
            "componentVersion": "2.1.0",
            "configurationUpdate": {
                "merge": "{\"STREAM_MANAGER_STORE_ROOT_DIR\":\"/greengrass/v2/stream-manager\"}"
            }
        }
    }
}
EOF

aws greengrassv2 create-deployment \
    --cli-input-json file://stream-manager-deployment.json
```

### Stream Manager 사용 컴포넌트

```bash
mkdir -p ~/greengrass-components/com.example.StreamManagerUpload
cd ~/greengrass-components/com.example.StreamManagerUpload
```

```bash
cat > stream_manager_uploader.py << 'EOF'
#!/usr/bin/env python3
"""
Stream Manager를 사용한 S3 업로드
대용량 데이터를 효율적으로 S3로 내보냅니다.
"""

import os
import json
import time
import random
import datetime
import traceback
import asyncio

from stream_manager import (
    StreamManagerClient,
    MessageStreamDefinition,
    ExportDefinition,
    S3ExportTaskExecutorConfig,
    StatusConfig,
    StatusLevel,
    StatusMessage,
    Persistence,
    StrategyOnFull,
)

# 설정
THING_NAME = "orangepi5-core-001"
STREAM_NAME = "sensor-data-stream"
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "orangepi5-greengrass-data")

def create_stream_manager_client():
    """Stream Manager 클라이언트 생성"""
    return StreamManagerClient()

def create_stream(client):
    """메시지 스트림 생성"""
    try:
        # 기존 스트림 확인
        streams = client.list_streams()
        if STREAM_NAME in streams:
            print(f"[INFO] Stream '{STREAM_NAME}' already exists")
            return

        # S3 내보내기 설정
        s3_export_config = S3ExportTaskExecutorConfig(
            identifier="s3-export",
            s3_bucket=BUCKET_NAME,
            s3_key_prefix=f"stream-data/{THING_NAME}/",
            s3_region="ap-northeast-2"
        )

        export_definition = ExportDefinition(
            s3_task_executor=[s3_export_config]
        )

        # 스트림 정의
        stream_definition = MessageStreamDefinition(
            name=STREAM_NAME,
            max_size=268435456,  # 256MB
            stream_segment_size=16777216,  # 16MB
            strategy_on_full=StrategyOnFull.OverwriteOldestData,
            persistence=Persistence.File,
            flush_on_write=False,
            export_definition=export_definition
        )

        client.create_message_stream(stream_definition)
        print(f"[INFO] Stream '{STREAM_NAME}' created")

    except Exception as e:
        print(f"[ERROR] Failed to create stream: {e}")
        traceback.print_exc()

def append_data(client, data):
    """스트림에 데이터 추가"""
    try:
        payload = json.dumps(data).encode()
        sequence_number = client.append_message(STREAM_NAME, payload)
        print(f"[APPEND] Sequence: {sequence_number}, Size: {len(payload)} bytes")
        return sequence_number
    except Exception as e:
        print(f"[ERROR] Failed to append data: {e}")
        traceback.print_exc()
        return None

def get_sensor_data():
    """시뮬레이션된 센서 데이터"""
    return {
        "device_id": THING_NAME,
        "timestamp": datetime.datetime.now().isoformat(),
        "sensors": {
            "temperature": round(random.uniform(20.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "pressure": round(random.uniform(1000.0, 1020.0), 2),
            "light": round(random.uniform(100.0, 1000.0), 2)
        }
    }

def main():
    print("=" * 60)
    print("Stream Manager Uploader Started")
    print(f"Stream: {STREAM_NAME}")
    print(f"Target Bucket: s3://{BUCKET_NAME}")
    print("=" * 60)

    try:
        # Stream Manager 클라이언트 생성
        client = create_stream_manager_client()
        print("[INFO] Stream Manager client connected")

        # 스트림 생성
        create_stream(client)

        # 데이터 수집 및 스트림에 추가
        count = 0
        while True:
            count += 1

            # 센서 데이터 수집
            data = get_sensor_data()
            data["sequence"] = count

            # 스트림에 추가
            append_data(client, data)

            # 5초 대기
            time.sleep(5)

    except Exception as e:
        print(f"[FATAL] Error: {e}")
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    main()
EOF
```

### Stream Manager 레시피

```bash
cat > recipe.yaml << 'EOF'
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.StreamManagerUpload
ComponentVersion: '1.0.0'
ComponentDescription: Stream Manager based S3 upload
ComponentPublisher: Tutorial
ComponentDependencies:
  aws.greengrass.StreamManager:
    VersionRequirement: ">=2.0.0"
ComponentConfiguration:
  DefaultConfiguration:
    S3BucketName: "orangepi5-greengrass-data"
    accessControl:
      aws.greengrass.StreamManager:
        com.example.StreamManagerUpload:streammanager:1:
          operations:
            - "*"
          resources:
            - "*"
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: pip3 install stream_manager
      Setenv:
        S3_BUCKET_NAME: "{configuration:/S3BucketName}"
      Run: |
        python3 -u {artifacts:path}/stream_manager_uploader.py
    Artifacts:
      - URI: file://{artifacts:path}/stream_manager_uploader.py
EOF
```

---

## 통합 테스트 시나리오

### 시나리오: 센서 데이터 수집 및 이상 알림

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    통합 테스트 시나리오                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 센서 데이터 수집 (시뮬레이션)                                      │
│     │                                                                   │
│     ▼                                                                   │
│  2. 데이터 처리                                                         │
│     ├── 정상: S3에 배치 업로드                                         │
│     └── 이상: MQTT로 알림 발송                                         │
│                                                                         │
│  3. 클라우드 확인                                                       │
│     ├── S3 버킷에서 데이터 확인                                        │
│     └── IoT Core MQTT Test Client에서 알림 확인                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 통합 컴포넌트 작성

```bash
mkdir -p ~/greengrass-components/com.example.IntegratedSensor
cd ~/greengrass-components/com.example.IntegratedSensor
```

```bash
cat > integrated_sensor.py << 'EOF'
#!/usr/bin/env python3
"""
통합 센서 컴포넌트
- 센서 데이터 수집
- 정상 데이터: S3 업로드
- 이상 데이터: MQTT 알림
"""

import os
import json
import time
import random
import datetime
import traceback

import boto3
from botocore.exceptions import ClientError
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import (
    PublishToIoTCoreRequest,
    QOS
)

# 설정
THING_NAME = "orangepi5-core-001"
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "orangepi5-greengrass-data")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

# 임계값
TEMP_THRESHOLD_HIGH = 28.0
TEMP_THRESHOLD_LOW = 18.0
HUMIDITY_THRESHOLD_HIGH = 75.0

# 토픽
TOPIC_ALERTS = f"{THING_NAME}/alerts/sensor"
TOPIC_STATUS = f"{THING_NAME}/status/sensor"

# 버퍼
data_buffer = []
BUFFER_SIZE = 5

def get_sensor_data():
    """시뮬레이션된 센서 데이터 (가끔 이상치 발생)"""
    # 10% 확률로 이상치 발생
    if random.random() < 0.1:
        temp = round(random.uniform(28.0, 35.0), 2)  # 높은 온도
    else:
        temp = round(random.uniform(20.0, 27.0), 2)  # 정상 온도

    return {
        "device_id": THING_NAME,
        "timestamp": datetime.datetime.now().isoformat(),
        "sensors": {
            "temperature": temp,
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "pressure": round(random.uniform(1000.0, 1020.0), 2)
        }
    }

def check_anomaly(data):
    """이상치 검사"""
    anomalies = []
    sensors = data.get("sensors", {})

    temp = sensors.get("temperature", 0)
    humidity = sensors.get("humidity", 0)

    if temp > TEMP_THRESHOLD_HIGH:
        anomalies.append({
            "type": "HIGH_TEMPERATURE",
            "value": temp,
            "threshold": TEMP_THRESHOLD_HIGH,
            "message": f"Temperature too high: {temp}°C"
        })
    elif temp < TEMP_THRESHOLD_LOW:
        anomalies.append({
            "type": "LOW_TEMPERATURE",
            "value": temp,
            "threshold": TEMP_THRESHOLD_LOW,
            "message": f"Temperature too low: {temp}°C"
        })

    if humidity > HUMIDITY_THRESHOLD_HIGH:
        anomalies.append({
            "type": "HIGH_HUMIDITY",
            "value": humidity,
            "threshold": HUMIDITY_THRESHOLD_HIGH,
            "message": f"Humidity too high: {humidity}%"
        })

    return anomalies

def publish_alert(ipc_client, data, anomalies):
    """이상 알림 MQTT 발행"""
    try:
        alert_message = {
            "device_id": THING_NAME,
            "timestamp": datetime.datetime.now().isoformat(),
            "severity": "WARNING",
            "anomalies": anomalies,
            "sensor_data": data["sensors"]
        }

        request = PublishToIoTCoreRequest()
        request.topic_name = TOPIC_ALERTS
        request.payload = json.dumps(alert_message).encode()
        request.qos = QOS.AT_LEAST_ONCE

        operation = ipc_client.new_publish_to_iot_core()
        operation.activate(request)
        future = operation.get_response()
        future.result(timeout=10)

        print(f"[ALERT] Published to {TOPIC_ALERTS}")
        for anomaly in anomalies:
            print(f"  ⚠️ {anomaly['message']}")

        return True
    except Exception as e:
        print(f"[ERROR] Failed to publish alert: {e}")
        return False

def upload_to_s3(s3_client, batch_data):
    """S3에 배치 업로드"""
    try:
        now = datetime.datetime.now()
        key = f"sensor-data/{THING_NAME}/{now.strftime('%Y/%m/%d')}/data-{now.strftime('%H%M%S')}.json"

        payload = {
            "device_id": THING_NAME,
            "upload_time": now.isoformat(),
            "record_count": len(batch_data),
            "records": batch_data
        }

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(payload, indent=2).encode('utf-8'),
            ContentType='application/json'
        )

        print(f"[S3 UPLOAD] s3://{BUCKET_NAME}/{key} ({len(batch_data)} records)")
        return True
    except ClientError as e:
        print(f"[ERROR] S3 upload failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Integrated Sensor Component Started")
    print(f"Device: {THING_NAME}")
    print(f"S3 Bucket: {BUCKET_NAME}")
    print(f"Alert Topic: {TOPIC_ALERTS}")
    print("=" * 60)

    try:
        # 클라이언트 초기화
        ipc_client = awsiot.greengrasscoreipc.connect()
        s3_client = boto3.client('s3', region_name=REGION)
        print("[INFO] Clients initialized")

        global data_buffer
        collect_count = 0

        while True:
            collect_count += 1

            # 센서 데이터 수집
            sensor_data = get_sensor_data()
            sensor_data["sequence"] = collect_count

            print(f"\n[COLLECT #{collect_count}] Temp: {sensor_data['sensors']['temperature']}°C, "
                  f"Humidity: {sensor_data['sensors']['humidity']}%")

            # 이상치 검사
            anomalies = check_anomaly(sensor_data)

            if anomalies:
                # 이상 발견: MQTT 알림
                publish_alert(ipc_client, sensor_data, anomalies)

            # 버퍼에 추가
            data_buffer.append(sensor_data)

            # 버퍼가 가득 차면 S3 업로드
            if len(data_buffer) >= BUFFER_SIZE:
                if upload_to_s3(s3_client, data_buffer):
                    data_buffer = []

            time.sleep(5)

    except Exception as e:
        print(f"[FATAL] Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
EOF
```

### 통합 레시피

```bash
cat > recipe.yaml << 'EOF'
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.IntegratedSensor
ComponentVersion: '1.0.0'
ComponentDescription: Integrated sensor component with S3 and MQTT
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    S3BucketName: "orangepi5-greengrass-data"
    accessControl:
      aws.greengrass.ipc.mqttproxy:
        com.example.IntegratedSensor:mqttproxy:1:
          operations:
            - "aws.greengrass#PublishToIoTCore"
          resources:
            - "orangepi5-core-001/*"
Manifests:
  - Platform:
      os: linux
    Lifecycle:
      Install: pip3 install boto3 awsiotsdk
      Setenv:
        S3_BUCKET_NAME: "{configuration:/S3BucketName}"
        AWS_REGION: "ap-northeast-2"
      Run: |
        python3 -u {artifacts:path}/integrated_sensor.py
    Artifacts:
      - URI: file://{artifacts:path}/integrated_sensor.py
EOF
```

---

## 문제 해결

### MQTT 관련 문제

```bash
# IPC 권한 오류
증상: "aws.greengrass#UnauthorizedError"

해결:
1. recipe.yaml의 accessControl 섹션 확인
2. 토픽 패턴이 resources와 일치하는지 확인
3. 컴포넌트 재배포
```

### S3 관련 문제

```bash
# 자격 증명 오류
증상: "NoCredentialsError" 또는 "AccessDenied"

해결:
1. Token Exchange Role에 S3 권한 추가
2. IAM 역할 신뢰 정책 확인
3. 버킷 정책 확인

# 권한 확인 명령
aws iam get-role-policy \
    --role-name GreengrassV2TokenExchangeRole \
    --policy-name S3AccessPolicy
```

### 로그 확인

```bash
# 컴포넌트 로그
sudo tail -f /greengrass/v2/logs/com.example.IntegratedSensor.log

# Greengrass 전체 로그
sudo tail -f /greengrass/v2/logs/greengrass.log | grep -i "error\|warn"
```

---

## 테스트 완료 체크리스트

```
✅ S3/MQTT 통합 테스트 체크리스트

□ MQTT 발행 테스트 완료
□ MQTT 구독 테스트 완료
□ AWS IoT Core Test Client에서 메시지 확인
□ S3 버킷 생성 및 권한 설정
□ S3 업로드 테스트 완료
□ S3 버킷에서 데이터 확인
□ 통합 시나리오 테스트 완료
  - 정상 데이터 → S3 업로드
  - 이상 데이터 → MQTT 알림
```

---

## 다음 단계

S3와 MQTT 통합 테스트를 완료했습니다. 다음 문서에서는 Orange Pi 5의 NPU를 활용한 RTSP 카메라 연동 및 PPE(개인보호장비) 감지 시스템을 구현합니다.

➡️ [06. NPU + RTSP 카메라 + PPE 감지](./06-npu-rtsp-ppe-detection.md)

---

## 참고 자료

- [AWS IoT Greengrass IPC](https://docs.aws.amazon.com/greengrass/v2/developerguide/interprocess-communication.html)
- [Stream Manager 사용 가이드](https://docs.aws.amazon.com/greengrass/v2/developerguide/stream-manager.html)
- [AWS IoT Core MQTT](https://docs.aws.amazon.com/iot/latest/developerguide/mqtt.html)
