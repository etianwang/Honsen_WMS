# 数据库策略

React 桌面版通过本地 FastAPI 调用 `db_manager.py`，数据库文件默认位于 **exe 同目录** `db/honsen_storage.db`（开发时为项目根 `db/`）。

> 不做内网 Web 部署；API 仅 `127.0.0.1`。

## 原则

1. **单一 schema** — 表结构以 `login.py` → `initialize_all_schema` 为准。
2. **业务层复用** — 所有读写经 `db_manager.py`，不散落 SQL。
3. **初始化** — 仅登录页「初始化数据库」；不调用 `db_manager.initialize_database()` 作默认种子（与 login 种子不一致）。
4. **WAL** — 登录成功后 `enable_wal_mode()`，提升稳定性。

## 标准表结构

### `admin_user`

| 列 | 类型 |
|----|------|
| id | INTEGER PK |
| username | TEXT UNIQUE |
| password | TEXT (SHA256 hex) |

### `Inventory`

| 列 | 类型 |
|----|------|
| id | INTEGER PK AUTOINCREMENT |
| name | TEXT NOT NULL |
| reference | TEXT NOT NULL |
| category | TEXT |
| domain | TEXT |
| unit | TEXT |
| current_stock | INTEGER DEFAULT 0 |
| min_stock | INTEGER DEFAULT 0 |
| location | TEXT |
| cabinet | TEXT DEFAULT '' |

**唯一性（业务层）**：`(name, reference, location, cabinet)`

**字段语义**：`cabinet` 为仓库**柜号**，与 `location` 一起参与库存唯一键；在新增/编辑库存时维护，**出入库交易时不修改**。

### `transactions`

| 列 | 类型 |
|----|------|
| id | INTEGER PK AUTOINCREMENT |
| item_id | INTEGER FK → Inventory |
| date | TEXT |
| type | TEXT CHECK IN ('IN','OUT','REVERSAL-IN','REVERSAL-OUT') |
| quantity | INTEGER |
| recipient_source | TEXT |
| project_ref | TEXT |

**字段语义**：

| 字段 | 入库 (IN) | 出库 (OUT) |
|------|-----------|------------|
| `recipient_source` | **来源柜号**（从哪条柜子来），必填 | **接收人**，必填 |
| `project_ref` | 通常为空 | 项目编号，可选 |

历史来源柜号可通过 `get_item_cabinet_map()` 从入库交易反查，用于搜索提示。

### `config`

| 列 | 类型 |
|----|------|
| id | INTEGER PK AUTOINCREMENT |
| category | TEXT |
| value | TEXT |
| UNIQUE(category, value) |

## 初始化方式

| 场景 | 做法 |
|------|------|
| 全新部署 | PyQt6 登录页「初始化数据库」 |
| 已有数据 | 将 `db/honsen_storage.db` 放在 exe 同目录或配置路径 |
| 备份 | 复制整个 `db/` 目录 |

## 兼容说明

- 若历史库存在多余列（如旧版 `initial_cabinet`），桌面端忽略、不写入，仅使用上表字段。
- 未来改 schema 须编写迁移脚本，并保证旧库可升级。

---

*最后更新：2026-07-09*
