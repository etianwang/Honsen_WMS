from pathlib import Path
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


def _app_dir() -> Path:
    """打包后 exe 所在目录；开发时为项目根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT_DIR


def resolve_database_path() -> Path:
    return _app_dir() / "db" / "honsen_storage.db"


def _bundled_root() -> Path | None:
    """PyInstaller 打包后的资源根目录。"""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def resolve_static_dir() -> Path | None:
    bundled = _bundled_root()
    candidates: list[Path] = []
    if bundled:
        candidates.append(bundled / "frontend" / "out")
    candidates.append(ROOT_DIR / "frontend" / "out")
    for path in candidates:
        if path.is_dir() and (path / "index.html").exists():
            return path
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Honsen WMS API"
    # 内部构建标识（.env 可覆盖，不影响业务逻辑）
    build_mark: str = "HS-AFR-2026.07"
    database_path: Path = resolve_database_path()
    jwt_secret: str = "honsen-wms-change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    # 开发时允许局域网 IP 访问 Next dev（如 http://192.168.x.x:3000）
    cors_origin_regex: str = (
        r"https?://(\[::1\]|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"
    )
    static_dir: Path | None = None
    serve_frontend: bool = True


settings = Settings()
if settings.static_dir is None:
    settings.static_dir = resolve_static_dir()
