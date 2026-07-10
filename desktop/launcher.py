"""
Honsen WMS 桌面启动器：本地 FastAPI + pywebview 窗口。

开发（需先构建前端）：
    cd frontend && npm run build:desktop
    python desktop/launcher.py

打包入口见 desktop/honsen_wms.spec
"""
from __future__ import annotations

import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def resolve_root() -> Path:
    """开发环境用项目根；PyInstaller 单文件用 _MEIPASS。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def resolve_static_index() -> Path | None:
    root = resolve_root()
    candidates = [
        root / "frontend" / "out" / "index.html",
        Path(__file__).resolve().parent.parent / "frontend" / "out" / "index.html",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def fatal_startup_error(message: str) -> None:
    log_path = Path(sys.executable).resolve().parent / "honsen-wms-error.log"
    try:
        log_path.write_text(message, encoding="utf-8")
    except OSError:
        pass
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "弘盛非洲仓库管理系统", 0x10)
        except Exception:
            pass
    raise SystemExit(message)


ROOT = resolve_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WindowApi:
    """供前端调用的窗口控制 API（最小化 / 最大化 / 关闭）。"""

    # pywebview 桌面壳 · frameless + drag region

    def __init__(self) -> None:
        self._maximized = False

    def minimize(self) -> None:
        import webview

        webview.windows[0].minimize()

    def toggle_maximize(self) -> None:
        import webview

        window = webview.windows[0]
        if self._maximized:
            window.restore()
            self._maximized = False
        else:
            window.maximize()
            self._maximized = True

    def close(self) -> None:
        import webview

        webview.windows[0].destroy()


def find_free_port(host: str, start: int = DEFAULT_PORT, end: int = 8010) -> int:
    for port in range(start, end + 1):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if probe.connect_ex((host, port)) == 0:
                continue
        finally:
            probe.close()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    fatal_startup_error(f"无法在 {start}-{end} 范围内找到可用端口，请关闭占用端口的程序后重试。")


def _wait_for_server(health_url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def _run_api(port: int) -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=port,
        log_level="warning",
        access_log=False,
    )


def main() -> None:
    import webview

    if resolve_static_index() is None:
        fatal_startup_error(
            "未找到前端静态资源。\n"
            "请重新执行打包脚本：scripts/build-desktop.ps1"
        )

    port = find_free_port(HOST)
    start_url = f"http://{HOST}:{port}/"
    health_url = f"http://{HOST}:{port}/health"

    server = threading.Thread(target=_run_api, args=(port,), daemon=True)
    server.start()

    if not _wait_for_server(health_url):
        fatal_startup_error(f"本地 API 启动失败（端口 {port}）。请查看 honsen-wms-error.log。")

    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True

    api = WindowApi()
    webview.create_window(
        "弘盛非洲仓库管理系统",
        start_url,
        width=1280,
        height=800,
        min_size=(1024, 640),
        frameless=True,
        easy_drag=False,
        js_api=api,
    )
    webview.start()


if __name__ == "__main__":
    main()
