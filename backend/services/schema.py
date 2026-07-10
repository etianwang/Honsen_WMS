"""Read-only checks against the legacy SQLite schema (PyQt6 / login.py)."""

import sqlite3

from backend.config import settings

# 与 login.py `initialize_all_schema` 保持一致，Web 端不得擅自增表/改表
EXPECTED_TABLES = frozenset({"admin_user", "Inventory", "transactions", "config"})

INVENTORY_COLUMNS = frozenset({
    "id", "name", "reference", "category", "domain", "unit",
    "current_stock", "min_stock", "location", "cabinet",
})


def validate_schema(db_path: str | None = None) -> dict:
    """
    只读校验：确认现有库表结构与桌面版一致。
    不执行 CREATE / ALTER / 迁移。
    """
    path = db_path or str(settings.database_path)
    result = {
        "schema_ok": False,
        "tables_found": [],
        "missing_tables": [],
        "inventory_columns_ok": False,
        "message": "",
    }

    if not settings.database_path.exists():
        result["message"] = "数据库文件不存在（请沿用 PyQt6 登录页「初始化数据库」或复制现有 db 文件）"
        return result

    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        result["tables_found"] = sorted(tables)
        result["missing_tables"] = sorted(EXPECTED_TABLES - tables)

        if result["missing_tables"]:
            result["message"] = f"缺少表: {', '.join(result['missing_tables'])}"
            return result

        cursor.execute("PRAGMA table_info(Inventory)")
        inv_cols = {row[1] for row in cursor.fetchall()}
        missing_cols = INVENTORY_COLUMNS - inv_cols
        extra_cols = inv_cols - INVENTORY_COLUMNS
        result["inventory_columns_ok"] = not missing_cols
        if missing_cols:
            result["message"] = f"Inventory 缺少列: {', '.join(sorted(missing_cols))}"
            return result
        if extra_cols:
            # 允许多余列（历史迁移残留），但不主动写入
            result["message"] = f"兼容模式：Inventory 含额外列 {', '.join(sorted(extra_cols))}"

        result["schema_ok"] = True
        if not result["message"]:
            result["message"] = "与桌面版 schema 一致"
        return result
    finally:
        conn.close()
