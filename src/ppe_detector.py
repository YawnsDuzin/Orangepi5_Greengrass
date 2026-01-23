#!/usr/bin/env python3
"""
RKNN NPU를 사용한 PPE (개인보호장비) 감지기
Orange Pi 5 + Greengrass PPE Detection 시스템용

지원 감지 항목:
- 안전모 (hardhat) / 미착용 (no_hardhat)
- 안전조끼 (safety_vest) / 미착용 (no_safety_vest)
- 마스크 (mask) / 미착용 (no_mask)
- 보안경 (safety_glasses)
- 안전장갑 (gloves)
- 사람 (person)

사용 예시:
    from ppe_detector import PPEDetector

    detector = PPEDetector(
        model_path="/path/to/model.rknn",
        use_simulation=False
    )

    detections = detector.detect(frame)
    result_frame = detector.draw_detections(frame, detections)

    detector.release()
"""

import cv2
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import random


@dataclass
class Detection:
    """
    감지 결과 데이터 클래스

    Attributes:
        class_id: 클래스 ID
        class_name: 클래스 이름
        confidence: 신뢰도 (0.0 ~ 1.0)
        bbox: 바운딩 박스 (x1, y1, x2, y2)
        is_violation: PPE 위반 여부
    """
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    is_violation: bool = False

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": {
                "x1": self.bbox[0],
                "y1": self.bbox[1],
                "x2": self.bbox[2],
                "y2": self.bbox[3]
            },
            "is_violation": self.is_violation
        }


class PPEDetector:
    """
    RKNN NPU 기반 PPE 감지기

    Orange Pi 5의 RK3588S NPU (6 TOPS)를 활용하여
    실시간으로 PPE 착용 여부를 감지합니다.
    """

    # PPE 클래스 정의
    CLASSES = [
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

    # PPE 위반 클래스 (알림 대상)
    VIOLATION_CLASSES = ['no_hardhat', 'no_safety_vest', 'no_mask']

    # 클래스별 표시 색상 (BGR)
    COLORS = {
        'person': (255, 255, 255),      # 흰색
        'hardhat': (0, 200, 0),         # 녹색
        'no_hardhat': (0, 0, 255),      # 빨간색
        'safety_vest': (0, 200, 0),     # 녹색
        'no_safety_vest': (0, 0, 255),  # 빨간색
        'mask': (0, 200, 0),            # 녹색
        'no_mask': (0, 0, 255),         # 빨간색
        'safety_glasses': (0, 200, 0),  # 녹색
        'gloves': (0, 200, 0)           # 녹색
    }

    # 클래스별 한글 라벨
    LABELS_KO = {
        'person': '사람',
        'hardhat': '안전모',
        'no_hardhat': '안전모 미착용',
        'safety_vest': '안전조끼',
        'no_safety_vest': '안전조끼 미착용',
        'mask': '마스크',
        'no_mask': '마스크 미착용',
        'safety_glasses': '보안경',
        'gloves': '안전장갑'
    }

    def __init__(
        self,
        model_path: str = "",
        input_size: Tuple[int, int] = (640, 640),
        conf_threshold: float = 0.5,
        nms_threshold: float = 0.45,
        use_simulation: bool = False
    ):
        """
        Args:
            model_path: RKNN 모델 파일 경로
            input_size: 모델 입력 크기 (width, height)
            conf_threshold: 신뢰도 임계값
            nms_threshold: NMS (Non-Maximum Suppression) 임계값
            use_simulation: 시뮬레이션 모드 사용 여부
        """
        self.model_path = model_path
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.use_simulation = use_simulation

        self.rknn = None
        self.inference_time = 0.0
        self.total_inferences = 0

        if not use_simulation and model_path:
            self._load_model()
        else:
            print("[PPE] Running in simulation mode")

    def _load_model(self):
        """RKNN 모델 로드"""
        try:
            from rknnlite.api import RKNNLite

            self.rknn = RKNNLite()

            # 모델 로드
            print(f"[PPE] Loading model: {self.model_path}")
            ret = self.rknn.load_rknn(self.model_path)
            if ret != 0:
                raise RuntimeError(f"Failed to load RKNN model: {ret}")

            # 런타임 환경 초기화 (3개 NPU 코어 모두 사용)
            ret = self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0_1_2)
            if ret != 0:
                raise RuntimeError(f"Failed to init RKNN runtime: {ret}")

            print(f"[PPE] Model loaded successfully")
            print(f"[PPE] Input size: {self.input_size}")
            print(f"[PPE] Confidence threshold: {self.conf_threshold}")

        except ImportError:
            print("[PPE] RKNN Lite not available, switching to simulation mode")
            self.use_simulation = True
        except FileNotFoundError:
            print(f"[PPE] Model file not found: {self.model_path}")
            print("[PPE] Switching to simulation mode")
            self.use_simulation = True
        except Exception as e:
            print(f"[PPE] Model load error: {e}")
            print("[PPE] Switching to simulation mode")
            self.use_simulation = True

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        전처리: 리사이즈 및 정규화

        Args:
            frame: 입력 이미지 (BGR, HWC)

        Returns:
            전처리된 이미지 (RGB, NHWC)
        """
        # 리사이즈
        img = cv2.resize(frame, self.input_size)

        # BGR -> RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # HWC -> NHWC (배치 차원 추가)
        img = np.expand_dims(img, axis=0)

        return img

    def postprocess(
        self,
        outputs: Any,
        orig_shape: Tuple[int, int, int]
    ) -> List[Detection]:
        """
        후처리: NMS 및 좌표 변환

        Args:
            outputs: 모델 출력
            orig_shape: 원본 이미지 shape (H, W, C)

        Returns:
            감지 결과 리스트
        """
        # 시뮬레이션 모드
        if self.use_simulation:
            return self._simulate_detections(orig_shape)

        detections = []

        try:
            # YOLOv5 출력 형식 처리
            output = np.array(outputs[0])

            if output.ndim == 3:
                output = output[0]  # 배치 차원 제거

            # [x, y, w, h, conf, class_scores...]
            boxes = output[:, :4]
            obj_conf = output[:, 4:5]
            class_scores = output[:, 5:]

            # 클래스별 신뢰도 계산
            scores = obj_conf * class_scores
            class_ids = np.argmax(scores, axis=1)
            confidences = np.max(scores, axis=1)

            # 신뢰도 필터링
            mask = confidences > self.conf_threshold
            boxes = boxes[mask]
            class_ids = class_ids[mask]
            confidences = confidences[mask]

            if len(boxes) == 0:
                return detections

            # xywh -> xyxy 변환
            boxes_xyxy = self._xywh_to_xyxy(boxes)

            # NMS
            indices = cv2.dnn.NMSBoxes(
                boxes_xyxy.tolist(),
                confidences.tolist(),
                self.conf_threshold,
                self.nms_threshold
            )

            # 좌표 스케일 변환
            h, w = orig_shape[:2]
            scale_x = w / self.input_size[0]
            scale_y = h / self.input_size[1]

            for i in indices.flatten():
                x1, y1, x2, y2 = boxes_xyxy[i]
                x1 = int(max(0, x1 * scale_x))
                y1 = int(max(0, y1 * scale_y))
                x2 = int(min(w, x2 * scale_x))
                y2 = int(min(h, y2 * scale_y))

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

        except Exception as e:
            print(f"[PPE] Postprocess error: {e}")

        return detections

    def _xywh_to_xyxy(self, boxes: np.ndarray) -> np.ndarray:
        """xywh 형식을 xyxy 형식으로 변환"""
        xyxy = np.zeros_like(boxes)
        xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2  # x1
        xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2  # y1
        xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2  # x2
        xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2  # y2
        return xyxy

    def _simulate_detections(
        self,
        orig_shape: Tuple[int, int, int]
    ) -> List[Detection]:
        """
        시뮬레이션 감지 결과 생성 (테스트용)

        실제 모델 없이 PPE 감지 시스템을 테스트할 수 있도록
        랜덤한 감지 결과를 생성합니다.
        """
        detections = []
        h, w = orig_shape[:2]

        # 1~3개의 감지 결과 생성
        num_detections = random.randint(1, 3)

        for _ in range(num_detections):
            # 30% 확률로 위반 클래스 생성
            if random.random() < 0.3:
                class_name = random.choice(self.VIOLATION_CLASSES)
            else:
                class_name = random.choice(['person', 'hardhat', 'safety_vest', 'mask'])

            class_id = self.CLASSES.index(class_name)

            # 랜덤 바운딩 박스 (이미지 내)
            x1 = random.randint(50, max(51, w // 2))
            y1 = random.randint(50, max(51, h // 2))
            box_w = random.randint(80, min(200, w - x1))
            box_h = random.randint(100, min(300, h - y1))
            x2 = min(x1 + box_w, w)
            y2 = min(y1 + box_h, h)

            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=random.uniform(0.6, 0.95),
                bbox=(x1, y1, x2, y2),
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
            time.sleep(0.02)  # 시뮬레이션된 추론 시간 (~20ms)
        else:
            outputs = self.rknn.inference(inputs=[input_data])

        # 후처리
        detections = self.postprocess(outputs, frame.shape)

        # 통계 업데이트
        self.inference_time = time.time() - start_time
        self.total_inferences += 1

        return detections

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        show_fps: bool = True,
        show_labels: bool = True,
        use_korean: bool = False
    ) -> np.ndarray:
        """
        감지 결과를 프레임에 그리기

        Args:
            frame: 입력 이미지
            detections: 감지 결과 리스트
            show_fps: FPS 표시 여부
            show_labels: 라벨 표시 여부
            use_korean: 한글 라벨 사용 여부

        Returns:
            결과가 그려진 이미지
        """
        result = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = self.COLORS.get(det.class_name, (255, 255, 255))

            # 바운딩 박스 (위반 시 더 굵게)
            thickness = 3 if det.is_violation else 2
            cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)

            if show_labels:
                # 라벨 텍스트
                if use_korean:
                    label = f"{self.LABELS_KO.get(det.class_name, det.class_name)}: {det.confidence:.2f}"
                else:
                    label = f"{det.class_name}: {det.confidence:.2f}"

                if det.is_violation:
                    label = f"! {label}"

                # 라벨 배경
                (text_w, text_h), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                cv2.rectangle(
                    result,
                    (x1, y1 - text_h - 10),
                    (x1 + text_w + 5, y1),
                    color,
                    -1
                )

                # 라벨 텍스트 (흰색)
                cv2.putText(
                    result,
                    label,
                    (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

        # FPS 및 추론 시간 표시
        if show_fps:
            fps = 1.0 / self.inference_time if self.inference_time > 0 else 0
            fps_text = f"FPS: {fps:.1f} | Inference: {self.inference_time*1000:.1f}ms"
            cv2.putText(
                result,
                fps_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            # 시뮬레이션 모드 표시
            if self.use_simulation:
                cv2.putText(
                    result,
                    "[SIMULATION MODE]",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2
                )

        return result

    def get_violations(self, detections: List[Detection]) -> List[Detection]:
        """위반 감지 결과만 필터링"""
        return [d for d in detections if d.is_violation]

    def get_stats(self) -> dict:
        """감지기 통계 반환"""
        return {
            "model_path": self.model_path,
            "input_size": self.input_size,
            "conf_threshold": self.conf_threshold,
            "simulation_mode": self.use_simulation,
            "total_inferences": self.total_inferences,
            "last_inference_time_ms": round(self.inference_time * 1000, 2),
            "average_fps": round(1.0 / self.inference_time, 1) if self.inference_time > 0 else 0
        }

    def release(self):
        """리소스 해제"""
        if self.rknn:
            self.rknn.release()
            self.rknn = None
            print("[PPE] Model released")


# 테스트용 메인
if __name__ == "__main__":
    print("=== PPE Detector Test ===")

    # 시뮬레이션 모드 테스트
    detector = PPEDetector(
        model_path="",
        use_simulation=True
    )

    # 테스트 이미지 생성
    test_frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)

    print("\nRunning detection test...")
    for i in range(5):
        detections = detector.detect(test_frame)

        print(f"\nFrame {i+1}:")
        print(f"  Inference time: {detector.inference_time*1000:.1f}ms")
        print(f"  Detections: {len(detections)}")

        violations = detector.get_violations(detections)
        print(f"  Violations: {len(violations)}")

        for det in detections:
            status = "[VIOLATION]" if det.is_violation else "[OK]"
            print(f"    - {det.class_name}: {det.confidence:.2f} {status}")

    # 시각화 테스트
    result = detector.draw_detections(test_frame, detections)
    print(f"\nVisualization result shape: {result.shape}")

    # 통계 출력
    print(f"\nDetector Stats: {detector.get_stats()}")

    detector.release()
    print("\nTest completed!")
