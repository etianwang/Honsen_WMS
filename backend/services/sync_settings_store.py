"""本地同步配置：仅扫描 exe 同目录下的 JSON，找不到则留空。"""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import settings
from backend.schemas.sync import SyncSettings

SETTINGS_FILE = "sync_settings.json"
PROFILE_TYPE = "honsen_wms_postgresql_sync"
DEFAULT_EXPORT_NAME = "postgresql_sync.json"


def app_dir() -> Path:
    return settings.database_path.parent.parent


def settings_path() -> Path:
    return app_dir() / SETTINGS_FILE


def build_export_document(settings_obj: SyncSettings) -> dict:
    return {
        "type": PROFILE_TYPE,
        "version": 1,
        **settings_obj.model_dump(),
    }


def parse_sync_document(data: dict) -> SyncSettings | None:
    payload = data
    if data.get("type") == PROFILE_TYPE:
        payload = {key: data[key] for key in SyncSettings.model_fields if key in data}
    try:
        parsed = SyncSettings.model_validate(payload)
    except ValueError:
        return None
    if not parsed.host.strip():
        return None
    return parsed


def read_profile_file(path: Path) -> SyncSettings | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return parse_sync_document(data)
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def discover_sync_settings() -> tuple[SyncSettings, str | None]:
    """仅检索 exe 同目录下的 JSON；检测不到则返回空配置。"""
    candidates: list[tuple[float, Path, SyncSettings]] = []
    for path in app_dir().glob("*.json"):
        parsed = read_profile_file(path)
        if parsed:
            candidates.append((path.stat().st_mtime, path, parsed))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        _, path, parsed = candidates[0]
        return parsed, str(path.resolve())

    return SyncSettings(), None


def load_sync_settings() -> SyncSettings:
    settings_obj, _ = discover_sync_settings()
    return settings_obj


def load_sync_settings_with_source() -> tuple[SyncSettings, str | None]:
    return discover_sync_settings()


def save_sync_settings(settings_obj: SyncSettings) -> SyncSettings:
    path = settings_path()
    path.write_text(
        json.dumps(build_export_document(settings_obj), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return settings_obj


def save_sync_settings_to_file(settings_obj: SyncSettings, target: Path) -> Path:
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_export_document(settings_obj), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target
