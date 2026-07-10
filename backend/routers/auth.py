import db_manager
from fastapi import APIRouter, Depends

from backend.auth_jwt import create_access_token, get_current_user
from backend.exceptions import bad_request, unauthorized
from backend.schemas.auth import LoginRequest, LoginResponse, PasswordChangeRequest
from backend.config import settings
from backend.services import db as db_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    if not settings.database_path.exists():
        raise bad_request("数据库不存在，请先初始化数据库")
    if not db_manager.check_admin_credentials(db_service.DB_PATH, body.username, body.password):
        raise unauthorized("账号或密码错误")
    token = create_access_token(body.username)
    return LoginResponse(access_token=token, username=body.username)


@router.put("/password")
def change_password(
    body: PasswordChangeRequest,
    username: str = Depends(get_current_user),
) -> dict:
    if not db_manager.check_admin_credentials(db_service.DB_PATH, username, body.current_password):
        raise unauthorized("当前密码错误")
    if not db_manager.update_admin_password(db_service.DB_PATH, body.new_password):
        raise bad_request("密码更新失败")
    return {"message": "密码已更新"}
