"""SQLite → PostgreSQL 覆盖同步（整合自 remote_database_sync）。"""
from __future__ import annotations

import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import psycopg2
from psycopg2 import OperationalError

from backend.schemas.sync import SyncLogEntry, SyncSettings, SyncSqlCheck, TableSyncStatus

LogCallback = Callable[[SyncLogEntry], None]

TYPE_MAP = {
    "INT": "BIGINT",
    "INTEGER": "BIGINT",
    "TINYINT": "SMALLINT",
    "SMALLINT": "SMALLINT",
    "MEDIUMINT": "INTEGER",
    "BIGINT": "BIGINT",
    "INT2": "SMALLINT",
    "INT8": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    "NUMERIC": "NUMERIC",
    "DECIMAL": "NUMERIC",
    "TEXT": "TEXT",
    "VARCHAR": "TEXT",
    "CLOB": "TEXT",
    "DATE": "DATE",
    "DATETIME": "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP": "TIMESTAMP WITH TIME ZONE",
    "BLOB": "BYTEA",
    "BOOLEAN": "BOOLEAN",
}


def map_sqlite_type_to_pg(sqlite_type: str) -> str:
    if not sqlite_type:
        return "TEXT"
    clean_type = re.sub(r"\(.*\)", "", sqlite_type).strip().upper()
    return TYPE_MAP.get(clean_type, "TEXT")


def get_connection(settings: SyncSettings):
    return psycopg2.connect(
        host=settings.host.strip(),
        port=settings.port,
        dbname=settings.db_name.strip(),
        user=settings.user.strip(),
        password=settings.password,
        connect_timeout=settings.connect_timeout,
        sslmode=(settings.sslmode or "prefer").strip() or "prefer",
    )


def _init_pg_session(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SET timezone TO 'UTC';")
    conn.commit()


def fetch_pg_table_names(conn) -> list[str]:
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
      AND table_name != 'sync_status'
    ORDER BY table_name;
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]


def create_status_table(conn) -> bool:
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS public.sync_status (
                    table_name TEXT PRIMARY KEY,
                    row_count BIGINT NOT NULL,
                    last_sync_time TIMESTAMP WITH TIME ZONE NOT NULL
                );
                """
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False


def get_table_status(conn, table_names: list[str]) -> dict[str, TableSyncStatus]:
    if not table_names:
        return {}

    status_data: dict[str, TableSyncStatus] = {}
    with conn.cursor() as cursor:
        row_count_queries = [
            f"SELECT '{name}' AS table_name, COUNT(*) AS row_count FROM \"{name}\""
            for name in table_names
        ]
        cursor.execute(" UNION ALL ".join(row_count_queries))
        row_counts = {row[0]: row[1] for row in cursor.fetchall()}

        sync_times: dict[str, str] = {}
        if create_status_table(conn):
            cursor.execute(
                """
                SELECT table_name, last_sync_time AT TIME ZONE 'UTC'
                FROM public.sync_status
                """
            )
            sync_times = {
                row[0]: row[1].strftime("%Y-%m-%d %H:%M:%S") for row in cursor.fetchall()
            }

        for name in table_names:
            status_data[name] = TableSyncStatus(
                row_count=row_counts.get(name, 0),
                last_sync_time=sync_times.get(name, "N/A"),
            )
    return status_data


def update_sync_status(conn, table_name: str, row_count: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO public.sync_status (table_name, row_count, last_sync_time)
            VALUES (%s, %s, NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (table_name)
            DO UPDATE SET row_count = EXCLUDED.row_count,
                          last_sync_time = NOW() AT TIME ZONE 'UTC';
            """,
            (table_name, row_count),
        )
    conn.commit()


def validate_settings(settings: SyncSettings) -> str | None:
    if not settings.host.strip():
        return "请填写远程地址"
    if not settings.db_name.strip():
        return "请填写节点/库名"
    if not settings.user.strip():
        return "请填写账号"
    if not settings.password:
        return "请填写密码"
    return None


def test_remote_connection(
    settings: SyncSettings,
) -> tuple[bool, float, str, list[SyncSqlCheck], dict[str, TableSyncStatus], str | None]:
    err = validate_settings(settings)
    if err:
        return False, 0.0, err, [], {}, None

    start = time.time()
    conn = None
    sql_checks: list[SyncSqlCheck] = []
    try:
        conn = get_connection(settings)
        _init_pg_session(conn)
        duration = time.time() - start

        with conn.cursor() as cursor:
            probe_sql = "SELECT 1"
            cursor.execute(probe_sql)
            row = cursor.fetchone()
            sql_checks.append(
                SyncSqlCheck(
                    name="连通性",
                    sql=probe_sql,
                    ok=True,
                    result=str(row[0]) if row else "ok",
                )
            )

            version_sql = "SELECT version()"
            cursor.execute(version_sql)
            version_row = cursor.fetchone()
            sql_checks.append(
                SyncSqlCheck(
                    name="服务器版本",
                    sql=version_sql,
                    ok=True,
                    result=(version_row[0] if version_row else "")[:160],
                )
            )

        create_status_table(conn)
        table_names = fetch_pg_table_names(conn)
        tables = get_table_status(conn, table_names)
        latest_times = [
            status.last_sync_time
            for status in tables.values()
            if status.last_sync_time and status.last_sync_time != "N/A"
        ]
        latest_sync_time = max(latest_times) if latest_times else None
        return (
            True,
            duration * 1000,
            "远程连接成功",
            sql_checks,
            tables,
            latest_sync_time,
        )
    except OperationalError as exc:
        duration = time.time() - start
        sql_checks.append(
            SyncSqlCheck(name="连通性", sql="connect", ok=False, result=str(exc)[:200])
        )
        return False, duration * 1000, f"PostgreSQL 连接失败: {exc}", sql_checks, {}, None
    except Exception as exc:
        duration = time.time() - start
        sql_checks.append(
            SyncSqlCheck(name="连通性", sql="connect", ok=False, result=str(exc)[:200])
        )
        return False, duration * 1000, f"连接测试失败: {exc}", sql_checks, {}, None
    finally:
        if conn:
            conn.close()


@dataclass
class SyncResult:
    success: bool
    message: str
    logs: list[SyncLogEntry] = field(default_factory=list)
    _on_log: LogCallback | None = field(default=None, repr=False, compare=False)

    def log(self, message: str, level: str = "info") -> None:
        entry = SyncLogEntry(level=level, message=message)
        self.logs.append(entry)
        if self._on_log is not None:
            self._on_log(entry)


def sync_sqlite_to_postgres(
    sqlite_path: str,
    settings: SyncSettings,
    on_log: LogCallback | None = None,
) -> SyncResult:
    result = SyncResult(success=False, message="", _on_log=on_log)
    err = validate_settings(settings)
    if err:
        result.message = err
        result.log(err, "error")
        return result

    pg_conn = None
    local_conn = None
    try:
        result.log("正在连接远程 PostgreSQL...", "info")
        pg_conn = get_connection(settings)
        _init_pg_session(pg_conn)

        if not create_status_table(pg_conn):
            result.message = "无法创建状态记录表，同步终止"
            result.log(result.message, "error")
            return result

        result.log("正在读取本地 SQLite 数据库...", "info")
        local_conn = sqlite3.connect(sqlite_path)
        local_cursor = local_conn.cursor()
        local_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        local_tables = [row[0] for row in local_cursor.fetchall()]
        if not local_tables:
            result.message = "本地数据库中没有用户表，同步取消"
            result.log(result.message, "error")
            return result

        result.log(f"发现 {len(local_tables)} 张本地表，开始覆盖同步...", "info")
        pg_cursor = pg_conn.cursor()
        pg_tables = fetch_pg_table_names(pg_conn)

        for table_name in local_tables:
            result.log(f"正在同步表: {table_name}", "info")
            local_cursor.execute(f'SELECT * FROM "{table_name}"')
            rows = local_cursor.fetchall()
            columns = [desc[0] for desc in local_cursor.description]
            cols_str = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(["%s"] * len(columns))

            if table_name in pg_tables:
                pg_cursor.execute(
                    f'TRUNCATE TABLE "public"."{table_name}" RESTART IDENTITY CASCADE;'
                )
            else:
                result.log(f"远程表 {table_name} 不存在，正在创建...", "warning")
                local_cursor.execute(f'PRAGMA table_info("{table_name}")')
                col_info = local_cursor.fetchall()
                col_defs: list[str] = []
                for cid, name, type_str, notnull, _dflt, pk in col_info:
                    pg_type = map_sqlite_type_to_pg(type_str)
                    def_str = f'"{name}" {pg_type}'
                    if notnull:
                        def_str += " NOT NULL"
                    if pk == 1:
                        if cid == 0 and "BIGINT" in pg_type:
                            def_str = f'"{name}" SERIAL PRIMARY KEY'
                        else:
                            def_str += " PRIMARY KEY"
                    col_defs.append(def_str)

                create_sql = (
                    f'CREATE TABLE "public"."{table_name}" ({", ".join(col_defs)});'
                )
                try:
                    pg_cursor.execute(create_sql)
                    pg_conn.commit()
                    result.log(f"表 {table_name} 创建成功", "success")
                except Exception as exc:
                    pg_conn.rollback()
                    result.message = f"远程表 {table_name} 创建失败: {exc}"
                    result.log(result.message, "error")
                    return result

            row_count = len(rows)
            if row_count > 0:
                insert_sql = (
                    f'INSERT INTO "public"."{table_name}" ({cols_str}) '
                    f"VALUES ({placeholders});"
                )
                pg_cursor.executemany(insert_sql, rows)
                pg_conn.commit()
                result.log(f"表 {table_name} 插入 {row_count} 条数据", "success")
                update_sync_status(pg_conn, table_name, row_count)
            else:
                result.log(f"表 {table_name} 为空，跳过数据插入", "warning")
                update_sync_status(pg_conn, table_name, 0)

        result.success = True
        result.message = "所有本地数据已成功同步到远程数据库（覆盖模式）"
        result.log(result.message, "success")
        return result

    except sqlite3.Error as exc:
        result.message = f"本地 SQLite 操作失败: {exc}"
        result.log(result.message, "error")
        return result
    except psycopg2.Error as exc:
        if pg_conn:
            pg_conn.rollback()
        result.message = f"远程 PostgreSQL 同步失败: {exc}"
        result.log(result.message, "error")
        return result
    except Exception as exc:
        result.message = f"同步过程中发生未知错误: {exc}"
        result.log(result.message, "error")
        return result
    finally:
        if local_conn:
            local_conn.close()
        if pg_conn:
            pg_conn.close()
