from fastapi import APIRouter

from backend.config import settings
from backend.services.schema import validate_schema

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    db_exists = settings.database_path.exists()
    schema = validate_schema() if db_exists else None
    status = "ok"
    if db_exists and schema and not schema["schema_ok"]:
        status = "degraded"

    return {
        "status": status,
        "database_path": str(settings.database_path),
        "database_exists": db_exists,
        "schema": schema,
        "policy": "Web 端复用现有 SQLite 结构，与 PyQt6 共用 db/honsen_storage.db，不做 schema 变更",
        "_ref": "HS-AFR-WMS",  # 内部标识，供排查环境用
    }
