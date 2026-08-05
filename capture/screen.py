"""屏幕捕获模块：独占全屏下使用 mss 直接抓取显示器。"""
from __future__ import annotations

import ctypes
import time
from pathlib import Path

import cv2
import mss
import numpy as np


def _set_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class ScreenCapture:
    def __init__(self, monitor: int = 0):
        _set_dpi_awareness()
        self._sct = mss.MSS()
        self.monitor_index = monitor
        monitors = self._sct.monitors
        if not 0 <= monitor < len(monitors):
            self.monitor_index = 0
        self.monitor = monitors[self.monitor_index]

    @property
    def resolution(self) -> tuple[int, int]:
        return self.monitor["width"], self.monitor["height"]

    def grab(self) -> np.ndarray | None:
        try:
            shot = self._sct.grab(self.monitor)
            return np.asarray(shot)[:, :, :3]
        except Exception as e:
            print(f"[capture] 抓帧失败: {e}")
            return None

    def save_frame(self, frame: np.ndarray, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), frame)


def grab_now(monitor: int = 0) -> np.ndarray | None:
    return ScreenCapture(monitor).grab()


def enable_utf8_console() -> None:
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    enable_utf8_console()
    cap = ScreenCapture(0)
    print(f"显示器 {cap.monitor_index}: {cap.resolution}")
    start = time.perf_counter()
    ok = 0
    fps_target = 10
    for _ in range(fps_target):
        frame = cap.grab()
        if frame is not None:
            ok += 1
        time.sleep(1 / fps_target)
    elapsed = time.perf_counter() - start
    print(f"10 次抓帧: 成功 {ok}/{fps_target}, 实际帧率 {ok / elapsed:.1f} fps")
    frame = cap.grab()
    if frame is not None:
        cap.save_frame(frame, Path("output/capture_test.png"))
        print("已保存测试帧: output/capture_test.png")
