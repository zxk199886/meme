"""Desktop window for the dashboard (Windows first).

    python -m pearl_dashboard.desktop                     # open the window
    python -m pearl_dashboard.desktop --mock              # demo with fake data
    python -m pearl_dashboard.desktop --install-shortcut  # put "Pearl 挖矿" on the desktop

The window shows the same page as the browser dashboard. Closing it exits the program.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.request
import webbrowser
from pathlib import Path

# Only the standard library at module level: anything that can fail to import is loaded
# inside run(), after output has been routed to the log.

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LOG = HERE / "desktop.log"
LAUNCHER = HERE / "launch.vbs"
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
def _vbs_str(s):
    return '"' + str(s).replace('"', '""') + '"'


def launcher_vbs(python_exe=None, path_env=None):
    """VBScript that starts the desktop app the same way it works from PowerShell.

    It reuses this Python (pythonw.exe next to it, so no console and no hidden-window
    tricks) and this session's PATH (conda and similar setups need it). Errors that happen
    before the app can log them are read from stderr and shown in a message box; exit
    code 3 means the app already showed its own.
    """
    exe = Path(python_exe or sys.executable)
    pyw = exe.with_name("pythonw.exe")
    if not pyw.exists():
        pyw = exe
    path_env = os.environ.get("PATH", "") if path_env is None else path_env
    # VBScript lines are kept short: PATH can be thousands of characters.
    chunks = [path_env[i:i + 200] for i in range(0, len(path_env), 200)] or [""]
    path_lines = [f"p = {_vbs_str(chunks[0])}"] + [f"p = p & {_vbs_str(c)}" for c in chunks[1:]]
    return "\r\n".join([
        "' Generated by: python -m pearl_dashboard.desktop --install-shortcut",
        "' Machine-specific. Run that command again after moving Python or this folder.",
        "Option Explicit",
        "Dim sh, env, ex, p, code, msg",
        'Set sh = CreateObject("WScript.Shell")',
        'Set env = sh.Environment("Process")',
        *path_lines,
        'env("PATH") = p',
        'env("PYTHONUTF8") = "1"',
        f"sh.CurrentDirectory = {_vbs_str(REPO)}",
        "On Error Resume Next",
        f"Set ex = sh.Exec({_vbs_str(f'{_vbs_q(pyw)} -m pearl_dashboard.desktop')})",
        # No "_" line continuations anywhere: a stray line ending would break them.
        "If Err.Number <> 0 Then",
        '  msg = "Pearl 启动失败：找不到 Python" & vbCrLf',
        f"  msg = msg & {_vbs_str(pyw)} & vbCrLf & vbCrLf & Err.Description & vbCrLf & vbCrLf",
        '  msg = msg & "在 PowerShell 里重新运行：python -m pearl_dashboard.desktop --install-shortcut"',
        f"  MsgBox msg, vbExclamation, {_vbs_str(TITLE)}",
        "  WScript.Quit 1",
        "End If",
        "On Error GoTo 0",
        "Do While ex.Status = 0: WScript.Sleep 500: Loop",
        "code = ex.ExitCode",
        "If code <> 0 And code <> 3 Then",
        "  msg = ex.StdErr.ReadAll",
        "  If Len(msg) > 1500 Then msg = Right(msg, 1500)",
        '  msg = "Pearl 启动失败（退出码 " & code & "）" & vbCrLf & vbCrLf & msg & vbCrLf',
        f'  msg = msg & "完整日志：" & {_vbs_str(LOG)} & vbCrLf & "把这段文字或日志发给 Claude。"',
        f"  MsgBox msg, vbExclamation, {_vbs_str(TITLE)}",
        "End If",
        "",
    ])


def _vbs_q(path):
    """A path quoted for a command line (the outer VBScript quoting is added by _vbs_str)."""
    return f'"{path}"'


def write_launcher(python_exe=None, path_env=None):
    # UTF-16 with BOM: the only Unicode encoding wscript reads, needed for non-ASCII paths.
    # Written as bytes: text mode on Windows would turn "\r\n" into "\r\r\n".
    LAUNCHER.write_bytes(launcher_vbs(python_exe, path_env).encode("utf-16"))
    return LAUNCHER


def shortcut_script():
    """PowerShell that creates the desktop shortcut pointing at launch.vbs via wscript."""
    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    return "\n".join([
        "$desktop = [Environment]::GetFolderPath('Desktop')",
        "$shell = New-Object -ComObject WScript.Shell",
        f"$lnk = $shell.CreateShortcut((Join-Path $desktop {q(SHORTCUT_NAME + '.lnk')}))",
        "$lnk.TargetPath = (Join-Path $env:SystemRoot 'System32\\wscript.exe')",
        f"$lnk.Arguments = {q(_vbs_str(LAUNCHER))}",
        f"$lnk.WorkingDirectory = {q(REPO)}",
        f"$lnk.IconLocation = {q(ICON)}",
        f"$lnk.Description = {q(TITLE)}",
        "$lnk.Save()",
        "Write-Output (Join-Path $desktop " + q(SHORTCUT_NAME + ".lnk") + ")",
    ])


MOVE_STEPS = """请把代码放到你自己的用户文件夹。打开普通的 PowerShell（不要用管理员），运行：

    cd $HOME
    git clone https://github.com/zxk199886/meme.git
    cd meme
    git checkout claude/eager-keller-wp51iz
    pip install -r pearl_dashboard\\requirements.txt
    python -m pearl_dashboard.desktop --install-shortcut

想保留模拟数据：把旧目录里的 pearl_dashboard\\pearl.sqlite3 复制到新目录的 pearl_dashboard 里。"""


def _under(path, root):
    norm = lambda x: str(x).replace("/", "\\").rstrip("\\").lower() + "\\"  # noqa: E731
    return norm(path).startswith(norm(root))


def location_problem(repo=None, env=None):
    """Why a double-click launch can't work from where the code lives, or None."""
    repo = Path(repo or REPO)
    env = os.environ if env is None else env
    for key in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)"):
        root = env.get(key)
        if root and _under(repo, root):
            return f"代码放在了系统目录 {repo}。双击运行时没有管理员权限，写不了日志和数据。"
    try:
        with tempfile.TemporaryFile(dir=repo / "pearl_dashboard"):
            pass
    except OSError:
        return f"没有权限写入 {repo / 'pearl_dashboard'}。"
    return None


def install_shortcut():
    if sys.platform != "win32":
        print("桌面快捷方式只支持 Windows。其它系统请运行：python -m pearl_dashboard.desktop")
        return 1
    problem = location_problem()
    if problem:
        print(f"没有创建快捷方式：{problem}\n\n{MOVE_STEPS}")
        return 1
    write_launcher()
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", shortcut_script()],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("创建快捷方式失败：\n" + r.stderr)
        return 1
    print(f"已创建：{r.stdout.strip()}\n以后双击桌面上的「{SHORTCUT_NAME}」就能打开。")
    return 0


# ---------------------------------------------------------------- main
def run(mock=False, config_path=None):
    from . import config as config_mod
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
        # Native code writes to fds 1/2 directly; keep that off launch.vbs's stderr pipe
        # (a full pipe would block the app) and in the log instead.
        for fd in (1, 2):
            try:
                os.dup2(log.fileno(), fd)
            except OSError:
                pass
    print(f"--- {datetime.datetime.now():%Y-%m-%d %H:%M:%S} 启动 · {sys.executable} · Python {sys.version.split()[0]}"
          f" · 目录 {os.getcwd()}", file=sys.stderr, flush=True)
    try:
        run(mock=args.mock or os.environ.get("MOCK") == "1", config_path=args.config)
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        message_box(f"Pearl 启动失败：\n\n{tb[-800:]}\n\n完整日志：{LOG}")
        raise SystemExit(3)  # 3 = already reported, launch.vbs won't show a second box


if __name__ == "__main__":
    main()
