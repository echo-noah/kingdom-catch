"""交互式模板截图工具。

用法:  .venv\\Scripts\\python.exe tools\\capture_template.py
  - 鼠标拖动框选目标区域（丢球动画帧 / 捕捉成功提示 / 捕捉失败提示）
  - 空格: 保存当前整帧到 output/templates_raw/
  - 回车: 将框选区域裁剪保存到 templates/<名字>.png（按提示输入名字）
  - R: 重置选框 | Q: 退出
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2

from capture.screen import ScreenCapture, enable_utf8_console

WIN = "capture_template"
TEMPLATES_DIR = Path("templates")
RAW_DIR = Path("output/templates_raw")

_sel: list[int] = []
_selection: list[int] = []


def _on_mouse(event, x, y, flags, param) -> None:
    global _sel, _selection
    if event == cv2.EVENT_LBUTTONDOWN:
        _sel = [x, y]
        _selection = []
    elif event == cv2.EVENT_MOUSEMOVE and _sel:
        _selection = [*_sel, x, y]
    elif event == cv2.EVENT_LBUTTONUP:
        if _sel:
            x0, y0 = _sel
            _selection = [x0, y0, x, y]
        _sel = []


def _draw_overlay(frame):
    vis = frame.copy()
    if _selection:
        x0, y0, x1, y1 = _selection
        cv2.rectangle(vis, (min(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)), (0, 255, 0), 2)
    cv2.putText(vis, "L-drag: select | ENTER: save tpl | SPACE: save frame | R: reset | Q: quit",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
    return vis


def _save_template(frame):
    if not _selection:
        print("[!] 请先用鼠标框选区域")
        return
    x0, y0, x1, y1 = sorted(_selection[0::2]), sorted(_selection[1::2])
    name = input("模板名字（如 ball_throw / catch_success / catch_fail）: ").strip()
    if not name:
        print("[!] 名字不能为空")
        return
    crop = frame[y0[0] : y1[0], x0[0] : x1[0]]
    if crop.size == 0:
        print("[!] 选框无效")
        return
    TEMPLATES_DIR.mkdir(exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.png"
    cv2.imwrite(str(path), crop)
    print(f"[OK] 已保存模板: {path} ({crop.shape[1]}x{crop.shape[0]})")


def main() -> None:
    enable_utf8_console()
    TEMPLATES_DIR.mkdir(exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cap = ScreenCapture(0)
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WIN, _on_mouse)
    print(f"显示器 {cap.monitor_index}: {cap.resolution}  按 Q 退出")
    while True:
        frame = cap.grab()
        if frame is None:
            time.sleep(0.1)
            continue
        cv2.imshow(WIN, _draw_overlay(frame))
        key = cv2.waitKey(50) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            _sel.clear()
            _selection.clear()
        elif key == ord(" "):
            stamp = time.strftime("%Y%m%d_%H%M%S")
            p = RAW_DIR / f"raw_{stamp}.png"
            cv2.imwrite(str(p), frame)
            print(f"[OK] 已保存整帧: {p}")
        elif key in (13, 10):  # Enter
            _save_template(frame)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
