#!/usr/bin/env python3
"""
游戏自动化主引擎
用法: python automator.py [--config config.yaml]
"""

import time
import logging
import argparse
import threading
from datetime import datetime
from pathlib import Path

import pyautogui
import yaml
import keyboard

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def setup_logging(cfg: dict) -> logging.Logger:
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO"))
    handlers = [logging.StreamHandler()]
    if log_cfg.get("save_to_file"):
        handlers.append(logging.FileHandler(log_cfg.get("log_file", "automation.log"), encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )
    return logging.getLogger("automator")


class ImageMatcher:
    """截图图像匹配工具"""

    def __init__(self, cfg: dict):
        self.confidence = cfg.get("confidence", 0.85)
        self.grayscale = cfg.get("grayscale", True)
        self.timeout = cfg.get("timeout", 10)

    def find(self, template_path: str, confidence: float = None) -> tuple | None:
        """在屏幕上查找模板图像，返回中心坐标或 None"""
        conf = confidence if confidence is not None else self.confidence
        path = Path(template_path)
        if not path.exists():
            logging.getLogger("automator").warning("模板图像不存在: %s", template_path)
            return None
        try:
            loc = pyautogui.locateOnScreen(str(path), confidence=conf, grayscale=self.grayscale)
            if loc:
                return pyautogui.center(loc)
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            logging.getLogger("automator").debug("图像匹配异常: %s", e)
        return None

    def wait_for(self, template_path: str, timeout: float = None, confidence: float = None) -> tuple | None:
        """等待图像出现，超时返回 None"""
        deadline = time.time() + (timeout if timeout is not None else self.timeout)
        while time.time() < deadline:
            pos = self.find(template_path, confidence)
            if pos:
                return pos
            time.sleep(0.2)
        return None


class ActionExecutor:
    """执行单个动作"""

    def __init__(self, auto_cfg: dict, matcher: ImageMatcher, logger: logging.Logger):
        self.delay = auto_cfg.get("action_delay", 0.3)
        self.click_dur = auto_cfg.get("click_duration", 0.1)
        self.matcher = matcher
        self.log = logger

    def run(self, action: dict) -> bool:
        """执行动作，返回是否成功"""
        atype = action.get("type")
        desc = action.get("description", atype)

        try:
            if atype == "click_image":
                return self._click_image(action, desc)
            elif atype == "click_pos":
                return self._click_pos(action, desc)
            elif atype == "press_key":
                return self._press_key(action, desc)
            elif atype == "wait":
                return self._wait(action, desc)
            elif atype == "wait_image":
                return self._wait_image(action, desc)
            elif atype == "drag":
                return self._drag(action, desc)
            else:
                self.log.warning("未知动作类型: %s", atype)
                return False
        except Exception as e:
            self.log.error("动作 [%s] 执行失败: %s", desc, e)
            return False

    def _click_image(self, action: dict, desc: str) -> bool:
        pos = self.matcher.find(action["image"], action.get("confidence"))
        if pos is None:
            self.log.warning("[%s] 未找到图像: %s", desc, action["image"])
            return False
        self.log.info("[%s] 点击 (%d, %d)", desc, *pos)
        pyautogui.click(pos, duration=self.click_dur)
        time.sleep(self.delay)
        return True

    def _click_pos(self, action: dict, desc: str) -> bool:
        x, y = action["x"], action["y"]
        self.log.info("[%s] 点击固定坐标 (%d, %d)", desc, x, y)
        pyautogui.click(x, y, duration=self.click_dur)
        time.sleep(self.delay)
        return True

    def _press_key(self, action: dict, desc: str) -> bool:
        key = action["key"]
        count = action.get("count", 1)
        self.log.info("[%s] 按键 '%s' x%d", desc, key, count)
        for _ in range(count):
            pyautogui.press(key)
            time.sleep(self.delay)
        return True

    def _wait(self, action: dict, desc: str) -> bool:
        secs = action.get("seconds", 1.0)
        self.log.debug("[%s] 等待 %.1f 秒", desc, secs)
        time.sleep(secs)
        return True

    def _wait_image(self, action: dict, desc: str) -> bool:
        pos = self.matcher.wait_for(
            action["image"],
            timeout=action.get("timeout"),
            confidence=action.get("confidence"),
        )
        if pos is None:
            self.log.warning("[%s] 等待图像超时: %s", desc, action["image"])
            return action.get("optional", False)
        self.log.info("[%s] 检测到图像: %s", desc, action["image"])
        return True

    def _drag(self, action: dict, desc: str) -> bool:
        sx, sy = action["from_x"], action["from_y"]
        ex, ey = action["to_x"], action["to_y"]
        dur = action.get("duration", 0.5)
        self.log.info("[%s] 拖拽 (%d,%d) -> (%d,%d)", desc, sx, sy, ex, ey)
        pyautogui.moveTo(sx, sy, duration=0.2)
        pyautogui.dragTo(ex, ey, duration=dur, button="left")
        time.sleep(self.delay)
        return True


class GameAutomator:
    """游戏自动化主控制器"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        self.log = setup_logging(self.cfg)
        self.log.info("加载配置: %s", config_path)

        auto_cfg = self.cfg.get("automation", {})
        img_cfg = self.cfg.get("image_matching", {})

        if auto_cfg.get("failsafe", True):
            pyautogui.FAILSAFE = True
        else:
            pyautogui.FAILSAFE = False

        self.loop_count = auto_cfg.get("loop_count", 0)
        self.loop_delay = auto_cfg.get("loop_delay", 1.0)
        self.actions = self.cfg.get("actions", [])
        self.conditions = self.cfg.get("conditions", [])

        self.matcher = ImageMatcher(img_cfg)
        self.executor = ActionExecutor(auto_cfg, self.matcher, self.log)

        self._running = False
        self._paused = False
        self._lock = threading.Lock()

        hotkeys = self.cfg.get("hotkeys", {})
        self._start_key = hotkeys.get("start", "F5")
        self._stop_key = hotkeys.get("stop", "F6")

    def _register_hotkeys(self):
        keyboard.add_hotkey(self._start_key, self._toggle_pause)
        keyboard.add_hotkey(self._stop_key, self._stop)
        self.log.info("热键: %s=开始/暂停  %s=停止", self._start_key, self._stop_key)

    def _toggle_pause(self):
        with self._lock:
            self._paused = not self._paused
        state = "暂停" if self._paused else "继续"
        self.log.info("--- %s ---", state)

    def _stop(self):
        self.log.info("收到停止信号，正在退出...")
        self._running = False

    def _check_conditions(self):
        """检查所有条件，满足则执行对应动作组"""
        for cond in self.conditions:
            name = cond.get("name", "未命名条件")
            img = cond.get("image")
            if not img:
                continue
            pos = self.matcher.find(img, cond.get("confidence"))
            if pos:
                self.log.info("触发条件: [%s]", name)
                for act in cond.get("action_group", []):
                    self.executor.run(act)

    def _save_error_screenshot(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"error_{ts}.png"
        pyautogui.screenshot(path)
        self.log.info("已保存错误截图: %s", path)

    def run(self):
        self._register_hotkeys()
        self._running = True
        self.log.info("按 %s 开始，按 %s 停止", self._start_key, self._stop_key)

        loop_idx = 0
        try:
            while self._running:
                if self._paused:
                    time.sleep(0.1)
                    continue

                loop_idx += 1
                self.log.info("===== 第 %d 轮开始 =====", loop_idx)

                # 条件检测
                self._check_conditions()

                # 执行动作序列
                for action in self.actions:
                    if not self._running or self._paused:
                        break
                    self.executor.run(action)

                self.log.info("===== 第 %d 轮完成 =====", loop_idx)

                if self.loop_count > 0 and loop_idx >= self.loop_count:
                    self.log.info("已完成 %d 轮，退出", self.loop_count)
                    break

                time.sleep(self.loop_delay)

        except pyautogui.FailSafeException:
            self.log.warning("触发紧急停止（鼠标移到左上角）")
        except KeyboardInterrupt:
            self.log.info("用户中断")
        except Exception as e:
            self.log.error("运行异常: %s", e, exc_info=True)
            if self.cfg.get("logging", {}).get("screenshot_on_error"):
                self._save_error_screenshot()
        finally:
            keyboard.unhook_all()
            self.log.info("自动化脚本已退出，共执行 %d 轮", loop_idx)


def main():
    parser = argparse.ArgumentParser(description="游戏自动化脚本")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    args = parser.parse_args()

    automator = GameAutomator(args.config)
    automator.run()


if __name__ == "__main__":
    main()
