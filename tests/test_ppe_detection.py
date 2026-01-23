#!/usr/bin/env python3
"""
PPE Detection System 통합 테스트

테스트 실행:
    cd /path/to/project
    python -m pytest tests/ -v
    또는
    python tests/test_ppe_detection.py
"""

import sys
import os
import time
import numpy as np

# 소스 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rtsp_reader import RTSPReader, SimulatedCamera, create_camera
from ppe_detector import PPEDetector, Detection


class TestSimulatedCamera:
    """시뮬레이션 카메라 테스트"""

    def test_camera_init(self):
        """카메라 초기화 테스트"""
        camera = SimulatedCamera(width=640, height=480, fps=30)
        assert camera.width == 640
        assert camera.height == 480
        assert camera.resolution == (640, 480)

    def test_camera_start_stop(self):
        """카메라 시작/정지 테스트"""
        camera = SimulatedCamera()
        assert camera.start() == True
        assert camera.is_connected == True
        camera.stop()
        assert camera.is_connected == False

    def test_frame_capture(self):
        """프레임 캡처 테스트"""
        camera = SimulatedCamera(width=640, height=480, fps=10)
        camera.start()

        frame = camera.get_frame()
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        assert frame.dtype == np.uint8

        camera.stop()

    def test_multiple_frames(self):
        """연속 프레임 캡처 테스트"""
        camera = SimulatedCamera(width=320, height=240, fps=30)
        camera.start()

        frames = []
        for _ in range(5):
            frame = camera.get_frame()
            if frame is not None:
                frames.append(frame)

        assert len(frames) == 5
        camera.stop()


class TestPPEDetector:
    """PPE 감지기 테스트"""

    def test_detector_init(self):
        """감지기 초기화 테스트"""
        detector = PPEDetector(use_simulation=True)
        assert detector.use_simulation == True
        assert detector.conf_threshold == 0.5
        detector.release()

    def test_detection_simulation(self):
        """시뮬레이션 감지 테스트"""
        detector = PPEDetector(use_simulation=True)

        # 테스트 프레임 생성
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        detections = detector.detect(frame)

        assert isinstance(detections, list)
        assert len(detections) >= 1

        for det in detections:
            assert isinstance(det, Detection)
            assert det.class_name in PPEDetector.CLASSES
            assert 0 <= det.confidence <= 1
            assert len(det.bbox) == 4

        detector.release()

    def test_violation_detection(self):
        """위반 감지 테스트"""
        detector = PPEDetector(use_simulation=True)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # 여러 번 실행하여 위반 감지 확인
        found_violation = False
        for _ in range(20):
            detections = detector.detect(frame)
            violations = detector.get_violations(detections)
            if violations:
                found_violation = True
                break

        # 시뮬레이션에서 30% 확률로 위반 발생하므로
        # 20번 실행하면 거의 확실히 발견됨
        # (실패할 확률: 0.7^20 ≈ 0.08%)
        assert found_violation, "위반이 감지되어야 합니다"

        detector.release()

    def test_draw_detections(self):
        """감지 결과 시각화 테스트"""
        detector = PPEDetector(use_simulation=True)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        detections = detector.detect(frame)
        result = detector.draw_detections(frame, detections)

        assert result is not None
        assert result.shape == frame.shape
        assert result.dtype == np.uint8

        detector.release()

    def test_inference_time(self):
        """추론 시간 측정 테스트"""
        detector = PPEDetector(use_simulation=True)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        detector.detect(frame)

        # 시뮬레이션은 ~20ms 대기
        assert detector.inference_time > 0
        assert detector.inference_time < 1.0  # 1초 미만

        detector.release()

    def test_stats(self):
        """통계 테스트"""
        detector = PPEDetector(use_simulation=True)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        for _ in range(5):
            detector.detect(frame)

        stats = detector.get_stats()

        assert stats['total_inferences'] == 5
        assert stats['simulation_mode'] == True
        assert 'last_inference_time_ms' in stats

        detector.release()


class TestCameraFactory:
    """카메라 팩토리 함수 테스트"""

    def test_create_simulated_camera(self):
        """시뮬레이션 카메라 생성"""
        camera = create_camera(use_simulation=True, width=320, height=240)
        assert isinstance(camera, SimulatedCamera)
        assert camera.resolution == (320, 240)

    def test_create_camera_no_url(self):
        """URL 없이 카메라 생성 (시뮬레이션)"""
        camera = create_camera(rtsp_url=None)
        assert isinstance(camera, SimulatedCamera)

    def test_create_rtsp_camera(self):
        """RTSP 카메라 생성 (연결 시도만)"""
        camera = create_camera(rtsp_url="rtsp://test.invalid/stream", use_simulation=False)
        assert isinstance(camera, RTSPReader)


class TestDetectionDataclass:
    """Detection 데이터클래스 테스트"""

    def test_detection_creation(self):
        """Detection 생성"""
        det = Detection(
            class_id=1,
            class_name="hardhat",
            confidence=0.85,
            bbox=(100, 100, 200, 300),
            is_violation=False
        )

        assert det.class_id == 1
        assert det.class_name == "hardhat"
        assert det.confidence == 0.85
        assert det.bbox == (100, 100, 200, 300)
        assert det.is_violation == False

    def test_detection_to_dict(self):
        """Detection -> dict 변환"""
        det = Detection(
            class_id=2,
            class_name="no_hardhat",
            confidence=0.75,
            bbox=(50, 50, 150, 250),
            is_violation=True
        )

        d = det.to_dict()

        assert d['class_id'] == 2
        assert d['class_name'] == "no_hardhat"
        assert d['confidence'] == 0.75
        assert d['bbox']['x1'] == 50
        assert d['is_violation'] == True


class TestIntegration:
    """통합 테스트"""

    def test_full_pipeline(self):
        """전체 파이프라인 테스트"""
        # 카메라 생성
        camera = SimulatedCamera(width=640, height=480, fps=10)
        camera.start()

        # 감지기 생성
        detector = PPEDetector(use_simulation=True)

        # 프레임 처리 루프
        processed_frames = 0
        total_detections = 0
        total_violations = 0

        for _ in range(10):
            frame = camera.get_frame()
            if frame is None:
                continue

            detections = detector.detect(frame)
            violations = detector.get_violations(detections)
            result = detector.draw_detections(frame, detections)

            processed_frames += 1
            total_detections += len(detections)
            total_violations += len(violations)

            assert result is not None
            assert result.shape == (480, 640, 3)

        # 정리
        camera.stop()
        detector.release()

        # 결과 확인
        assert processed_frames == 10
        assert total_detections >= 10  # 각 프레임에서 최소 1개 감지
        print(f"\n통합 테스트 결과:")
        print(f"  처리된 프레임: {processed_frames}")
        print(f"  총 감지: {total_detections}")
        print(f"  총 위반: {total_violations}")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("PPE Detection System Tests")
    print("=" * 60)

    test_classes = [
        TestSimulatedCamera,
        TestPPEDetector,
        TestCameraFactory,
        TestDetectionDataclass,
        TestIntegration
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    getattr(instance, method_name)()
                    print(f"  [PASS] {method_name}")
                    passed_tests += 1
                except AssertionError as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed_tests.append((test_class.__name__, method_name, str(e)))
                except Exception as e:
                    print(f"  [ERROR] {method_name}: {e}")
                    failed_tests.append((test_class.__name__, method_name, str(e)))

    print("\n" + "=" * 60)
    print(f"테스트 결과: {passed_tests}/{total_tests} 통과")
    print("=" * 60)

    if failed_tests:
        print("\n실패한 테스트:")
        for class_name, method, error in failed_tests:
            print(f"  - {class_name}.{method}: {error}")
        return False
    else:
        print("\n모든 테스트 통과!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
