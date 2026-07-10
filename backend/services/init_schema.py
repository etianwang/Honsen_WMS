"""数据库初始化（与 login.initialize_all_schema 逻辑一致，无 PyQt6 依赖）。"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

DEFAULT_LOGIN_USER = "Honsen_Admin"
DEFAULT_LOGIN_PASS_PLAINTEXT = "66778899HONSEN"


def database_has_schema(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_user'"
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def initialize_database(db_path: Path) -> dict:
    """
    创建全新数据库 schema 与默认种子。
    若 admin_user 表已存在则拒绝（与桌面 login 行为一致）。
    """
    if database_has_schema(db_path):
        return {
            "created": False,
            "message": "数据库已存在，并非新库。如需重置请手动删除 db 目录下的 .db 文件。",
        }

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE admin_user (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)
        hashed = hashlib.sha256(DEFAULT_LOGIN_PASS_PLAINTEXT.encode("utf-8")).hexdigest()
        cur.execute(
            "INSERT INTO admin_user (username, password) VALUES (?, ?)",
            (DEFAULT_LOGIN_USER, hashed),
        )

        cur.execute("""
            CREATE TABLE Inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                reference TEXT NOT NULL,
                category TEXT,
                domain TEXT,
                unit TEXT,
                current_stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                location TEXT,
                cabinet TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'REVERSAL-IN', 'REVERSAL-OUT')),
                quantity INTEGER NOT NULL,
                recipient_source TEXT,
                project_ref TEXT,
                FOREIGN KEY (item_id) REFERENCES Inventory(id)
            )
        """)

        cur.execute("""
            CREATE TABLE config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(category, value)
            );
        """)

        seeds = {
            "LOCATION": ["基地仓库", "大仓库", "别墅", "办公楼", "公寓", "其他"],
            "PROJECT": ["日常维护", "别墅", "办公楼", "公寓", "基地", "通用"],
            "UNIT": ["个", "件", "套", "米", "卷", "箱", "KG", "升", "桶", "其他"],
            "CATEGORY": [
                "办公用品", "工具耗材", "安防劳保", "电器设备", "建筑材料",
                "油漆涂料", "五金件", "管件", "电缆线材", "其他",
            ],
            "DOMAIN": ["强电", "弱电", "给排水", "暖通", "土建", "精装", "其他"],
        }
        for category, values in seeds.items():
            for value in values:
                cur.execute(
                    "INSERT OR IGNORE INTO config (category, value) VALUES (?, ?)",
                    (category, value),
                )

        conn.commit()
        return {
            "created": True,
            "message": "数据库初始化成功",
            "default_username": DEFAULT_LOGIN_USER,
            "default_password": DEFAULT_LOGIN_PASS_PLAINTEXT,
        }
    finally:
        cur.close()
        conn.close()
