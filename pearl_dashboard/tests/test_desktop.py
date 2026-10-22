import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from pearl_dashboard import config as config_mod
from pearl_dashboard import desktop
from pearl_dashboard.server import build


def get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, json.loads(r.read())


class BuildTest(unittest.TestCase):
    def start(self):
        ctrl, httpd, url = build(mock=True)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return ctrl, httpd, url

    def setUp(self):
        # build() reads config.yaml if present; keep tests on the defaults and off the proxy
        self.env = mock.patch.dict("os.environ", {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_serves_state_and_detects_running(self):
        _, httpd, url = self.start()
        status, data = get(url + "api/state")
        self.assertEqual(status, 200)
        self.assertTrue("mode" in data or "loading" in data)
        self.assertEqual(desktop.find_running(httpd.server_address[1]), url)

    def test_port_taken_falls_back(self):
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        self.addCleanup(blocker.close)
        taken = blocker.getsockname()[1]
        real_load = config_mod.load

        def load_with_port(*a, **k):
            cfg = real_load(*a, **k)
            cfg["listen_port"] = taken
            return cfg
        with mock.patch("pearl_dashboard.server.config_mod.load", load_with_port):
            _, httpd, url = self.start()
        self.assertNotEqual(httpd.server_address[1], taken)
        self.assertEqual(get(url + "api/state")[0], 200)  # Host check matches the new port

    def test_nothing_running(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        free = s.getsockname()[1]
        s.close()
        self.assertIsNone(desktop.find_running(free, timeout=0.5))


class HelpersTest(unittest.TestCase):
    def test_close_confirm_only_for_real_instances(self):
        self.assertEqual(desktop.needs_close_confirm(None), 0)
        self.assertEqual(desktop.needs_close_confirm({"instances": [{"simulated": True}]}), 0)
        self.assertEqual(desktop.needs_close_confirm({"instances": [{"simulated": False}, {"simulated": True}]}), 1)

    def test_shortcut_points_at_launcher_via_wscript(self):
        ps = desktop.shortcut_script()
        self.assertIn("System32\\wscript.exe", ps)
        self.assertIn(f"Arguments = '\"{desktop.LAUNCHER}\"'", ps)
        self.assertIn(f"WorkingDirectory = '{desktop.REPO}'", ps)
        self.assertIn("pearl.ico", ps)
        self.assertIn("GetFolderPath('Desktop')", ps)
        self.assertIn("Pearl 挖矿.lnk", ps)

    def test_shortcut_quotes_apostrophes(self):
        with mock.patch.object(desktop, "REPO", Path("/home/o'neil/meme")):
            ps = desktop.shortcut_script()
        self.assertIn("o''neil", ps)

    def test_launcher_uses_pythonw_and_session_path(self):
        exe = "/opt/张 三/miniconda3/python.exe"  # Windows paths can't be parsed on the Linux CI
        path = "C:\\conda\\Library\\bin;" * 300 + 'C:\\odd "dir"'
        with mock.patch.object(Path, "exists", return_value=True):
            vbs = desktop.launcher_vbs(exe, path)
        self.assertIn('sh.Exec("""/opt/张 三/miniconda3/pythonw.exe"" -m pearl_dashboard.desktop")', vbs)
        # PATH is rebuilt exactly from short chunks, quotes doubled
        parts = [line.split(" = ", 1)[1].removeprefix("p & ") for line in vbs.splitlines() if line.startswith("p = ")]
        rebuilt = "".join(part[1:-1].replace('""', '"') for part in parts)
        self.assertEqual(rebuilt, path)
        self.assertTrue(all(len(line) < 260 for line in vbs.splitlines() if line.startswith("p = ")))
        self.assertIn('env("PATH") = p', vbs)
        self.assertIn('env("PYTHONUTF8") = "1"', vbs)
        self.assertIn("If code <> 0 And code <> 3 Then", vbs)
        self.assertIn("ex.StdErr.ReadAll", vbs)
        self.assertIn(str(desktop.LOG), vbs)

    def test_launcher_falls_back_to_python_exe(self):
        with mock.patch.object(Path, "exists", return_value=False):
            vbs = desktop.launcher_vbs("/opt/py/python.exe", "")
        self.assertIn('""/opt/py/python.exe""', vbs)

    def test_launcher_file_is_utf16_with_bom(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(desktop, "LAUNCHER", Path(tmp) / "launch.vbs"):
            out = desktop.write_launcher(r"C:\用户\python.exe", "C:\\x")
            raw = out.read_bytes()
        self.assertEqual(raw[:2], b"\xff\xfe")
        self.assertIn("用户", raw.decode("utf-16"))

    def test_install_shortcut_non_windows(self):
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(desktop.install_shortcut(), 1)


class FallbackTest(unittest.TestCase):
    def test_uses_edge_app_mode_when_available(self):
        with mock.patch.object(desktop, "find_edge", return_value="msedge.exe"), \
                mock.patch.object(desktop.subprocess, "Popen") as popen, \
                mock.patch.dict(sys.modules, {"tkinter": None}), \
                mock.patch.object(desktop.threading, "Event") as event:
            desktop.open_fallback("http://127.0.0.1:8080/", None)
        popen.assert_called_once_with(["msedge.exe", "--app=http://127.0.0.1:8080/", "--new-window"])
        event.return_value.wait.assert_called_once()

    def test_default_browser_without_edge(self):
        with mock.patch.object(desktop, "find_edge", return_value=None), \
                mock.patch.object(desktop.webbrowser, "open") as wb, \
                mock.patch.dict(sys.modules, {"tkinter": None}), \
                mock.patch.object(desktop.threading, "Event"):
            desktop.open_fallback("http://127.0.0.1:9/", None)
        wb.assert_called_once_with("http://127.0.0.1:9/")

    def test_run_falls_back_without_pywebview(self):
        with mock.patch.dict(sys.modules, {"webview": None}), \
                mock.patch.object(desktop, "find_running", return_value="http://127.0.0.1:8080/"), \
                mock.patch.object(desktop, "open_fallback") as fb, \
                mock.patch("pearl_dashboard.server.keep_awake"):
            desktop.run()
        fb.assert_called_once_with("http://127.0.0.1:8080/", None)


class StartupTest(unittest.TestCase):
    def test_module_imports_only_stdlib(self):
        # Third-party imports at module level would fail before the log is set up.
        code = ("import sys; sys.modules.update(yaml=None, requests=None, webview=None); "
                "import pearl_dashboard.desktop")
        r = subprocess.run([sys.executable, "-c", code], cwd=desktop.REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_startup_error_exits_with_reported_code(self):
        with mock.patch.object(sys, "argv", ["desktop"]), \
                mock.patch.object(desktop, "run", side_effect=RuntimeError("boom")), \
                mock.patch.object(desktop, "message_box") as box:
            with self.assertRaises(SystemExit) as cm:
                desktop.main()
        self.assertEqual(cm.exception.code, 3)
        self.assertIn("boom", box.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
