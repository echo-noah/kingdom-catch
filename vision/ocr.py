"""OCR 兜底：RapidOCR 懒加载，仅事件帧调用；关键词映射结果判定。"""
from __future__ import annotations

from core.events import Outcome


class OcrReader:
    def __init__(self, cfg: dict | None):
        self.enable = bool(cfg and cfg.get("enable", True))
        self.keywords = dict(cfg.get("keywords", {})) if cfg else {}
        self._engine = None

    def _load(self):
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR

                self._engine = RapidOCR()
            except ImportError:
                print("[warn] 未安装 rapidocr-onnxruntime，OCR 兜底已停用。"
                      "可用: pip install rapidocr-onnxruntime")
                self._engine = False
        return self._engine

    def read(self, frame) -> str:
        if not self.enable:
            return ""
        engine = self._load()
        if not engine:
            return ""
        try:
            result, _ = engine(frame)
            if not result:
                return ""
            return "".join(item[1] for item in result)
        except Exception as e:
            print(f"[ocr] 识别失败: {e}")
            return ""

    def classify(self, text: str) -> Outcome | None:
        if not text:
            return None
        for kw, outcome in self.keywords.items():
            if kw in text:
                return Outcome(outcome)
        return None
