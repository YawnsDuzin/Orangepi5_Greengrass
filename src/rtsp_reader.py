#!/usr/bin/env python3
"""
RTSP 카메라 스트림 리더
Orange Pi 5 + Greengrass PPE Detection 시스템용

사용 예시:
    from rtsp_reader import RTSPReader, SimulatedCamera

    # 실제 RTSP 카메라
    camera = RTSPReader("rtsp://192.168.1.100:554/stream")

    # 또는 시뮬레이션 카메라 (테스트용)
    camera = SimulatedCamera(width=640, height=480, fps=30)

    camera.start()
    frame = camera.get_frame()
    camera.stop()
"""

import cv2
import threading
import time
from queue import Queue
from typing import Optional, Tuple
import numpy as np


class RTSPReader:
    """
    RTSP 스트림을 읽어 프레임 큐에 저장하는 클래스

    특징:
    - 별도 스레드에서 프레임 읽기 (블로킹 방지)
    - 자동 재연결 지원
    - 프레임 버퍼링으로 최신 프레임 제공
    - GStreamer 하드웨어 디코딩 지원 (Orange Pi 5)
    """

    def __init__(
        self,
        rtsp_url: str,
        queue_size: int = 2,
        reconnect_delay: float = 5.0,
        use_gstreamer: bool = True
    ):
        """
        Args:
            rtsp_url: RTSP 스트림 URL (예: rtsp://192.168.1.100:554/stream)
            queue_size: 프레임 버퍼 크기 (작을수록 지연 감소)
            reconnect_delay: 연결 실패 시 재시도 대기 시간 (초)
            use_gstreamer: GStreamer 하드웨어 디코딩 사용 여부
        """
        self.rtsp_url = rtsp_url
        self.queue_size = queue_size
        self.reconnect_delay = reconnect_delay
        self.use_gstreamer = use_gstreamer

        self.frame_queue: Queue = Queue(maxsize=queue_size)
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # 통계
        self.frame_count = 0
        self.fps = 0.0
        self.last_fps_time = time.time()
        self.connection_errors = 0

    def start(self) -> bool:
        """
        스트림 읽기 시작

        Returns:
            연결 성공 여부
        """
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
            self.thread = None

        if self.cap:
            self.cap.release()
            self.cap = None

        # 큐 비우기
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                pass

        print("[RTSP] Stopped")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        큐에서 프레임 가져오기

        Args:
            timeout: 대기 시간 (초)

        Returns:
            프레임 (BGR numpy array) 또는 None
        """
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return frame
        except:
            return None

    def _connect(self) -> bool:
        """RTSP 스트림 연결"""
        try:
            with self.lock:
                if self.cap is not None:
                    self.cap.release()

                # GStreamer 파이프라인 (RK3588 하드웨어 디코딩)
                if self.use_gstreamer:
                    gst_pipeline = self._build_gstreamer_pipeline()
                    self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

                    if not self.cap.isOpened():
                        print("[RTSP] GStreamer failed, falling back to FFmpeg")
                        self.cap = cv2.VideoCapture(self.rtsp_url)
                else:
                    self.cap = cv2.VideoCapture(self.rtsp_url)

                if not self.cap.isOpened():
                    print(f"[RTSP] Failed to connect to {self.rtsp_url}")
                    self.connection_errors += 1
                    return False

                # 버퍼 크기 최소화 (지연 감소)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                self.connection_errors = 0
                print(f"[RTSP] Connected to {self.rtsp_url}")
                print(f"[RTSP] Resolution: {self.resolution}")
                return True

        except Exception as e:
            print(f"[RTSP] Connection error: {e}")
            self.connection_errors += 1
            return False

    def _build_gstreamer_pipeline(self) -> str:
        """RK3588용 GStreamer 파이프라인 생성"""
        # MPP (Media Process Platform) 하드웨어 디코더 사용
        pipeline = (
            f"rtspsrc location={self.rtsp_url} latency=0 ! "
            f"rtph264depay ! h264parse ! "
            f"mppvideodec ! "
            f"videoconvert ! video/x-raw,format=BGR ! "
            f"appsink drop=1 sync=0"
        )
        return pipeline

    def _read_loop(self):
        """프레임 읽기 루프 (별도 스레드에서 실행)"""
        while self.running:
            try:
                with self.lock:
                    if self.cap is None or not self.cap.isOpened():
                        pass
                    else:
                        ret, frame = self.cap.read()

                        if not ret:
                            print("[RTSP] Frame read failed")
                            self.cap.release()
                            self.cap = None
                        else:
                            # 오래된 프레임 버리기
                            if self.frame_queue.full():
                                try:
                                    self.frame_queue.get_nowait()
                                except:
                                    pass

                            self.frame_queue.put(frame)
                            self._update_fps()
                            continue

                # 연결 끊긴 경우 재연결
                print(f"[RTSP] Reconnecting in {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)
                self._connect()

            except Exception as e:
                print(f"[RTSP] Read error: {e}")
                time.sleep(0.1)

    def _update_fps(self):
        """FPS 계산"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time

        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time

    @property
    def resolution(self) -> Tuple[int, int]:
        """스트림 해상도 반환"""
        with self.lock:
            if self.cap and self.cap.isOpened():
                w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                return (w, h)
        return (0, 0)

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        with self.lock:
            return self.cap is not None and self.cap.isOpened()


class SimulatedCamera:
    """
    RTSP 카메라 시뮬레이션 (테스트 및 개발용)

    실제 카메라 없이 PPE 감지 시스템을 테스트할 수 있습니다.
    랜덤한 패턴의 프레임을 생성합니다.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 30
    ):
        """
        Args:
            width: 프레임 너비
            height: 프레임 높이
            fps: 목표 프레임 레이트
        """
        self.width = width
        self.height = height
        self.target_fps = fps
        self.frame_delay = 1.0 / fps
        self.running = False
        self.last_frame_time = time.time()
        self.frame_count = 0

        # 시뮬레이션된 사람 영역 (PPE 테스트용)
        self.person_regions = [
            (100, 80, 250, 380),   # x1, y1, x2, y2
            (350, 100, 500, 400),
        ]

    def start(self) -> bool:
        """시뮬레이션 시작"""
        self.running = True
        self.last_frame_time = time.time()
        print(f"[SIM] Simulated camera started ({self.width}x{self.height}@{self.target_fps}fps)")
        return True

    def stop(self):
        """시뮬레이션 중지"""
        self.running = False
        print("[SIM] Simulated camera stopped")

    def get_frame(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        시뮬레이션된 프레임 생성

        Returns:
            시뮬레이션된 프레임 또는 None
        """
        if not self.running:
            return None

        # FPS 제한
        elapsed = time.time() - self.last_frame_time
        if elapsed < self.frame_delay:
            time.sleep(self.frame_delay - elapsed)

        self.last_frame_time = time.time()
        self.frame_count += 1

        # 배경 프레임 생성
        frame = self._create_frame()

        return frame

    def _create_frame(self) -> np.ndarray:
        """시뮬레이션 프레임 생성"""
        # 그라데이션 배경
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 배경 색상 (약간의 노이즈 추가)
        frame[:, :] = [40 + np.random.randint(-5, 5),
                       40 + np.random.randint(-5, 5),
                       50 + np.random.randint(-5, 5)]

        # 시뮬레이션된 사람 영역 그리기
        for i, (x1, y1, x2, y2) in enumerate(self.person_regions):
            # 사람 영역 (다른 색상)
            color = (100 + i*30, 120 + i*20, 140 + i*10)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)

            # 머리 영역 (안전모 위치)
            head_y = y1 + 30
            head_x = (x1 + x2) // 2
            cv2.circle(frame, (head_x, head_y), 25, (180, 160, 140), -1)

            # 몸통 영역 (조끼 위치)
            body_top = y1 + 60
            body_bottom = y1 + 200
            cv2.rectangle(frame, (x1 + 20, body_top), (x2 - 20, body_bottom),
                         (150, 140, 130), -1)

        # 타임스탬프 추가
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"SIMULATED CAMERA - {timestamp}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1
        )

        # 프레임 번호
        cv2.putText(
            frame,
            f"Frame: {self.frame_count}",
            (10, self.height - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (150, 150, 150),
            1
        )

        return frame

    @property
    def resolution(self) -> Tuple[int, int]:
        """해상도 반환"""
        return (self.width, self.height)

    @property
    def fps(self) -> float:
        """현재 FPS"""
        return self.target_fps

    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self.running


def create_camera(
    rtsp_url: Optional[str] = None,
    use_simulation: bool = False,
    **kwargs
):
    """
    카메라 인스턴스 생성 팩토리 함수

    Args:
        rtsp_url: RTSP URL (None이면 시뮬레이션)
        use_simulation: 강제 시뮬레이션 모드
        **kwargs: 추가 설정

    Returns:
        RTSPReader 또는 SimulatedCamera 인스턴스
    """
    if use_simulation or not rtsp_url:
        width = kwargs.get('width', 640)
        height = kwargs.get('height', 480)
        fps = kwargs.get('fps', 30)
        return SimulatedCamera(width=width, height=height, fps=fps)
    else:
        queue_size = kwargs.get('queue_size', 2)
        reconnect_delay = kwargs.get('reconnect_delay', 5.0)
        return RTSPReader(
            rtsp_url=rtsp_url,
            queue_size=queue_size,
            reconnect_delay=reconnect_delay
        )


# 테스트용 메인
if __name__ == "__main__":
    print("=== Camera Module Test ===")

    # 시뮬레이션 카메라 테스트
    camera = SimulatedCamera(width=640, height=480, fps=10)
    camera.start()

    print("Reading frames...")
    for i in range(5):
        frame = camera.get_frame()
        if frame is not None:
            print(f"  Frame {i+1}: shape={frame.shape}")

    camera.stop()
    print("Test completed!")
