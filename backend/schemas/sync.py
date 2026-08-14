from pydantic import BaseModel, Field


class SyncSettings(BaseModel):
    host: str = ""
    db_name: str = "postgres"
    port: int = 5432
    user: str = ""
    password: str = ""
    connect_timeout: int = Field(default=5, ge=1, le=60)
    sslmode: str = "prefer"


class ParseConnectionUrlRequest(BaseModel):
    url: str = Field(min_length=1)


class TableSyncStatus(BaseModel):
    row_count: int
    last_sync_time: str


class SyncSqlCheck(BaseModel):
    name: str
    sql: str
    ok: bool
    result: str


class SyncTestResponse(BaseModel):
    connected: bool
    duration_ms: float
    message: str
    sql_checks: list[SyncSqlCheck] = Field(default_factory=list)
    tables: dict[str, TableSyncStatus] = Field(default_factory=dict)
    latest_sync_time: str | None = None


class SyncLogEntry(BaseModel):
    level: str
    message: str


class SyncRunResponse(BaseModel):
    success: bool
    message: str
    logs: list[SyncLogEntry] = Field(default_factory=list)


class SyncSettingsResponse(BaseModel):
    settings: SyncSettings
    source_file: str | None = None


class SyncExportResponse(BaseModel):
    saved_path: str
    message: str
