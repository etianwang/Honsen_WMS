# Honsen WMS — Web 版运行说明

## 后端 (FastAPI)

```powershell
cd E:\Project\Py\wms
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health（含 schema 只读校验）
- 数据库：项目根目录 `db/honsen_storage.db`（**不改表结构**）

## 数据库策略

- Web 与桌面版 **共用同一 `.db` 文件**
- 启动时 **仅** `enable_wal_mode()`，不建表、不迁移
- 新库初始化请用 React 登录页「初始化数据库」
- 详见 [`docs/database-policy.md`](../docs/database-policy.md)

## 前端 (Next.js)

```powershell
cd E:\Project\Py\wms\frontend
npm install
npm run dev
```

- 访问：http://localhost:3000
- 默认 API 地址见 `frontend/.env.local`

## 默认账号

- 用户名：`Honsen_Admin`
- 密码：`66778899HONSEN`（首次初始化数据库后）

## 目录结构

```
Honsen_WMS/
├── backend/          # FastAPI API 层
├── frontend/         # Next.js Web UI
├── db_manager.py     # 复用业务逻辑
├── data_utility.py   # CSV 工具
├── db/               # SQLite 数据文件
└── docs/             # PD / ui-spec / task
```
