import db_manager
from fastapi import APIRouter

from backend.config import settings
from backend.exceptions import bad_request
from backend.services import db as db_service
from backend.services.init_schema import database_has_schema, initialize_database

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def system_status() -> dict:
    exists = settings.database_path.exists()
    has_schema = database_has_schema(settings.database_path) if exists else False
    return {
        "database_path": str(settings.database_path),
        "database_exists": exists,
        "schema_ready": has_schema,
    }


@router.post("/init")
def init_database() -> dict:
    result = initialize_database(settings.database_path)
    if not result["created"]:
        raise bad_request(result["message"])
    if settings.database_path.exists():
        try:
            db_manager.enable_wal_mode(db_service.DB_PATH)
        except Exception:
            pass
    return result
