# NPU + RTSP 카메라 + PPE 감지 시스템

## 목차
1. [개요](#개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [환경 설정](#환경-설정)
4. [RKNN 모델 준비](#rknn-모델-준비)
5. [RTSP 카메라 연동](#rtsp-카메라-연동)
6. [PPE 감지 구현](#ppe-감지-구현)
7. [Greengrass 컴포넌트로 배포](#greengrass-컴포넌트로-배포)
8. [전체 통합 시스템](#전체-통합-시스템)
9. [시뮬레이션 및 테스트](#시뮬레이션-및-테스트)
10. [성능 최적화](#성능-최적화)
11. [문제 해결](#문제-해결)

---

## 개요

이 문서에서는 Orange Pi 5의 NPU(6 TOPS)를 활용하여 **RTSP 카메라 영상에서 실시간으로 PPE(개인보호장비)를 감지**하고, AWS Greengrass를 통해 결과를 클라우드로 전송하는 시스템을 구현합니다.

### PPE (Personal Protective Equipment) 감지 대상

```
┌─────────────────────────────────────────────────────────────────┐
│                    PPE 감지 대상                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  👷 안전모 (Hardhat)                                           │
│     - 착용 여부 감지                                           │
│     - 색상 구분 (흰색, 노란색, 빨간색 등)                      │
│                                                                 │
│  🦺 안전조끼 (Safety Vest)                                     │
│     - 착용 여부 감지                                           │
│     - 반사띠 유무                                               │
│                                                                 │
│  😷 마스크 (Mask)                                               │
│     - 착용 여부 감지                                           │
│                                                                 │
│  🥽 보안경 (Safety Glasses)                                    │
│     - 착용 여부 감지                                           │
│                                                                 │
│  🧤 안전장갑 (Gloves)                                          │
│     - 착용 여부 감지                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 학습 목표

- RKNN SDK를 사용한 NPU 기반 추론
- RTSP 스트림 처리
- YOLOv5/v8 기반 객체 감지
- Greengrass 컴포넌트와 통합
- 실시간 알림 시스템 구현

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         전체 시스템 아키텍처                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                                                          │
│  │   RTSP       │                                                          │
│  │   카메라     │                                                          │
│  └──────┬───────┘                                                          │
│         │ RTSP Stream                                                      │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Orange Pi 5                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                   Greengrass Core                            │   │   │
│  │  │                                                              │   │   │
│  │  │  ┌──────────────────────────────────────────────────────┐  │   │   │
│  │  │  │              PPE Detection Component                  │  │   │   │
│  │  │  │                                                       │  │   │   │
│  │  │  │  [RTSP Reader] ─▶ [Preprocessor] ─▶ [NPU Inference]  │  │   │   │
│  │  │  │                                         │             │  │   │   │
│  │  │  │                                         ▼             │  │   │   │
│  │  │  │                    [Postprocessor] ◀── [RKNN Model]  │  │   │   │
│  │  │  │                         │                             │  │   │   │
│  │  │  │            ┌────────────┼────────────┐                │  │   │   │
│  │  │  │            ▼            ▼            ▼                │  │   │   │
│  │  │  │       [Visualize]  [MQTT Alert]  [S3 Upload]         │  │   │   │
│  │  │  │                                                       │  │   │   │
│  │  │  └──────────────────────────────────────────────────────┘  │   │   │
│  │  │                                                              │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                        │                                            │   │
│  │                        │ NPU (6 TOPS)                              │   │
│  │                        ▼                                            │   │
│  │               ┌─────────────────┐                                   │   │
│  │               │  RK3588S NPU    │                                   │   │
│  │               │  - YOLOv5/v8    │                                   │   │
│  │               │  - ~30 FPS      │                                   │   │
│  │               └─────────────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              │ MQTT / HTTPS                                │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AWS Cloud                                    │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  IoT Core    │  │     S3       │  │  CloudWatch  │              │   │
│  │  │  (알림)      │  │  (이미지)    │  │   (로그)     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 환경 설정

### 필수 패키지 설치

```bash
# 시스템 패키지
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-opencv \
    ffmpeg \
    libopencv-dev \
    libdrm-dev \
    librga-dev

# Python 패키지
pip3 install \
    opencv-python-headless \
    numpy \
    pillow \
    boto3 \
    awsiotsdk
```

### RKNN Toolkit Lite2 설치

> **중요**: NPU를 사용하려면 커널, RKNPU 드라이버, librknnrt, rknn-toolkit-lite2의 버전이 모두 호환되어야 합니다.
> 자세한 호환성 매트릭스와 OS 선택 가이드는 [02. OS 설치 및 NPU 환경 설정](./02-orangepi5-os-installation.md#호환성-매트릭스)을 참조하세요.

```bash
# 방법 1: pip으로 설치 (v2.3.0+, 권장)
pip3 install rknn-toolkit-lite2

# 방법 2: GitHub에서 직접 설치 (pip 실패 시)
cd /tmp
git clone --depth 1 https://github.com/airockchip/rknn-toolkit2.git
pip3 install /tmp/rknn-toolkit2/rknn_toolkit_lite2/packages/rknn_toolkit_lite2-*-cp3*-cp3*-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
rm -rf /tmp/rknn-toolkit2

# 설치 확인
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite installed successfully')"

# NPU 환경 종합 확인
cat /sys/kernel/debug/rknpu/version          # RKNPU 드라이버 v0.9.8 권장
strings /usr/lib/librknnrt.so | grep version  # librknnrt v2.3.0+ 권장
```

### 프로젝트 디렉토리 구조

```bash
# 프로젝트 디렉토리 생성
mkdir -p ~/ppe-detection/{models,src,config,tests}
cd ~/ppe-detection

# 디렉토리 구조
tree ~/ppe-detection
# ppe-detection/
# ├── models/           # RKNN 모델 파일
# │   └── ppe_yolov5.rknn
# ├── src/              # 소스 코드
# │   ├── __init__.py
# │   ├── rtsp_reader.py
# │   ├── ppe_detector.py
# │   ├── mqtt_publisher.py
# │   └── main.py
# ├── config/           # 설정 파일
# │   └── config.yaml
# └── tests/            # 테스트 코드
#     └── test_detector.py
```

---

## RKNN 모델 준비

### 방법 1: 사전 학습된 모델 다운로드

```bash
# Rockchip 제공 사전 학습 모델 다운로드
cd ~/ppe-detection/models

# YOLOv5 RKNN 모델 (예시 - airockchip 최신 리포지토리 사용)
wget https://github.com/airockchip/rknn-toolkit2/raw/master/examples/onnx/yolov5/yolov5s-640-640.rknn

# 또는 PPE 전용 모델 (있는 경우)
# wget https://example.com/ppe_yolov5.rknn
```

### 방법 2: 커스텀 모델 변환

PC에서 RKNN Toolkit2를 사용하여 ONNX 모델을 RKNN으로 변환합니다.

```python
# convert_model.py (PC에서 실행)
from rknn.api import RKNN

# RKNN 객체 생성
rknn = RKNN()

# 모델 설정
rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform='rk3588'
)

# ONNX 모델 로드
rknn.load_onnx(model='yolov5s_ppe.onnx')

# 모델 빌드 (양자화)
rknn.build(do_quantization=True, dataset='dataset.txt')

# RKNN 모델 저장
rknn.export_rknn('ppe_yolov5.rknn')

# 정리
rknn.release()
```

### PPE 클래스 정의

```python
# src/ppe_classes.py

PPE_CLASSES = [
    'person',           # 0
    'hardhat',          # 1 - 안전모
    'no_hardhat',       # 2 - 안전모 미착용
    'safety_vest',      # 3 - 안전조끼
    'no_safety_vest',   # 4 - 안전조끼 미착용
    'mask',             # 5 - 마스크
    'no_mask',          # 6 - 마스크 미착용
    'safety_glasses',   # 7 - 보안경
    'gloves'            # 8 - 안전장갑
]

# 위반 클래스 (알림 대상)
VIOLATION_CLASSES = ['no_hardhat', 'no_safety_vest', 'no_mask']

# 클래스별 색상 (BGR)
CLASS_COLORS = {
    'person': (255, 255, 255),
    'hardhat': (0, 255, 0),
    'no_hardhat': (0, 0, 255),
    'safety_vest': (0, 255, 0),
    'no_safety_vest': (0, 0, 255),
    'mask': (0, 255, 0),
    'no_mask': (0, 0, 255),
    'safety_glasses': (0, 255, 0),
    'gloves': (0, 255, 0)
}
```

---

## RTSP 카메라 연동

### RTSP 리더 클래스

```python
# src/rtsp_reader.py
#!/usr/bin/env python3
"""
RTSP 카메라 스트림 리더
"""

import cv2
import threading
import time
from queue import Queue
from typing import Optional, Tuple
import numpy as np


class RTSPReader:
    """RTSP 스트림을 읽어 프레임 큐에 저장하는 클래스"""

    def __init__(
        self,
        rtsp_url: str,
        queue_size: int = 2,
        reconnect_delay: float = 5.0
    ):
        """
        Args:
            rtsp_url: RTSP 스트림 URL
            queue_size: 프레임 버퍼 크기
            reconnect_delay: 재연결 대기 시간 (초)
        """
        self.rtsp_url = rtsp_url
        self.queue_size = queue_size
        self.reconnect_delay = reconnect_delay

        self.frame_queue: Queue = Queue(maxsize=queue_size)
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()

    def start(self) -> bool:
        """스트림 읽기 시작"""
        if self.running:
            return True

        if not self._connect():
            return False

        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[RTSP] Started reading from {self.rtsp_url}")
        return True

    def stop(self):
        """스트림 읽기 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        if self.cap:
            self.cap.release()
        print("[RTSP] Stopped")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        프레임 가져오기

        Args:
            timeout: 대기 시간 (초)

        Returns:
            프레임 또는 None
        """
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return frame
        except:
            return None

    def _connect(self) -> bool:
        """RTSP 스트림 연결"""
        try:
            # GStreamer 백엔드 사용 (하드웨어 디코딩)
            gst_pipeline = (
                f"rtspsrc location={self.rtsp_url} latency=0 ! "
                f"rtph264depay ! h264parse ! "
                f"mppvideodec ! "
                f"videoconvert ! video/x-raw,format=BGR ! "
                f"appsink drop=1"
            )

            self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

            # GStreamer 실패 시 FFmpeg 사용
            if not self.cap.isOpened():
                print("[RTSP] GStreamer failed, trying FFmpeg...")
                self.cap = cv2.VideoCapture(self.rtsp_url)

            if not self.cap.isOpened():
                print(f"[RTSP] Failed to connect to {self.rtsp_url}")
                return False

            # 버퍼 크기 최소화 (지연 감소)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            print(f"[RTSP] Connected to {self.rtsp_url}")
            return True

        except Exception as e:
            print(f"[RTSP] Connection error: {e}")
            return False

    def _read_loop(self):
        """프레임 읽기 루프"""
        while self.running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    print("[RTSP] Reconnecting...")
                    time.sleep(self.reconnect_delay)
                    self._connect()
                    continue

                ret, frame = self.cap.read()

                if not ret:
                    print("[RTSP] Frame read failed")
                    self.cap.release()
                    self.cap = None
                    continue

                # 오래된 프레임 버리기
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass

                self.frame_queue.put(frame)
                self.frame_count += 1

                # FPS 계산
                current_time = time.time()
                elapsed = current_time - self.last_fps_time
                if elapsed >= 1.0:
                    self.fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.last_fps_time = current_time

            except Exception as e:
                print(f"[RTSP] Read error: {e}")
                time.sleep(0.1)

    @property
    def resolution(self) -> Tuple[int, int]:
        """스트림 해상도 반환"""
        if self.cap and self.cap.isOpened():
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (w, h)
        return (0, 0)


# 시뮬레이션용 가상 카메라 (테스트용)
class SimulatedCamera:
    """RTSP 카메라 시뮬레이션 (테스트용)"""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self.running = False
        self.last_frame_time = time.time()

    def start(self) -> bool:
        self.running = True
        print("[SIM] Simulated camera started")
        return True

    def stop(self):
        self.running = False
        print("[SIM] Simulated camera stopped")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """시뮬레이션된 프레임 생성"""
        if not self.running:
            return None

        # FPS 제한
        elapsed = time.time() - self.last_frame_time
        if elapsed < self.frame_delay:
            time.sleep(self.frame_delay - elapsed)

        self.last_frame_time = time.time()

        # 테스트 프레임 생성 (랜덤 색상 + 텍스트)
        frame = np.random.randint(50, 200, (self.height, self.width, 3), dtype=np.uint8)

        # 시뮬레이션된 사람 영역 (PPE 테스트용)
        cv2.rectangle(frame, (200, 100), (440, 400), (100, 150, 200), -1)

        # 타임스탬프 추가
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SIMULATED - {timestamp}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame

    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)
```

---

## PPE 감지 구현

### PPE 감지기 클래스

```python
# src/ppe_detector.py
#!/usr/bin/env python3
"""
RKNN NPU를 사용한 PPE 감지기
"""

import cv2
import numpy as np
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Detection:
    """감지 결과 데이터 클래스"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    is_violation: bool


class PPEDetector:
    """RKNN NPU 기반 PPE 감지기"""

    # 클래스 정의
    CLASSES = [
        'person', 'hardhat', 'no_hardhat', 'safety_vest',
        'no_safety_vest', 'mask', 'no_mask', 'safety_glasses', 'gloves'
    ]

    # 위반 클래스
    VIOLATION_CLASSES = ['no_hardhat', 'no_safety_vest', 'no_mask']

    # 클래스별 색상 (BGR)
    COLORS = {
        'person': (255, 255, 255),
        'hardhat': (0, 255, 0),
        'no_hardhat': (0, 0, 255),
        'safety_vest': (0, 255, 0),
        'no_safety_vest': (0, 0, 255),
        'mask': (0, 255, 0),
        'no_mask': (0, 0, 255),
        'safety_glasses': (0, 255, 0),
        'gloves': (0, 255, 0)
    }

    def __init__(
        self,
        model_path: str,
        input_size: Tuple[int, int] = (640, 640),
        conf_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        use_simulation: bool = False
    ):
        """
        Args:
            model_path: RKNN 모델 경로
            input_size: 모델 입력 크기 (width, height)
            conf_threshold: 신뢰도 임계값
            nms_threshold: NMS 임계값
            use_simulation: 시뮬레이션 모드 사용 여부
        """
        self.model_path = model_path
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.use_simulation = use_simulation

        self.rknn = None
        self.inference_time = 0.0

        if not use_simulation:
            self._load_model()

    def _load_model(self):
        """RKNN 모델 로드"""
        try:
            from rknnlite.api import RKNNLite

            self.rknn = RKNNLite()

            # 모델 로드
            ret = self.rknn.load_rknn(self.model_path)
            if ret != 0:
                raise RuntimeError(f"Failed to load model: {ret}")

            # 런타임 환경 초기화
            ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0_1_2)
            if ret != 0:
                raise RuntimeError(f"Failed to init runtime: {ret}")

            print(f"[PPE] Model loaded: {self.model_path}")
            print(f"[PPE] Input size: {self.input_size}")

        except ImportError:
            print("[PPE] RKNN Lite not available, using simulation mode")
            self.use_simulation = True
        except Exception as e:
            print(f"[PPE] Model load error: {e}, using simulation mode")
            self.use_simulation = True

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """전처리: 리사이즈 및 정규화"""
        # 리사이즈
        img = cv2.resize(frame, self.input_size)

        # BGR -> RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # HWC -> NHWC
        img = np.expand_dims(img, axis=0)

        return img

    def postprocess(
        self,
        outputs: List[np.ndarray],
        orig_shape: Tuple[int, int]
    ) -> List[Detection]:
        """후처리: NMS 및 좌표 변환"""
        detections = []

        # 시뮬레이션 모드
        if self.use_simulation:
            return self._simulate_detections(orig_shape)

        # YOLOv5 출력 처리
        output = outputs[0]

        # 바운딩 박스 추출
        boxes = output[:, :4]
        scores = output[:, 4:5] * output[:, 5:]
        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        # 신뢰도 필터링
        mask = confidences > self.conf_threshold
        boxes = boxes[mask]
        class_ids = class_ids[mask]
        confidences = confidences[mask]

        if len(boxes) == 0:
            return detections

        # NMS
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(),
            confidences.tolist(),
            self.conf_threshold,
            self.nms_threshold
        )

        # 결과 생성
        h, w = orig_shape[:2]
        scale_x = w / self.input_size[0]
        scale_y = h / self.input_size[1]

        for i in indices.flatten():
            x1, y1, x2, y2 = boxes[i]
            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)

            class_id = int(class_ids[i])
            class_name = self.CLASSES[class_id] if class_id < len(self.CLASSES) else 'unknown'
            confidence = float(confidences[i])
            is_violation = class_name in self.VIOLATION_CLASSES

            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                is_violation=is_violation
            )
            detections.append(detection)

        return detections

    def _simulate_detections(self, orig_shape: Tuple[int, int]) -> List[Detection]:
        """시뮬레이션 감지 결과 생성 (테스트용)"""
        import random

        detections = []
        h, w = orig_shape[:2]

        # 랜덤하게 감지 결과 생성
        num_detections = random.randint(1, 3)

        for i in range(num_detections):
            # 랜덤 클래스 선택 (위반 포함)
            if random.random() < 0.3:  # 30% 확률로 위반
                class_name = random.choice(self.VIOLATION_CLASSES)
            else:
                class_name = random.choice(['person', 'hardhat', 'safety_vest', 'mask'])

            class_id = self.CLASSES.index(class_name)

            # 랜덤 바운딩 박스
            x1 = random.randint(50, w // 2)
            y1 = random.randint(50, h // 2)
            x2 = x1 + random.randint(100, 200)
            y2 = y1 + random.randint(150, 300)

            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=random.uniform(0.6, 0.95),
                bbox=(x1, y1, min(x2, w), min(y2, h)),
                is_violation=class_name in self.VIOLATION_CLASSES
            )
            detections.append(detection)

        return detections

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        PPE 감지 실행

        Args:
            frame: 입력 이미지 (BGR)

        Returns:
            감지 결과 리스트
        """
        start_time = time.time()

        # 전처리
        input_data = self.preprocess(frame)

        # 추론
        if self.use_simulation:
            outputs = None
            time.sleep(0.03)  # 시뮬레이션된 추론 시간
        else:
            outputs = self.rknn.inference(inputs=[input_data])

        # 후처리
        detections = self.postprocess(outputs, frame.shape)

        self.inference_time = time.time() - start_time

        return detections

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        show_fps: bool = True
    ) -> np.ndarray:
        """감지 결과를 프레임에 그리기"""
        result = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = self.COLORS.get(det.class_name, (255, 255, 255))

            # 바운딩 박스
            thickness = 3 if det.is_violation else 2
            cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)

            # 라벨
            label = f"{det.class_name}: {det.confidence:.2f}"
            if det.is_violation:
                label = f"⚠️ {label}"

            # 라벨 배경
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(result, (x1, y1 - text_h - 10), (x1 + text_w, y1), color, -1)
            cv2.putText(result, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # FPS 표시
        if show_fps:
            fps = 1.0 / self.inference_time if self.inference_time > 0 else 0
            fps_text = f"FPS: {fps:.1f} | Inference: {self.inference_time*1000:.1f}ms"
            cv2.putText(result, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return result

    def release(self):
        """리소스 해제"""
        if self.rknn:
            self.rknn.release()
            print("[PPE] Model released")
```

---

## Greengrass 컴포넌트로 배포

### 메인 애플리케이션

```python
# src/main.py
#!/usr/bin/env python3
"""
PPE 감지 메인 애플리케이션
Greengrass 컴포넌트로 실행됩니다.
"""

import os
import sys
import json
import time
import datetime
import threading
import traceback
from typing import Optional
import cv2
import numpy as np
import boto3
from botocore.exceptions import ClientError

# Greengrass IPC
try:
    import awsiot.greengrasscoreipc as ipc
    from awsiot.greengrasscoreipc.model import (
        PublishToIoTCoreRequest,
        QOS
    )
    HAS_GREENGRASS = True
except ImportError:
    HAS_GREENGRASS = False
    print("[WARN] Greengrass IPC not available, running standalone")

# 로컬 모듈
from rtsp_reader import RTSPReader, SimulatedCamera
from ppe_detector import PPEDetector, Detection


class PPEDetectionSystem:
    """PPE 감지 시스템"""

    def __init__(self):
        # 환경 변수에서 설정 로드
        self.thing_name = os.environ.get("THING_NAME", "orangepi5-core-001")
        self.rtsp_url = os.environ.get("RTSP_URL", "")
        self.model_path = os.environ.get("MODEL_PATH", "/greengrass/v2/packages/artifacts/ppe_model/yolov5s.rknn")
        self.s3_bucket = os.environ.get("S3_BUCKET", "orangepi5-greengrass-data")
        self.aws_region = os.environ.get("AWS_REGION", "ap-northeast-2")
        self.use_simulation = os.environ.get("USE_SIMULATION", "true").lower() == "true"

        # MQTT 토픽
        self.topic_alerts = f"{self.thing_name}/alerts/ppe"
        self.topic_status = f"{self.thing_name}/status/ppe"

        # 컴포넌트
        self.camera: Optional[RTSPReader] = None
        self.detector: Optional[PPEDetector] = None
        self.ipc_client = None
        self.s3_client = None

        # 상태
        self.running = False
        self.frame_count = 0
        self.detection_count = 0
        self.violation_count = 0
        self.last_violation_time = None

        # 알림 쿨다운 (같은 위반에 대해 반복 알림 방지)
        self.alert_cooldown = 30  # 초
        self.last_alert_time = {}

    def initialize(self):
        """시스템 초기화"""
        print("=" * 60)
        print("PPE Detection System Initializing")
        print(f"Thing Name: {self.thing_name}")
        print(f"RTSP URL: {self.rtsp_url or 'Simulation Mode'}")
        print(f"Model Path: {self.model_path}")
        print(f"S3 Bucket: {self.s3_bucket}")
        print(f"Simulation Mode: {self.use_simulation}")
        print("=" * 60)

        # 카메라 초기화
        if self.rtsp_url and not self.use_simulation:
            self.camera = RTSPReader(self.rtsp_url)
        else:
            print("[INFO] Using simulated camera")
            self.camera = SimulatedCamera(width=640, height=480, fps=10)

        # PPE 감지기 초기화
        self.detector = PPEDetector(
            model_path=self.model_path,
            use_simulation=self.use_simulation
        )

        # Greengrass IPC 초기화
        if HAS_GREENGRASS:
            try:
                self.ipc_client = ipc.connect()
                print("[INFO] Greengrass IPC connected")
            except Exception as e:
                print(f"[WARN] Greengrass IPC connection failed: {e}")

        # S3 클라이언트 초기화
        try:
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            print("[INFO] S3 client initialized")
        except Exception as e:
            print(f"[WARN] S3 client initialization failed: {e}")

        print("[INFO] System initialized successfully")

    def publish_mqtt(self, topic: str, message: dict) -> bool:
        """MQTT 메시지 발행"""
        if not self.ipc_client:
            print(f"[MQTT] (No IPC) Topic: {topic}")
            print(f"[MQTT] Payload: {json.dumps(message, indent=2)}")
            return False

        try:
            request = PublishToIoTCoreRequest()
            request.topic_name = topic
            request.payload = json.dumps(message).encode()
            request.qos = QOS.AT_LEAST_ONCE

            operation = self.ipc_client.new_publish_to_iot_core()
            operation.activate(request)
            future = operation.get_response()
            future.result(timeout=10)

            print(f"[MQTT] Published to {topic}")
            return True
        except Exception as e:
            print(f"[MQTT] Publish failed: {e}")
            return False

    def upload_image_to_s3(self, frame: np.ndarray, prefix: str = "violations") -> Optional[str]:
        """이미지를 S3에 업로드"""
        if not self.s3_client:
            return None

        try:
            # 이미지 인코딩
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_data = buffer.tobytes()

            # S3 키 생성
            now = datetime.datetime.now()
            key = f"{prefix}/{self.thing_name}/{now.strftime('%Y/%m/%d')}/{now.strftime('%H%M%S_%f')}.jpg"

            # 업로드
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=image_data,
                ContentType='image/jpeg'
            )

            s3_url = f"s3://{self.s3_bucket}/{key}"
            print(f"[S3] Uploaded: {s3_url}")
            return s3_url

        except ClientError as e:
            print(f"[S3] Upload failed: {e}")
            return None

    def send_violation_alert(self, detections: list, frame: np.ndarray):
        """PPE 위반 알림 전송"""
        violations = [d for d in detections if d.is_violation]

        if not violations:
            return

        # 쿨다운 체크
        current_time = time.time()
        for violation in violations:
            last_time = self.last_alert_time.get(violation.class_name, 0)
            if current_time - last_time < self.alert_cooldown:
                continue

            self.last_alert_time[violation.class_name] = current_time

            # 이미지 업로드
            s3_url = self.upload_image_to_s3(frame, "violations")

            # 알림 메시지 구성
            alert_message = {
                "device_id": self.thing_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "PPE_VIOLATION",
                "severity": "HIGH",
                "violation": {
                    "type": violation.class_name,
                    "confidence": round(violation.confidence, 3),
                    "location": {
                        "x1": violation.bbox[0],
                        "y1": violation.bbox[1],
                        "x2": violation.bbox[2],
                        "y2": violation.bbox[3]
                    }
                },
                "image_url": s3_url,
                "message": f"PPE violation detected: {violation.class_name}"
            }

            # MQTT 발행
            self.publish_mqtt(self.topic_alerts, alert_message)
            self.violation_count += 1

    def send_status_update(self):
        """상태 업데이트 전송"""
        status_message = {
            "device_id": self.thing_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "running",
            "stats": {
                "frames_processed": self.frame_count,
                "detections_total": self.detection_count,
                "violations_total": self.violation_count,
                "last_violation": self.last_violation_time
            }
        }

        self.publish_mqtt(self.topic_status, status_message)

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """프레임 처리"""
        # PPE 감지
        detections = self.detector.detect(frame)

        self.frame_count += 1
        self.detection_count += len(detections)

        # 위반 체크 및 알림
        violations = [d for d in detections if d.is_violation]
        if violations:
            self.last_violation_time = datetime.datetime.now().isoformat()
            self.send_violation_alert(detections, frame)

        # 결과 시각화
        result_frame = self.detector.draw_detections(frame, detections)

        return result_frame

    def run(self):
        """메인 실행 루프"""
        self.initialize()

        if not self.camera.start():
            print("[ERROR] Failed to start camera")
            return

        self.running = True
        status_interval = 60  # 60초마다 상태 업데이트
        last_status_time = time.time()

        print("[INFO] Starting main processing loop")

        try:
            while self.running:
                # 프레임 가져오기
                frame = self.camera.get_frame(timeout=1.0)

                if frame is None:
                    continue

                # 프레임 처리
                result = self.process_frame(frame)

                # 상태 업데이트 (주기적)
                if time.time() - last_status_time >= status_interval:
                    self.send_status_update()
                    last_status_time = time.time()

                # 디버그 출력 (매 100프레임)
                if self.frame_count % 100 == 0:
                    print(f"[INFO] Processed {self.frame_count} frames, "
                          f"{self.detection_count} detections, "
                          f"{self.violation_count} violations")

        except KeyboardInterrupt:
            print("\n[INFO] Shutting down...")
        except Exception as e:
            print(f"[ERROR] Main loop error: {e}")
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """정리"""
        self.running = False

        if self.camera:
            self.camera.stop()

        if self.detector:
            self.detector.release()

        print("[INFO] Cleanup completed")


def main():
    """엔트리 포인트"""
    system = PPEDetectionSystem()
    system.run()


if __name__ == "__main__":
    main()
```

### Greengrass 레시피

```yaml
# recipe.yaml
---
RecipeFormatVersion: '2020-01-25'
ComponentName: com.example.PPEDetection
ComponentVersion: '1.0.0'
ComponentDescription: PPE Detection system with NPU acceleration
ComponentPublisher: Tutorial
ComponentConfiguration:
  DefaultConfiguration:
    ThingName: "orangepi5-core-001"
    RtspUrl: ""
    S3Bucket: "orangepi5-greengrass-data"
    UseSimulation: "true"
    accessControl:
      aws.greengrass.ipc.mqttproxy:
        com.example.PPEDetection:mqttproxy:1:
          operations:
            - "aws.greengrass#PublishToIoTCore"
          resources:
            - "orangepi5-core-001/*"
Manifests:
  - Platform:
      os: linux
      architecture: aarch64
    Lifecycle:
      Install: |
        pip3 install opencv-python-headless numpy pillow boto3 awsiotsdk
      Setenv:
        THING_NAME: "{configuration:/ThingName}"
        RTSP_URL: "{configuration:/RtspUrl}"
        S3_BUCKET: "{configuration:/S3Bucket}"
        USE_SIMULATION: "{configuration:/UseSimulation}"
        MODEL_PATH: "{artifacts:decompressedPath}/models/yolov5s.rknn"
        AWS_REGION: "ap-northeast-2"
      Run: |
        python3 -u {artifacts:decompressedPath}/src/main.py
    Artifacts:
      - URI: s3://YOUR_BUCKET/artifacts/ppe-detection.zip
        Unarchive: ZIP
```

---

## 전체 통합 시스템

### 프로젝트 파일 구조

```bash
# 전체 프로젝트 구조
ppe-detection/
├── models/
│   └── yolov5s.rknn          # RKNN 모델
├── src/
│   ├── __init__.py
│   ├── ppe_classes.py        # 클래스 정의
│   ├── rtsp_reader.py        # RTSP 리더
│   ├── ppe_detector.py       # PPE 감지기
│   └── main.py               # 메인 애플리케이션
├── config/
│   └── config.yaml           # 설정 파일
├── tests/
│   ├── test_camera.py
│   ├── test_detector.py
│   └── test_integration.py
├── recipe.yaml               # Greengrass 레시피
└── requirements.txt          # Python 의존성
```

### 배포 스크립트

```bash
#!/bin/bash
# deploy.sh - PPE Detection 컴포넌트 배포

set -e

COMPONENT_NAME="com.example.PPEDetection"
COMPONENT_VERSION="1.0.0"
BUCKET_NAME="orangepi5-greengrass-artifacts"
THING_NAME="orangepi5-core-001"

echo "=== PPE Detection Component Deployment ==="

# 1. 아티팩트 패키징
echo "[1/4] Packaging artifacts..."
cd ~/ppe-detection
zip -r ppe-detection.zip models/ src/ requirements.txt

# 2. S3 업로드
echo "[2/4] Uploading to S3..."
aws s3 cp ppe-detection.zip s3://${BUCKET_NAME}/artifacts/

# 3. 컴포넌트 버전 생성
echo "[3/4] Creating component version..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > /tmp/recipe.json << EOF
{
    "RecipeFormatVersion": "2020-01-25",
    "ComponentName": "${COMPONENT_NAME}",
    "ComponentVersion": "${COMPONENT_VERSION}",
    "ComponentDescription": "PPE Detection with NPU",
    "ComponentPublisher": "Tutorial",
    "ComponentConfiguration": {
        "DefaultConfiguration": {
            "ThingName": "${THING_NAME}",
            "S3Bucket": "orangepi5-greengrass-data",
            "UseSimulation": "true"
        }
    },
    "Manifests": [{
        "Platform": {"os": "linux", "architecture": "aarch64"},
        "Lifecycle": {
            "Install": "pip3 install -r {artifacts:decompressedPath}/requirements.txt",
            "Run": "python3 -u {artifacts:decompressedPath}/src/main.py"
        },
        "Artifacts": [{
            "URI": "s3://${BUCKET_NAME}/artifacts/ppe-detection.zip",
            "Unarchive": "ZIP"
        }]
    }]
}
EOF

aws greengrassv2 create-component-version \
    --inline-recipe "$(cat /tmp/recipe.json)"

# 4. 배포
echo "[4/4] Creating deployment..."
aws greengrassv2 create-deployment \
    --target-arn "arn:aws:iot:ap-northeast-2:${ACCOUNT_ID}:thing/${THING_NAME}" \
    --deployment-name "PPEDetection-Deployment-$(date +%Y%m%d%H%M%S)" \
    --components "{
        \"${COMPONENT_NAME}\": {
            \"componentVersion\": \"${COMPONENT_VERSION}\"
        }
    }"

echo "=== Deployment completed ==="
```

---

## 시뮬레이션 및 테스트

### 카메라 테스트

```python
# tests/test_camera.py
#!/usr/bin/env python3
"""카메라 연결 테스트"""

import sys
sys.path.append('../src')

from rtsp_reader import RTSPReader, SimulatedCamera
import cv2
import time


def test_simulated_camera():
    """시뮬레이션 카메라 테스트"""
    print("=== Simulated Camera Test ===")

    camera = SimulatedCamera(width=640, height=480, fps=30)
    camera.start()

    for i in range(10):
        frame = camera.get_frame()
        if frame is not None:
            print(f"Frame {i+1}: shape={frame.shape}")
        time.sleep(0.1)

    camera.stop()
    print("Test passed!")


def test_rtsp_camera(rtsp_url: str):
    """RTSP 카메라 테스트"""
    print(f"=== RTSP Camera Test: {rtsp_url} ===")

    camera = RTSPReader(rtsp_url)

    if not camera.start():
        print("Failed to connect!")
        return

    for i in range(30):
        frame = camera.get_frame()
        if frame is not None:
            print(f"Frame {i+1}: shape={frame.shape}, FPS={camera.fps:.1f}")
        time.sleep(0.1)

    camera.stop()
    print("Test passed!")


if __name__ == "__main__":
    test_simulated_camera()

    # RTSP 테스트 (URL 제공 시)
    # test_rtsp_camera("rtsp://192.168.1.100:554/stream")
```

### PPE 감지기 테스트

```python
# tests/test_detector.py
#!/usr/bin/env python3
"""PPE 감지기 테스트"""

import sys
sys.path.append('../src')

from ppe_detector import PPEDetector
import numpy as np
import cv2
import time


def test_simulation_mode():
    """시뮬레이션 모드 테스트"""
    print("=== PPE Detector Simulation Test ===")

    detector = PPEDetector(
        model_path="",
        use_simulation=True
    )

    # 테스트 이미지 생성
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # 감지 실행
    for i in range(5):
        detections = detector.detect(test_frame)
        print(f"\nFrame {i+1}:")
        print(f"  Inference time: {detector.inference_time*1000:.1f}ms")
        print(f"  Detections: {len(detections)}")

        for det in detections:
            print(f"    - {det.class_name}: {det.confidence:.2f} "
                  f"{'[VIOLATION]' if det.is_violation else ''}")

    # 시각화 테스트
    result = detector.draw_detections(test_frame, detections)
    print(f"\nVisualization shape: {result.shape}")

    detector.release()
    print("\nTest passed!")


def test_with_model(model_path: str):
    """실제 모델 테스트"""
    print(f"=== PPE Detector Model Test: {model_path} ===")

    detector = PPEDetector(
        model_path=model_path,
        use_simulation=False
    )

    # 테스트 이미지 로드 또는 생성
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    # 워밍업
    print("Warming up...")
    for _ in range(5):
        detector.detect(test_frame)

    # 벤치마크
    print("Benchmarking...")
    times = []
    for i in range(20):
        start = time.time()
        detections = detector.detect(test_frame)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    fps = 1.0 / avg_time

    print(f"\nBenchmark Results:")
    print(f"  Average inference time: {avg_time*1000:.1f}ms")
    print(f"  Average FPS: {fps:.1f}")
    print(f"  Min time: {min(times)*1000:.1f}ms")
    print(f"  Max time: {max(times)*1000:.1f}ms")

    detector.release()
    print("\nTest passed!")


if __name__ == "__main__":
    test_simulation_mode()

    # 실제 모델 테스트 (모델 경로 제공 시)
    # test_with_model("/path/to/ppe_yolov5.rknn")
```

### 통합 테스트

```python
# tests/test_integration.py
#!/usr/bin/env python3
"""통합 테스트"""

import sys
import os
import time

# 환경 변수 설정
os.environ["THING_NAME"] = "test-device"
os.environ["USE_SIMULATION"] = "true"
os.environ["S3_BUCKET"] = "test-bucket"

sys.path.append('../src')

from main import PPEDetectionSystem


def test_integration():
    """통합 테스트 (시뮬레이션 모드)"""
    print("=== Integration Test ===")

    system = PPEDetectionSystem()
    system.use_simulation = True

    # 초기화
    system.initialize()

    # 카메라 시작
    system.camera.start()

    # 프레임 처리 테스트
    for i in range(10):
        frame = system.camera.get_frame()
        if frame is not None:
            result = system.process_frame(frame)
            print(f"Frame {i+1}: processed, "
                  f"detections={system.detection_count}, "
                  f"violations={system.violation_count}")
        time.sleep(0.5)

    # 정리
    system.cleanup()

    print("\n=== Test Summary ===")
    print(f"Frames processed: {system.frame_count}")
    print(f"Total detections: {system.detection_count}")
    print(f"Total violations: {system.violation_count}")
    print("\nIntegration test passed!")


if __name__ == "__main__":
    test_integration()
```

### 테스트 실행

```bash
# 테스트 실행
cd ~/ppe-detection/tests

# 개별 테스트
python3 test_camera.py
python3 test_detector.py
python3 test_integration.py

# 모든 테스트
python3 -m pytest -v
```

---

## 성능 최적화

### NPU 최적화 팁

```python
# NPU 최적화 설정
# 1. 코어 마스크 설정 (3개 NPU 코어 모두 사용)
rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0_1_2)

# 2. 비동기 추론 사용
rknn.init_runtime(async_mode=True)

# 3. 배치 처리 (여러 프레임 동시 처리)
# 모델 변환 시 배치 크기 설정
```

### 메모리 최적화

```python
# 메모리 효율적인 프레임 처리
import gc

def process_with_memory_opt(frame):
    # 입력 복사 최소화
    input_data = preprocess(frame)

    # 추론
    output = rknn.inference(inputs=[input_data])

    # 즉시 메모리 해제
    del input_data
    gc.collect()

    return postprocess(output)
```

### 프레임 스킵

```python
# 적응형 프레임 스킵
class AdaptiveFrameSkip:
    def __init__(self, target_fps=15, max_skip=5):
        self.target_fps = target_fps
        self.max_skip = max_skip
        self.skip_count = 0

    def should_process(self, actual_fps):
        if actual_fps < self.target_fps:
            # FPS가 낮으면 스킵 증가
            self.skip_count = min(self.skip_count + 1, self.max_skip)
        else:
            # FPS가 충분하면 스킵 감소
            self.skip_count = max(self.skip_count - 1, 0)

        if self.skip_count > 0:
            self.skip_count -= 1
            return False
        return True
```

---

## 문제 해결

### 자주 발생하는 문제

#### 1. RKNN 모델 로드 실패

```bash
# 문제: "Failed to load model" 오류

# 해결:
# 1. 모델 파일 존재 확인
ls -la /path/to/model.rknn

# 2. RKNN Lite 설치 확인
python3 -c "from rknnlite.api import RKNNLite; print('OK')"

# 3. NPU 드라이버 확인
ls /dev/dri/

# 4. 권한 확인
sudo usermod -aG video,render $USER
```

#### 2. RTSP 연결 실패

```bash
# 문제: "Failed to connect to RTSP" 오류

# 해결:
# 1. 네트워크 연결 확인
ping <camera_ip>

# 2. RTSP URL 테스트 (ffmpeg)
ffplay rtsp://192.168.1.100:554/stream

# 3. 방화벽 확인
sudo ufw allow 554/tcp
```

#### 3. 메모리 부족

```bash
# 문제: "Out of memory" 오류

# 해결:
# 1. 스왑 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 메모리 사용량 확인
free -h
htop
```

#### 4. 추론 속도 느림

```bash
# 문제: FPS가 예상보다 낮음

# 확인:
# 1. NPU 사용 여부 확인
cat /sys/kernel/debug/rknpu/load

# 2. CPU 사용률 확인 (NPU 대신 CPU 사용 중일 수 있음)
htop

# 해결:
# - 모델이 NPU용으로 변환되었는지 확인
# - 입력 크기 줄이기 (640x640 → 416x416)
# - 프레임 스킵 적용
```

---

## 완료 체크리스트

```
✅ NPU + RTSP + PPE 감지 체크리스트

환경 설정:
□ RKNN Toolkit Lite 설치
□ OpenCV 설치
□ Python 의존성 설치

모델 준비:
□ RKNN 모델 다운로드/변환
□ 모델 테스트

카메라 연동:
□ RTSP 리더 구현
□ 시뮬레이션 카메라 구현
□ 연결 테스트

PPE 감지:
□ 감지기 구현
□ 시뮬레이션 모드 테스트
□ 실제 모델 테스트

Greengrass 통합:
□ 메인 애플리케이션 구현
□ MQTT 알림 테스트
□ S3 업로드 테스트
□ 컴포넌트 배포

최종 테스트:
□ 통합 테스트 통과
□ 성능 벤치마크
□ 장시간 안정성 테스트
```

---

## 참고 자료

- [RKNN Toolkit2 GitHub (airockchip, 최신)](https://github.com/airockchip/rknn-toolkit2)
- [RKNN Toolkit2 릴리스](https://github.com/airockchip/rknn-toolkit2/releases)
- [rknn-toolkit-lite2 (PyPI)](https://pypi.org/project/rknn-toolkit-lite2/)
- [YOLOv5 RKNN 변환 가이드](https://github.com/airockchip/rknn_model_zoo)
- [OpenCV RTSP 스트리밍](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html)
- [AWS IoT Greengrass ML Inference](https://docs.aws.amazon.com/greengrass/v2/developerguide/perform-machine-learning-inference.html)

---

## 마무리

이 튜토리얼을 통해 Orange Pi 5의 NPU를 활용한 실시간 PPE 감지 시스템을 구현하고 AWS Greengrass와 통합하는 방법을 배웠습니다.

### 다음 단계 제안

1. **모델 개선**: 자체 데이터로 PPE 모델 재학습
2. **대시보드**: AWS QuickSight로 시각화 대시보드 구축
3. **다중 카메라**: 여러 카메라 동시 처리
4. **알림 확장**: SNS, Slack 등 다양한 알림 채널 추가
5. **엣지 분석**: AWS IoT Analytics 연동
