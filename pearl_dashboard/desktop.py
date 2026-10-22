"""Desktop window for the dashboard (Windows first).

    python -m pearl_dashboard.desktop                     # open the window
    python -m pearl_dashboard.desktop --mock              # demo with fake data
    python -m pearl_dashboard.desktop --install-shortcut  # put "Pearl 挖矿" on the desktop

The window shows the same page as the browser dashboard. Closing it exits the program.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import traceback
import urllib.request
import webbrowser
from pathlib import Path

from . import config as config_mod

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LOG = HERE / "desktop.log"
ICON = HERE / "static" / "pearl.ico"
TITLE = "Pearl 租卡挖矿"
SHORTCUT_NAME = "Pearl 挖矿"


# ---------------------------------------------------------------- helpers
def message_box(text, title=TITLE, yes_no=False):
    """Native Windows message box (safe from any thread). Elsewhere: print, answer yes."""
    if sys.platform == "win32":
        import ctypes
        MB_YESNO, MB_ICONWARNING, MB_TOPMOST, IDYES = 0x4, 0x30, 0x40000, 6
        flags = MB_ICONWARNING | MB_TOPMOST | (MB_YESNO if yes_no else 0)
        return ctypes.windll.user32.MessageBoxW(None, text, title, flags) == IDYES
    print(f"[{title}] {text}", file=sys.stderr)
    return True


def find_running(port, timeout=1.5):
    """URL of a dashboard already answering on this port, else None."""
    url = f"http://127.0.0.1:{port}/"
    try:
        with urllib.request.urlopen(url + "api/state", timeout=timeout) as r:
            data = json.loads(r.read())
        return url if isinstance(data, dict) and ("mode" in data or "loading" in data) else None
    except Exception:
        return None


def needs_close_confirm(state):
    """Number of real (billed) instances still running, 0 if closing is harmless."""
    return sum(1 for i in (state or {}).get("instances", []) if not i.get("simulated"))


def find_edge():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if base:
            exe = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if exe.exists():
                return str(exe)
    return shutil.which("msedge")


# ---------------------------------------------------------------- windows
def open_webview(url, ctrl):
    import webview  # raises ImportError when pywebview isn't installed

    window = webview.create_window(TITLE, url, width=1280, height=900, min_size=(420, 600),
                                   text_select=True)

    def on_closing():
        n = needs_close_confirm(ctrl.state if ctrl else None)
        if n and not message_box(f"还有 {n} 台真机在计费。\n关掉后它们会继续运行，直到最长寿命到期自毁。\n\n仍然退出？",
                                 yes_no=True):
            return False
        return True

    window.events.closing += on_closing
    webview.start()


def open_fallback(url, ctrl):
    """No pywebview: app-style Edge window (or the default browser) plus a small control window."""
    edge = find_edge()

    def show():
        if edge:
            subprocess.Popen([edge, f"--app={url}", "--new-window"])
        else:
            webbrowser.open(url)

    show()
    try:
        import tkinter as tk
        root = tk.Tk()
    except Exception:  # no tkinter, or no display
        print(f"面板：{url}（按 Ctrl+C 退出）")
        threading.Event().wait()
        return

    root.title(TITLE)
    root.resizable(False, False)
    if ICON.exists() and sys.platform == "win32":
        root.iconbitmap(str(ICON))
    tk.Label(root, text="Pearl 正在运行", font=("Microsoft YaHei", 12, "bold")).pack(padx=24, pady=(16, 4))
    tk.Label(root, text="关掉这个小窗口就会退出程序", fg="#666").pack(padx=24)
    row = tk.Frame(root)
    row.pack(pady=14)

    def quit_app():
        n = needs_close_confirm(ctrl.state if ctrl else None)
        if n and not message_box(f"还有 {n} 台真机在计费，关掉后它们继续运行到寿命到期。仍然退出？", yes_no=True):
            return
        root.destroy()

    tk.Button(row, text="打开面板", width=10, command=show).pack(side="left", padx=6)
    tk.Button(row, text="退出", width=10, command=quit_app).pack(side="left", padx=6)
    root.protocol("WM_DELETE_WINDOW", quit_app)
    root.mainloop()


# ---------------------------------------------------------------- shortcut
def shortcut_script(python_exe=None):
    """PowerShell that creates the desktop shortcut."""
    exe = Path(python_exe or sys.executable)
    target = exe.with_name("pythonw.exe")
    if not target.exists():
        target = exe

    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    return "\n".join([
        "$desktop = [Environment]::GetFolderPath('Desktop')",
        "$shell = New-Object -ComObject WScript.Shell",
        f"$lnk = $shell.CreateShortcut((Join-Path $desktop {q(SHORTCUT_NAME + '.lnk')}))",
        f"$lnk.TargetPath = {q(target)}",
        f"$lnk.Arguments = {q('-m pearl_dashboard.desktop')}",
        f"$lnk.WorkingDirectory = {q(REPO)}",
        f"$lnk.IconLocation = {q(ICON)}",
        f"$lnk.Description = {q(TITLE)}",
        "$lnk.Save()",
        "Write-Output (Join-Path $desktop " + q(SHORTCUT_NAME + ".lnk") + ")",
    ])


def install_shortcut():
    if sys.platform != "win32":
        print("桌面快捷方式只支持 Windows。其它系统请运行：python -m pearl_dashboard.desktop")
        return 1
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", shortcut_script()],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("创建快捷方式失败：\n" + r.stderr)
        return 1
    print(f"已创建：{r.stdout.strip()}\n以后双击桌面上的「{SHORTCUT_NAME}」就能打开。")
    return 0


# ---------------------------------------------------------------- main
def run(mock=False, config_path=None):
    from .server import build, keep_awake

    port = int(config_mod.load(config_path)["listen_port"])
    url, ctrl = find_running(port), None
    if not url:
        ctrl, httpd, url = build(config_path, mock)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
    keep_awake()
    try:
        open_webview(url, ctrl)
    except ImportError:
        open_fallback(url, ctrl)
    except Exception:
        # e.g. WebView2 runtime missing or pythonnet broken: keep going in Edge / the browser.
        print("桌面窗口打不开，改用浏览器：\n" + traceback.format_exc(), file=sys.stderr)
        open_fallback(url, ctrl)


def main():
    ap = argparse.ArgumentParser(description="Pearl 桌面版")
    ap.add_argument("--mock", action="store_true", help="用假数据演示")
    ap.add_argument("--config", help="配置文件路径")
    ap.add_argument("--install-shortcut", action="store_true", help="在桌面创建快捷方式")
    args = ap.parse_args()
    if args.install_shortcut:
        raise SystemExit(install_shortcut())

    # pythonw has no console: keep output in a log file so problems can be reported.
    if sys.stdout is None or sys.stderr is None or os.path.basename(sys.executable).lower() == "pythonw.exe":
        log = open(LOG, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log
    try:
        run(mock=args.mock or os.environ.get("MOCK") == "1", config_path=args.config)
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        message_box(f"Pearl 启动失败：\n\n{tb[-800:]}\n\n完整日志：{LOG}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
