#!/usr/bin/env python3
"""
辅助工具：截图 & 坐标获取
用于制作模板图像和确定点击坐标

用法:
  python capture_tool.py screenshot           # 全屏截图
  python capture_tool.py coords               # 实时显示鼠标坐标
  python capture_tool.py crop <x> <y> <w> <h> <output.png>  # 裁剪区域保存为模板
"""

import sys
import time
from pathlib import Path

import pyautogui
from PIL import Image


def take_screenshot(output: str = None):
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = output or f"screenshot_{ts}.png"
    img = pyautogui.screenshot()
    img.save(path)
    print(f"截图已保存: {path}  ({img.width}x{img.height})")
    return path


def show_coords():
    print("实时坐标追踪（按 Ctrl+C 退出）：")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\r  坐标: ({x:4d}, {y:4d})", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n退出坐标追踪")


def crop_region(x: int, y: int, w: int, h: int, output: str):
    """截取屏幕指定区域并保存为模板图像"""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot(region=(x, y, w, h))
    img.save(output)
    print(f"区域截图已保存: {output}  ({w}x{h})")


def interactive_crop():
    """交互式裁剪：先截全图，再手动输入区域坐标"""
    print("先截取全屏...")
    path = take_screenshot()
    print(f"\n请查看截图 {path}，然后输入要裁剪的区域：")
    x = int(input("  左上角 X: "))
    y = int(input("  左上角 Y: "))
    w = int(input("  宽度 W: "))
    h = int(input("  高度 H: "))

    Path("templates").mkdir(exist_ok=True)
    name = input("  模板名称（不含扩展名）: ").strip() or "template"
    out = f"templates/{name}.png"
    crop_region(x, y, w, h, out)
    print(f"\n模板已保存，可在 config.yaml 中引用: {out}")


def main():
    args = sys.argv[1:]

    if not args or args[0] == "screenshot":
        out = args[1] if len(args) > 1 else None
        take_screenshot(out)

    elif args[0] == "coords":
        show_coords()

    elif args[0] == "crop":
        if len(args) == 6:
            crop_region(int(args[1]), int(args[2]), int(args[3]), int(args[4]), args[5])
        else:
            interactive_crop()

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
