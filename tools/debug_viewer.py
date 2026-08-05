"""调试预览工具：实时抓帧 + 标注匹配结果，可调阈值即时生效。

用法:  .venv\\Scripts\\python.exe tools\\debug_viewer.py
  - 每帧运行模板匹配并画出匹配框 + 置信度
  - 键 1/2/3: 调整选中模板阈值 | 键 +/-: 切模板 | 键 T: 切换显示
  - Q: 退出
"""
from __future__ import annotations

import time

import cv2
import yaml

from capture.screen import ScreenCapture, enable_utf8_console
from vision.preprocess import downsample
from vision.matcher import TemplateMatcher

WIN = "debug_viewer"


def main() -> None:
    enable_utf8_console()
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    cap = ScreenCapture(cfg["capture"].get("monitor", 0))
    matcher = TemplateMatcher(cfg["vision"]["templates"], cfg["capture"]["target_width"])
    if not matcher.names:
        print("[!] 无可用模板，请先用 tools/capture_template.py 截图模板")
        return

    names = matcher.names
    idx = 0
    show_all = True
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    print(f"当前模板: {names}")
    print("键 1/2: 阈值 -0.05/+0.05 | 键 +/-: 切换模板 | 键 T: 全显/单显 | Q: 退出")
    while True:
        frame = cap.grab()
        if frame is None:
            time.sleep(0.1)
            continue
        small, _ = downsample(frame, cfg["capture"]["target_width"])
        results = matcher.match(small)
        cur = names[idx]
        th = matcher.thresholds[cur]
        vis = frame.copy()
        for name, r in results.items():
            if show_all or name == cur:
                x, y, w, h = r.rect
                color = (0, 255, 0) if r.score >= matcher.thresholds[name] else (0, 0, 255)
                cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
                cv2.putText(vis, f"{name} {r.score:.2f}/{matcher.thresholds[name]:.2f}",
                            (x, max(0, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        cv2.putText(vis, f"[{cur}] th={th:.2f} | 1/2: +-0.05 | +/-: switch | T: mode | Q: quit",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        cv2.imshow(WIN, vis)
        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("1"):
            matcher.set_threshold(cur, max(0.0, th - 0.05))
        elif key == ord("2"):
            matcher.set_threshold(cur, min(1.0, th + 0.05))
        elif key in (ord("="), ord("+")):
            idx = (idx + 1) % len(names)
        elif key == ord("-"):
            idx = (idx - 1) % len(names)
        elif key == ord("t"):
            show_all = not show_all
        elif key == ord("s"):
            stamp = time.strftime("%Y%m%d_%H%M%S")
            p = f"output/debug_view_{stamp}.png"
            cv2.imwrite(p, vis)
            print(f"[OK] 已保存: {p}")
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
