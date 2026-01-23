#!/usr/bin/env python3
"""
PPE 감지 메인 애플리케이션
AWS Greengrass 컴포넌트로 실행됩니다.

기능:
- RTSP 카메라 또는 시뮬레이션 카메라에서 영상 수집
- NPU를 사용한 실시간 PPE 감지
- MQTT를 통한 위반 알림 전송
- S3에 위반 이미지 업로드
- 주기적 상태 보고

사용 예시:
    # 환경 변수 설정
    export THING_NAME="orangepi5-core-001"
    export USE_SIMULATION="true"

    # 실행
    python3 main.py

환경 변수:
    THING_NAME: IoT Thing 이름
    RTSP_URL: RTSP 카메라 URL (없으면 시뮬레이션)
    MODEL_PATH: RKNN 모델 경로
    S3_BUCKET: S3 버킷 이름
    AWS_REGION: AWS 리전
    USE_SIMULATION: 시뮬레이션 모드 사용 여부
"""

import os
import sys
import json
import time
import datetime
import threading
import traceback
import signal
from typing import Optional, List
import cv2
import numpy as np

# AWS SDK
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    print("[WARN] boto3 not installed, S3 upload disabled")

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
from rtsp_reader import RTSPReader, SimulatedCamera, create_camera
from ppe_detector import PPEDetector, Detection


class PPEDetectionSystem:
    """
    PPE 감지 시스템

    RTSP 카메라 영상에서 실시간으로 PPE 착용 여부를 감지하고
    위반 발생 시 AWS IoT Core로 알림을 전송합니다.
    """

    def __init__(self):
        """시스템 초기화"""
        # 환경 변수에서 설정 로드
        self.thing_name = os.environ.get("THING_NAME", "orangepi5-core-001")
        self.rtsp_url = os.environ.get("RTSP_URL", "")
        self.model_path = os.environ.get("MODEL_PATH", "")
        self.s3_bucket = os.environ.get("S3_BUCKET", "orangepi5-greengrass-data")
        self.aws_region = os.environ.get("AWS_REGION", "ap-northeast-2")
        self.use_simulation = os.environ.get("USE_SIMULATION", "true").lower() == "true"

        # MQTT 토픽
        self.topic_alerts = f"{self.thing_name}/alerts/ppe"
        self.topic_status = f"{self.thing_name}/status/ppe"

        # 컴포넌트
        self.camera = None
        self.detector = None
        self.ipc_client = None
        self.s3_client = None

        # 상태
        self.running = False
        self.frame_count = 0
        self.detection_count = 0
        self.violation_count = 0
        self.last_violation_time = None
        self.start_time = None

        # 알림 쿨다운 (같은 위반에 대해 반복 알림 방지)
        self.alert_cooldown = 30  # 초
        self.last_alert_time = {}

        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n[INFO] Received signal {signum}, shutting down...")
        self.running = False

    def initialize(self) -> bool:
        """
        시스템 초기화

        Returns:
            초기화 성공 여부
        """
        print("=" * 60)
        print("PPE Detection System v1.0.0")
        print("=" * 60)
        print(f"Thing Name: {self.thing_name}")
        print(f"RTSP URL: {self.rtsp_url or 'Not configured (Simulation)'}")
        print(f"Model Path: {self.model_path or 'Not configured (Simulation)'}")
        print(f"S3 Bucket: {self.s3_bucket}")
        print(f"AWS Region: {self.aws_region}")
        print(f"Simulation Mode: {self.use_simulation}")
        print("=" * 60)

        try:
            # 카메라 초기화
            self._init_camera()

            # PPE 감지기 초기화
            self._init_detector()

            # Greengrass IPC 초기화
            self._init_greengrass()

            # S3 클라이언트 초기화
            self._init_s3()

            print("[INFO] System initialized successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            traceback.print_exc()
            return False

    def _init_camera(self):
        """카메라 초기화"""
        if self.rtsp_url and not self.use_simulation:
            print(f"[INFO] Initializing RTSP camera: {self.rtsp_url}")
            self.camera = RTSPReader(
                rtsp_url=self.rtsp_url,
                queue_size=2,
                reconnect_delay=5.0
            )
        else:
            print("[INFO] Using simulated camera")
            self.camera = SimulatedCamera(width=640, height=480, fps=15)

    def _init_detector(self):
        """PPE 감지기 초기화"""
        self.detector = PPEDetector(
            model_path=self.model_path,
            input_size=(640, 640),
            conf_threshold=0.5,
            use_simulation=self.use_simulation
        )
        print("[INFO] PPE detector initialized")

    def _init_greengrass(self):
        """Greengrass IPC 초기화"""
        if HAS_GREENGRASS:
            try:
                self.ipc_client = ipc.connect()
                print("[INFO] Greengrass IPC connected")
            except Exception as e:
                print(f"[WARN] Greengrass IPC connection failed: {e}")
                self.ipc_client = None
        else:
            print("[WARN] Running without Greengrass IPC")

    def _init_s3(self):
        """S3 클라이언트 초기화"""
        if HAS_BOTO3:
            try:
                self.s3_client = boto3.client('s3', region_name=self.aws_region)
                print("[INFO] S3 client initialized")
            except Exception as e:
                print(f"[WARN] S3 client initialization failed: {e}")
                self.s3_client = None
        else:
            print("[WARN] Running without S3 support")

    def publish_mqtt(self, topic: str, message: dict) -> bool:
        """
        MQTT 메시지 발행

        Args:
            topic: MQTT 토픽
            message: 메시지 딕셔너리

        Returns:
            발행 성공 여부
        """
        payload = json.dumps(message, default=str)

        if not self.ipc_client:
            # IPC 없이 로컬 출력
            print(f"[MQTT] Topic: {topic}")
            print(f"[MQTT] Payload: {payload[:200]}...")
            return True

        try:
            request = PublishToIoTCoreRequest()
            request.topic_name = topic
            request.payload = payload.encode()
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

    def upload_image_to_s3(
        self,
        frame: np.ndarray,
        prefix: str = "violations"
    ) -> Optional[str]:
        """
        이미지를 S3에 업로드

        Args:
            frame: 이미지 프레임
            prefix: S3 키 접두사

        Returns:
            S3 URL 또는 None
        """
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
                ContentType='image/jpeg',
                Metadata={
                    'device_id': self.thing_name,
                    'timestamp': now.isoformat()
                }
            )

            s3_url = f"s3://{self.s3_bucket}/{key}"
            print(f"[S3] Uploaded: {s3_url}")
            return s3_url

        except ClientError as e:
            print(f"[S3] Upload failed: {e}")
            return None
        except Exception as e:
            print(f"[S3] Unexpected error: {e}")
            return None

    def send_violation_alert(
        self,
        detections: List[Detection],
        frame: np.ndarray
    ):
        """
        PPE 위반 알림 전송

        Args:
            detections: 감지 결과 리스트
            frame: 현재 프레임
        """
        violations = [d for d in detections if d.is_violation]

        if not violations:
            return

        current_time = time.time()

        for violation in violations:
            # 쿨다운 체크
            last_time = self.last_alert_time.get(violation.class_name, 0)
            if current_time - last_time < self.alert_cooldown:
                continue

            self.last_alert_time[violation.class_name] = current_time
            self.violation_count += 1
            self.last_violation_time = datetime.datetime.now().isoformat()

            # 결과 이미지 생성
            result_frame = self.detector.draw_detections(frame, [violation])

            # S3 업로드
            s3_url = self.upload_image_to_s3(result_frame, "violations")

            # 알림 메시지 구성
            alert_message = {
                "device_id": self.thing_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": "PPE_VIOLATION",
                "severity": "HIGH",
                "violation": violation.to_dict(),
                "image_url": s3_url,
                "message": f"PPE violation detected: {violation.class_name}",
                "stats": {
                    "total_violations": self.violation_count,
                    "frames_processed": self.frame_count
                }
            }

            # MQTT 발행
            self.publish_mqtt(self.topic_alerts, alert_message)
            print(f"[ALERT] {violation.class_name} violation detected!")

    def send_status_update(self):
        """상태 업데이트 전송"""
        uptime = time.time() - self.start_time if self.start_time else 0

        status_message = {
            "device_id": self.thing_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "running" if self.running else "stopped",
            "uptime_seconds": int(uptime),
            "stats": {
                "frames_processed": self.frame_count,
                "detections_total": self.detection_count,
                "violations_total": self.violation_count,
                "last_violation": self.last_violation_time,
                "inference_time_ms": round(self.detector.inference_time * 1000, 2) if self.detector else 0
            },
            "config": {
                "simulation_mode": self.use_simulation,
                "camera_resolution": self.camera.resolution if self.camera else (0, 0)
            }
        }

        self.publish_mqtt(self.topic_status, status_message)

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        프레임 처리

        Args:
            frame: 입력 프레임

        Returns:
            처리된 프레임
        """
        # PPE 감지
        detections = self.detector.detect(frame)

        # 통계 업데이트
        self.frame_count += 1
        self.detection_count += len(detections)

        # 위반 체크 및 알림
        violations = [d for d in detections if d.is_violation]
        if violations:
            self.send_violation_alert(detections, frame)

        # 결과 시각화
        result_frame = self.detector.draw_detections(
            frame,
            detections,
            show_fps=True,
            show_labels=True
        )

        return result_frame

    def run(self):
        """메인 실행 루프"""
        if not self.initialize():
            print("[ERROR] Initialization failed, exiting")
            return

        if not self.camera.start():
            print("[ERROR] Failed to start camera, exiting")
            return

        self.running = True
        self.start_time = time.time()

        # 상태 업데이트 간격 (초)
        status_interval = 60
        last_status_time = time.time()

        # 로그 출력 간격 (프레임 수)
        log_interval = 100

        print("[INFO] Starting main processing loop...")
        print("[INFO] Press Ctrl+C to stop")
        print("-" * 60)

        try:
            while self.running:
                # 프레임 가져오기
                frame = self.camera.get_frame(timeout=1.0)

                if frame is None:
                    continue

                # 프레임 처리
                result = self.process_frame(frame)

                # 주기적 상태 업데이트
                if time.time() - last_status_time >= status_interval:
                    self.send_status_update()
                    last_status_time = time.time()

                # 주기적 로그 출력
                if self.frame_count % log_interval == 0:
                    fps = 1.0 / self.detector.inference_time if self.detector.inference_time > 0 else 0
                    print(f"[INFO] Frames: {self.frame_count}, "
                          f"Detections: {self.detection_count}, "
                          f"Violations: {self.violation_count}, "
                          f"FPS: {fps:.1f}")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user")
        except Exception as e:
            print(f"[ERROR] Main loop error: {e}")
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """정리 작업"""
        print("[INFO] Cleaning up...")
        self.running = False

        # 최종 상태 전송
        self.send_status_update()

        # 카메라 정지
        if self.camera:
            self.camera.stop()

        # 감지기 해제
        if self.detector:
            self.detector.release()

        print("[INFO] Cleanup completed")
        print("=" * 60)
        print("Session Summary")
        print("=" * 60)
        print(f"Total frames processed: {self.frame_count}")
        print(f"Total detections: {self.detection_count}")
        print(f"Total violations: {self.violation_count}")
        if self.start_time:
            uptime = time.time() - self.start_time
            print(f"Uptime: {uptime:.1f} seconds")
        print("=" * 60)


def main():
    """엔트리 포인트"""
    system = PPEDetectionSystem()
    system.run()


if __name__ == "__main__":
    main()
