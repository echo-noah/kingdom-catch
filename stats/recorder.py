"""统计记录：内存计数 + CSV 追加 + 会话 JSON 落盘。"""
from __future__ import annotations

import csv
import json
import time
import uuid
from pathlib import Path

from core.events import Outcome, StatEvent


class Recorder:
    def __init__(self, csv_path: str | Path = "output/stats.csv"):
        self.csv_path = Path(csv_path)
        self.session_id = uuid.uuid4().hex[:8]
        self.started_at = time.time()
        self.throws = 0
        self.success = 0
        self.fail = 0
        self.unknown = 0
        self.events: list[dict] = []

    def record(self, ev: StatEvent) -> None:
        self.events.append({
            "ts": ev.ts, "kind": ev.kind,
            "outcome": ev.outcome.value if ev.outcome else None,
            "confidence": ev.confidence, "detail": ev.detail,
        })
        if ev.kind == "throw":
            self.throws += 1
        elif ev.kind == "result" and ev.outcome is Outcome.SUCCESS:
            self.success += 1
        elif ev.kind == "result" and ev.outcome is Outcome.FAIL:
            self.fail += 1
        elif ev.kind == "result":
            self.unknown += 1
        self._flush_csv(ev)

    def summary(self) -> dict:
        judged = self.success + self.fail
        rate = self.success / judged if judged else 0.0
        return {
            "throws": self.throws,
            "success": self.success,
            "fail": self.fail,
            "unknown": self.unknown,
            "success_rate": round(rate, 4),
        }

    def _flush_csv(self, ev: StatEvent) -> None:
        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            new_file = not self.csv_path.exists()
            with self.csv_path.open("a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if new_file:
                    writer.writerow(["ts", "kind", "outcome", "confidence", "detail"])
                writer.writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ev.ts)),
                    ev.kind,
                    ev.outcome.value if ev.outcome else "",
                    round(ev.confidence, 3),
                    json.dumps(ev.detail, ensure_ascii=False),
                ])
        except Exception as e:
            print(f"[stats] CSV 写入失败: {e}")

    def save_session_json(self) -> Path:
        path = Path("output") / f"session_{self.session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.started_at)),
            "ended_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            **self.summary(),
            "events": self.events,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
