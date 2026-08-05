"""主循环：抓帧 → 识别 → 状态机 → 统计输出。

用法:  .venv\\Scripts\\python.exe main.py
  Ctrl+C 优雅退出并落盘会话 JSON。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import yaml

from capture.screen import ScreenCapture, enable_utf8_console
from core.events import Event, EventType, Outcome, StatEvent
from core.state_machine import StateMachine
from stats.recorder import Recorder
from vision.color_detect import ColorDetector
from vision.matcher import TemplateMatcher
from vision.ocr import OcrReader
from vision.preprocess import crop_roi, downsample, frame_diff, to_gray


def load_config() -> dict:
    return yaml.safe_load(open("config.yaml", encoding="utf-8"))


def main() -> None:
    enable_utf8_console()
    cfg = load_config()
    cap = ScreenCapture(cfg["capture"].get("monitor", 0))
    target_w = cfg["capture"]["target_width"]
    fps = max(1, int(cfg["capture"].get("fps", 10)))
    matcher = TemplateMatcher(cfg["vision"]["templates"], target_w)
    color_det = ColorDetector(cfg["vision"].get("color_detect"))
    ocr = OcrReader(cfg["vision"].get("ocr"))
    sm = StateMachine(cfg["state_machine"]["throw_timeout_s"], cfg["state_machine"]["cooldown_s"])
    rec = Recorder(cfg["stats"]["csv_path"])
    save_debug = bool(cfg["stats"].get("save_debug", True))
    debug_dir = Path("output/debug")
    enable_diff = bool(cfg["vision"].get("enable_diff_trigger", False))

    if not matcher.names:
        print("[!] 警告: 无可用模板，请先运行 tools/capture_template.py 截图模板")
        print("[!] 提示: OCR 兜底仍可尝试判定结果")

    print(f"会话 {rec.session_id} 开始 | 显示器 {cap.monitor_index}: {cap.resolution} | {fps}fps")
    print(f"状态机: 丢球超时 {sm.throw_timeout_s}s | 冷却 {sm.cooldown_s}s")
    print("Ctrl+C 退出")

    prev_gray: object | None = None
    last_stats_ts = time.time()
    interval = 1.0 / fps

    def handle_stat(ev: StatEvent) -> None:
        rec.record(ev)
        if ev.kind == "throw":
            print(f"[丢球] #{rec.throws} 置信度 {ev.confidence:.2f}")
        elif ev.outcome:
            print(f"[结果] {ev.outcome.value} (统计中)")

    try:
        while True:
            t0 = time.time()
            frame = cap.grab()
            if frame is None:
                time.sleep(0.05)
                continue

            small, _ = downsample(frame, target_w)
            gray = to_gray(small)

            if enable_diff:
                if prev_gray is not None and frame_diff(prev_gray, gray) < cfg["vision"]["diff_threshold"]:
                    continue
                prev_gray = gray

            results = matcher.match(small)
            now = time.time()
            ev_out: list[Event] = []

            if sm.state_name == "idle":
                ball = results.get("ball_throw")
                if ball and ball.score >= matcher.thresholds["ball_throw"]:
                    ev_out.append(Event(EventType.BALL_THROWN, now, ball.score, {}))
            else:
                best: Event | None = None
                for name, outcome in (("catch_success", Outcome.SUCCESS), ("catch_fail", Outcome.FAIL)):
                    r = results.get(name)
                    if r and r.score >= matcher.thresholds[name]:
                        cand = Event(EventType.RESULT_DETECTED, now, r.score,
                                     {"outcome": outcome, "by": "template"})
                        if best is None or cand.confidence > best.confidence:
                            best = cand
                if best is None:
                    cr = color_det.match(small)
                    ratio = cr.get("success_ratio", 0.0)
                    if ratio >= color_det.min_ratio and color_det.enable:
                        best = Event(EventType.RESULT_DETECTED, now, ratio,
                                     {"outcome": Outcome.SUCCESS, "by": "color", "ratio": ratio})
                if best is None and ocr.enable:
                    text = ocr.read(small)
                    ocr_out = ocr.classify(text)
                    if ocr_out is not None:
                        best = Event(EventType.RESULT_DETECTED, now, 1.0,
                                     {"outcome": ocr_out, "by": "ocr", "text": text})
                        print(f"[ocr] 读到: {text}")
                if best is not None:
                    ev_out.append(best)

            for ev in ev_out:
                for stat in sm.feed(ev):
                    handle_stat(stat)
                    if save_debug:
                        vis = matcher.annotate(frame, results, 0.5)
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        stamp = time.strftime("%Y%m%d_%H%M%S")
                        cv2.imwrite(str(debug_dir / f"{stamp}_{stat.kind}_{stat.outcome or ''}.png"), vis)
            for stat in sm.poll(now):
                handle_stat(stat)

            if time.time() - last_stats_ts >= 1.0:
                s = rec.summary()
                rate = s["success_rate"] * 100
                print(f"[{time.strftime('%H:%M:%S')}] 丢球 {s['throws']} | 成功 {s['success']} | "
                      f"失败 {s['fail']} | 未知 {s['unknown']} | 成功率 {rate:.1f}% | "
                      f"状态 {sm.state_name}")
                last_stats_ts = time.time()

            elapsed = time.time() - t0
            if elapsed < interval:
                time.sleep(interval - elapsed)

    except KeyboardInterrupt:
        print("\n正在退出...")
    finally:
        s = rec.summary()
        print(f"=== 会话 {rec.session_id} 统计 ===")
        print(f"丢球 {s['throws']} | 成功 {s['success']} | 失败 {s['fail']} | "
              f"未知 {s['unknown']} | 成功率 {s['success_rate'] * 100:.1f}%")
        path = rec.save_session_json()
        print(f"已保存会话: {path}")


if __name__ == "__main__":
    sys.exit(main())
