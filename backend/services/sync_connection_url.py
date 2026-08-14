"""解析 PostgreSQL 连接字符串（支持 Neon 等云数据库）。"""
from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from backend.schemas.sync import SyncSettings


def parse_connection_url(url: str) -> SyncSettings:
    raw = url.strip()
    if not raw:
        raise ValueError("连接字符串不能为空")

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    parsed = urlparse(raw)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError("仅支持 postgresql:// 或 postgres:// 连接字符串")

    if not parsed.hostname:
        raise ValueError("连接字符串缺少主机地址")

    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    db_name = unquote((parsed.path or "/").lstrip("/") or "postgres")
    query = parse_qs(parsed.query)
    sslmode = (query.get("sslmode") or ["prefer"])[0]

    return SyncSettings(
        host=parsed.hostname,
        db_name=db_name,
        port=parsed.port or 5432,
        user=username,
        password=password,
        connect_timeout=5,
        sslmode=sslmode,
    )
