import db_manager
from fastapi import APIRouter, Depends

from backend.auth_jwt import get_current_user
from backend.exceptions import bad_request, not_found
from backend.schemas.config import ConfigMap, ConfigValueCreate
from backend.services import config as config_service
from backend.services import db as db_service

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigMap)
def get_config(_: str = Depends(get_current_user)) -> ConfigMap:
    return ConfigMap(**config_service.get_all_config())


@router.get("/{category}")
def get_config_by_category(category: str, _: str = Depends(get_current_user)) -> dict:
    values = db_manager.get_config_options(db_service.DB_PATH, category.upper())
    return {"category": category.upper(), "values": values}


@router.post("/{category}")
def add_config_value(
    category: str,
    body: ConfigValueCreate,
    _: str = Depends(get_current_user),
) -> dict:
    ok = db_manager.insert_config_option(db_service.DB_PATH, category.upper(), body.value)
    if not ok:
        raise bad_request("配置项已存在或插入失败")
    return {"message": "已添加"}


@router.delete("/{category}/{value}")
def delete_config_value(
    category: str,
    value: str,
    _: str = Depends(get_current_user),
) -> dict:
    if not db_manager.delete_config_option(db_service.DB_PATH, category.upper(), value):
        raise not_found("配置项不存在")
    return {"message": "已删除"}
