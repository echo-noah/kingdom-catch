"""Recorder 统计逻辑自测。"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.events import Outcome, StatEvent
from stats.recorder import Recorder


def main():
    with tempfile.TemporaryDirectory() as d:
        rec = Recorder(Path(d) / "stats.csv")
        for i in range(3):
            rec.record(StatEvent("throw", None, float(i)))
        rec.record(StatEvent("result", Outcome.SUCCESS, 1.0))
        rec.record(StatEvent("result", Outcome.FAIL, 2.0))
        rec.record(StatEvent("result", Outcome.FAIL, 3.0))
        s = rec.summary()
        assert s["throws"] == 3 and s["success"] == 1 and s["fail"] == 2 and s["unknown"] == 0
        assert abs(s["success_rate"] - round(1 / 3, 4)) < 1e-6, s
        lines = (Path(d) / "stats.csv").read_text(encoding="utf-8-sig").strip().splitlines()
        assert len(lines) == 1 + 6, len(lines)
        sess = rec.save_session_json()
        assert sess.exists()
    print("[PASS] recorder 统计/CSV/JSON")


if __name__ == "__main__":
    main()
