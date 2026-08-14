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


def resolve_app_dir() -> Path:
    """exe 同目录（开发时为项目根）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
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


def ensure_webview2_available() -> None:
    """检测系统 WebView2 Runtime；缺失时提示下载（不内置 Runtime）。"""
    if sys.platform != "win32":
        return
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        )
        winreg.CloseKey(key)
        return
    except OSError:
        pass
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        )
        winreg.CloseKey(key)
        return
    except OSError:
        pass

    fatal_startup_error(
        "未检测到 Microsoft Edge WebView2 Runtime。\n\n"
        "请安装后重试：\n"
        "https://developer.microsoft.com/microsoft-edge/webview2/\n"
        "（选择 Evergreen Standalone Installer）"
    )


ROOT = resolve_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class WindowApi:
    """供前端调用的窗口控制 API（最小化 / 最大化 / 关闭 / 导出保存）。"""

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

    def choose_sync_export_path(self, default_filename: str = "postgresql_sync.json") -> str | None:
        """打开系统保存对话框，供同步配置导出。"""
        import webview
        from webview import FileDialog

        result = webview.windows[0].create_file_dialog(
            FileDialog.SAVE,
            directory=str(resolve_app_dir()),
            save_filename=default_filename,
            file_types=("JSON 配置 (*.json)", "所有文件 (*.*)"),
        )
        if not result:
            return None
        if isinstance(result, (list, tuple)):
            return str(result[0]) if result else None
        return str(result)

    def save_download_file(self, default_filename: str, content_base64: str) -> str | None:
        """桌面端保存导出文件（WebView2 的 a.download 通常无反应）。"""
        import base64

        import webview
        from webview import FileDialog

        result = webview.windows[0].create_file_dialog(
            FileDialog.SAVE,
            directory=str(resolve_app_dir()),
            save_filename=default_filename,
            file_types=("所有文件 (*.*)",),
        )
        if not result:
            return None
        target = str(result[0]) if isinstance(result, (list, tuple)) else str(result)
        Path(target).write_bytes(base64.b64decode(content_base64))
        return target


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

    ensure_webview2_available()

    if resolve_static_index() is None:
        fatal_startup_error(
            "未找到前端静态资源。\n请重新执行打包脚本：scripts/build-desktop.ps1"
        )

    port = find_free_port(HOST)
    # Windows：自绘无边框窗口 + 自定义标题栏（贴合 WebView2 观感）。
    # macOS：用系统原生窗口边框（红绿灯按钮），跳过自绘标题栏/拖拽区，
    # 避免 Cocoa WKWebView 下自定义关闭按钮相关的挂起问题。
    is_windows = sys.platform == "win32"
    platform_hint = "win" if is_windows else "mac"
    start_url = f"http://{HOST}:{port}/?desktop_platform={platform_hint}"
    health_url = f"http://{HOST}:{port}/health"

    server = threading.Thread(target=_run_api, args=(port,), daemon=True)
    server.start()

    if not _wait_for_server(health_url):
        fatal_startup_error(f"本地 API 启动失败（端口 {port}）。请查看 honsen-wms-error.log。")

    if is_windows:
        webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True

    api = WindowApi()
    webview.create_window(
        "弘盛非洲仓库管理系统",
        start_url,
        width=1280,
        height=800,
        min_size=(1024, 640),
        frameless=is_windows,
        easy_drag=False,
        js_api=api,
    )
    webview.start()


if __name__ == "__main__":
    main()
