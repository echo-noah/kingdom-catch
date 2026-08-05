"""模板匹配：加载/热重载模板，逐帧匹配，返回置信度与位置。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from vision.preprocess import downsample, to_gray

METHOD = cv2.TM_CCOEFF_NORMED


@dataclass
class MatchResult:
    score: float
    rect: tuple[int, int, int, int]  # x, y, w, h（帧坐标）


class TemplateMatcher:
    def __init__(self, templates_cfg: dict, target_width: int = 1280):
        self.target_width = target_width
        self._templates: dict[str, dict] = {}
        self._warnings: list[str] = []
        self.reload(templates_cfg)

    def reload(self, templates_cfg: dict) -> None:
        self._templates = {}
        self._warnings = []
        for name, spec in (templates_cfg or {}).items():
            path = Path(spec["path"])
            if not path.exists():
                self._warnings.append(f"模板缺失，已跳过: {name} ({path})")
                continue
            img = cv2.imread(str(path))
            if img is None:
                self._warnings.append(f"模板读取失败: {name} ({path})")
                continue
            th = float(spec.get("threshold", 0.80))
            self._templates[name] = {"img": img, "gray": to_gray(img), "threshold": th}
            print(f"已加载模板 [{name}] 尺寸 {img.shape[1]}x{img.shape[0]} 阈值 {th:.2f}")
        if self._warnings:
            for w in self._warnings:
                print(f"[warn] {w}")

    @property
    def names(self) -> list[str]:
        return list(self._templates.keys())

    @property
    def thresholds(self) -> dict[str, float]:
        return {n: t["threshold"] for n, t in self._templates.items()}

    def set_threshold(self, name: str, value: float) -> None:
        if name in self._templates:
            self._templates[name]["threshold"] = float(value)

    def match(self, frame: np.ndarray) -> dict[str, MatchResult]:
        """对降采样帧匹配所有模板；分数 <0.9 且发生降采样时回原尺度复核。"""
        small, scale = downsample(frame, self.target_width)
        gray_small = to_gray(small)
        results: dict[str, MatchResult] = {}
        for name, t in self._templates.items():
            if t["gray"].shape[0] > gray_small.shape[0] or t["gray"].shape[1] > gray_small.shape[1]:
                continue
            score, loc = self._match_once(gray_small, t["gray"])
            rect = (int(loc[0] / scale), int(loc[1] / scale),
                    t["img"].shape[1], t["img"].shape[0])
            if score < 0.9 and scale < 1.0:
                gray_full = to_gray(frame)
                if t["gray"].shape[0] <= gray_full.shape[0] and t["gray"].shape[1] <= gray_full.shape[1]:
                    score2, loc2 = self._match_once(gray_full, t["gray"])
                    if score2 > score:
                        score, rect = score2, (loc2[0], loc2[1], t["img"].shape[1], t["img"].shape[0])
            results[name] = MatchResult(score=float(score), rect=rect)
        return results

    @staticmethod
    def _match_once(gray: np.ndarray, tpl: np.ndarray) -> tuple[float, tuple[int, int]]:
        res = cv2.matchTemplate(gray, tpl, METHOD)
        _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
        return float(max_val), max_loc

    def annotate(self, frame: np.ndarray, results: dict[str, MatchResult], threshold: float = 0.0) -> np.ndarray:
        vis = frame.copy()
        for name, r in results.items():
            if r.score < threshold:
                continue
            x, y, w, h = r.rect
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(vis, f"{name} {r.score:.2f}", (x, max(0, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return vis
