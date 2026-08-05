"""预处理：降采样、灰度、ROI、帧差。"""
from __future__ import annotations

import numpy as np


def downsample(frame: np.ndarray, target_width: int) -> tuple[np.ndarray, float]:
    h, w = frame.shape[:2]
    if target_width and w > target_width:
        scale = target_width / w
        target_h = int(h * scale)
        return cv2_resize(frame, (target_width, target_h)), scale
    return frame, 1.0


def cv2_resize(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    import cv2

    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


def to_gray(frame: np.ndarray) -> np.ndarray:
    import cv2

    if frame.ndim == 3:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame


def crop_roi(frame: np.ndarray, roi: list[int] | None) -> np.ndarray:
    if roi is None:
        return frame
    x, y, w, h = [int(v) for v in roi]
    return frame[y : y + h, x : x + w]


def frame_diff(prev_gray: np.ndarray, cur_gray: np.ndarray) -> float:
    import cv2

    diff = cv2.absdiff(prev_gray, cur_gray)
    return float(diff.mean())
