import json
import queue
import threading
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.auth_jwt import get_current_user
from backend.config import settings
from backend.exceptions import bad_request
from backend.schemas.sync import (
    ParseConnectionUrlRequest,
    SyncExportResponse,
    SyncLogEntry,
    SyncRunResponse,
    SyncSettings,
    SyncSettingsResponse,
    SyncTestResponse,
)
from backend.services.remote_sync import SyncResult, sync_sqlite_to_postgres, test_remote_connection
from backend.services.sync_connection_url import parse_connection_url
from backend.services.sync_settings_store import (
    DEFAULT_EXPORT_NAME,
    load_sync_settings_with_source,
    save_sync_settings,
    save_sync_settings_to_file,
)

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncExportRequest(BaseModel):
    settings: SyncSettings
    target_path: str = Field(min_length=1)


@router.get("/settings", response_model=SyncSettingsResponse)
def get_sync_settings(_: str = Depends(get_current_user)) -> SyncSettingsResponse:
    loaded, source = load_sync_settings_with_source()
    return SyncSettingsResponse(settings=loaded, source_file=source)


@router.put("/settings", response_model=SyncSettings)
def put_sync_settings(
    body: SyncSettings,
    _: str = Depends(get_current_user),
) -> SyncSettings:
    return save_sync_settings(body)


@router.post("/parse-url", response_model=SyncSettings)
def parse_url(
    body: ParseConnectionUrlRequest,
    _: str = Depends(get_current_user),
) -> SyncSettings:
    try:
        return parse_connection_url(body.url)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/export", response_model=SyncExportResponse)
def export_sync_settings(
    body: SyncExportRequest,
    _: str = Depends(get_current_user),
) -> SyncExportResponse:
    try:
        target = Path(body.target_path.strip())
    except (TypeError, ValueError) as exc:
        raise bad_request("保存路径无效") from exc

    if target.suffix.lower() != ".json":
        target = target.with_suffix(".json")

    saved = save_sync_settings_to_file(body.settings, target)
    return SyncExportResponse(
        saved_path=str(saved),
        message=f"连接配置已导出到 {saved}",
    )


@router.get("/export-default-name")
def export_default_name(_: str = Depends(get_current_user)) -> dict:
    return {
        "filename": DEFAULT_EXPORT_NAME,
        "app_dir": str(settings.database_path.parent.parent),
    }


@router.post("/test", response_model=SyncTestResponse)
def test_connection(
    body: SyncSettings,
    _: str = Depends(get_current_user),
) -> SyncTestResponse:
    save_sync_settings(body)
    connected, duration_ms, message, sql_checks, tables, latest_sync_time = (
        test_remote_connection(body)
    )
    return SyncTestResponse(
        connected=connected,
        duration_ms=round(duration_ms, 1),
        message=message,
        sql_checks=sql_checks,
        tables=tables,
        latest_sync_time=latest_sync_time,
    )


def _ndjson_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _stream_sync(sqlite_path: str, body: SyncSettings) -> Iterator[str]:
    """在工作线程执行同步，主生成器按日志到达顺序推送 NDJSON。"""
    event_q: queue.Queue[tuple[str, object]] = queue.Queue()

    def on_log(entry: SyncLogEntry) -> None:
        event_q.put(("log", entry))

    def worker() -> None:
        try:
            result = sync_sqlite_to_postgres(sqlite_path, body, on_log=on_log)
            event_q.put(("done", result))
        except Exception as exc:  # pragma: no cover - 兜底，避免流挂死
            fallback = SyncResult(success=False, message=f"同步线程异常: {exc}")
            fallback.log(fallback.message, "error")
            event_q.put(("done", fallback))

    thread = threading.Thread(target=worker, name="sqlite-pg-sync", daemon=True)
    thread.start()

    while True:
        kind, payload = event_q.get()
        if kind == "log":
            entry = payload  # type: SyncLogEntry
            assert isinstance(entry, SyncLogEntry)
            yield _ndjson_line(
                {"type": "log", "level": entry.level, "message": entry.message}
            )
        else:
            result = payload  # type: SyncResult
            assert isinstance(result, SyncResult)
            yield _ndjson_line(
                {
                    "type": "done",
                    "success": result.success,
                    "message": result.message,
                    "logs": [e.model_dump() for e in result.logs],
                }
            )
            break


@router.post("/run")
def run_sync(
    body: SyncSettings,
    _: str = Depends(get_current_user),
) -> StreamingResponse:
    """NDJSON 流式同步：每行一条事件（log / done），避免阻塞 UI 等待整批日志。"""
    if not settings.database_path.exists():
        raise bad_request("本地数据库不存在，请先在登录页初始化数据库")

    save_sync_settings(body)
    return StreamingResponse(
        _stream_sync(str(settings.database_path), body),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/run-sync", response_model=SyncRunResponse)
def run_sync_blocking(
    body: SyncSettings,
    _: str = Depends(get_current_user),
) -> SyncRunResponse:
    """兼容旧客户端：一次性返回全部日志（会阻塞至结束）。"""
    if not settings.database_path.exists():
        raise bad_request("本地数据库不存在，请先在登录页初始化数据库")

    save_sync_settings(body)
    result = sync_sqlite_to_postgres(str(settings.database_path), body)
    return SyncRunResponse(
        success=result.success,
        message=result.message,
        logs=result.logs,
    )
