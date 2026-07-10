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

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = "127.0.0.1"
DEFAULT_PORT = 8000


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
    raise SystemExit(f"无法在 {start}-{end} 范围内找到可用端口，请关闭占用端口的程序后重试。")


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

    static_index = ROOT / "frontend" / "out" / "index.html"
    if not static_index.is_file():
        raise SystemExit(
            "未找到前端构建产物。请先执行：\n"
            "  cd frontend\n"
            "  npm run build:desktop"
        )

    port = find_free_port(HOST)
    start_url = f"http://{HOST}:{port}/"
    health_url = f"http://{HOST}:{port}/health"

    server = threading.Thread(target=_run_api, args=(port,), daemon=True)
    server.start()

    if not _wait_for_server(health_url):
        raise SystemExit(f"本地 API 启动失败（端口 {port}）。")

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
