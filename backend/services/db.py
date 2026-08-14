import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import db_manager  # noqa: E402

from backend.config import settings

DB_PATH = str(settings.database_path)


def ensure_db_dir() -> None:
    """仅确保 db/ 目录存在，不创建或修改表结构。"""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)


def init_db_runtime() -> None:
    """
    启动时仅开启 WAL（与 PyQt6 登录后行为一致）。
    禁止在此调用 initialize_database / ALTER TABLE / 自动迁移。
    表结构初始化请使用桌面端 login.py「初始化数据库」。
    """
    ensure_db_dir()
    if settings.database_path.exists():
        try:
            db_manager.enable_wal_mode(DB_PATH)
        except Exception:
            # enable_wal_mode 内部 print 含 emoji，Windows GBK 控制台可能抛错；WAL 本身通常已生效
            pass
