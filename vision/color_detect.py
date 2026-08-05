"""HSV 颜色特征检测：捕捉成功/失败特效颜色像素占比判定。"""
from __future__ import annotations

import cv2
import numpy as np


class ColorDetector:
    def __init__(self, cfg: dict | None):
        self.enable = bool(cfg and cfg.get("enable", False))
        self.min_ratio = float(cfg.get("success_min_ratio", 0.03)) if cfg else 0.03
        self.lower = np.array(cfg["success_color"][:3], dtype=np.uint8) if cfg and cfg.get("success_color") else None
        self.upper = np.array(cfg["success_color"][3:], dtype=np.uint8) if cfg and cfg.get("success_color") else None

    def match(self, frame: np.ndarray, roi: list[int] | None = None) -> dict:
        """返回 {success_ratio: float}，未启用时返回空 dict。"""
        if not self.enable or self.lower is None:
            return {}
        sub = frame
        if roi:
            x, y, w, h = [int(v) for v in roi]
            sub = frame[y : y + h, x : x + w]
        hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        total = mask.size
        if total == 0:
            return {"success_ratio": 0.0}
        return {"success_ratio": float(cv2.countNonZero(mask)) / total}

    @property
    def hit(self) -> bool:
        return False

    def _make_hit(self, ratio: float) -> bool:
        return ratio >= self.min_ratio
