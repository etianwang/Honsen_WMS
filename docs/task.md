# Honsen WMS 桌面版 — 任务清单

> 技术栈：**React (Next.js)** → 本地 **FastAPI** → `db_manager.py` → SQLite → **pywebview exe**  
> 状态图例：⬜ 未开始 · 🔄 进行中 · ✅ 完成 · ⏸ 暂停

> **不是浏览器 Web 部署**：API 仅监听 `127.0.0.1`，由 pywebview 窗口加载，最终 PyInstaller 打成 exe。  
> **PyQt6 界面**：过渡期保留，React 功能对齐后下线。

---

## Phase 0 — 文档与约定

| # | 任务 | 状态 |
|---|------|------|
| 0.1 | 产品文档 `docs/PD.md`（React 桌面 exe） | ✅ |
| 0.2 | 界面规范 `docs/ui-spec.md`（React） | ✅ |
| 0.3 | 任务清单 `docs/task.md` | ✅ |
| 0.4 | 数据库说明 `docs/database-policy.md` | ✅ |

---

## Phase 1 — 后端 API（本地 FastAPI）

| # | 任务 | 状态 |
|---|------|------|
| 1.1 | `backend/` 骨架、JWT 认证 | ✅ |
| 1.2 | 库存 / 配置 / 交易 / 导入导出 API | ✅ |
| 1.3 | 入库必填来源柜号校验 | ✅ |
| 1.4 | FastAPI 托管前端静态资源 `frontend/out` | ✅ |
| 1.5 | 打包后 `db/` 路径指向 exe 同目录 | ✅ |
| 1.6 | 后端单元测试 | ⬜ |

---

## Phase 2 — React 前端（Next.js）

| # | 任务 | 状态 |
|---|------|------|
| 2.1 | 登录页、AppShell、设计 Token | ✅ |
| 2.2 | 库存页（列表 + 右侧面板） | ✅ |
| 2.3 | 交易页（筛选 + 表格 + 出入库 + 冲销/删除） | ✅ |
| 2.4 | 设置页（配置 + CSV 导入导出 + 改密码） | ✅ |
| 2.5 | 静态导出 `output: 'export'`，API 同源 | ✅ |
| 2.6 | Toast、加载态、行内确认 | ✅ |

---

## Phase 3 — 桌面壳与打包

| # | 任务 | 状态 |
|---|------|------|
| 3.1 | `desktop/launcher.py`（uvicorn + pywebview） | ✅ |
| 3.2 | `desktop/honsen_wms.spec` + `scripts/build-desktop.ps1` | ✅ |
| 3.3 | 构建 `dist/Honsen WMS.exe` 并冒烟测试 | ⬜ |
| 3.4 | 未装 Python 的 Windows 10+ 验证 | ⬜ |
| 3.5 | 登录页「初始化数据库」（`POST /api/system/init`） | ✅ |

---

## Phase 4 — 业务对齐与验收

| # | 任务 | 状态 |
|---|------|------|
| 4.1 | 柜号规则与 PyQt6 一致（来源柜号、不改 inventory.cabinet） | ✅ |
| 4.2 | 完整流程 UAT：登录 → 库存 → 出入库 → 冲销 → CSV | ⬜ |
| 4.3 | 下线 PyQt6 入口（`login.py` 改为 launcher 或文档切换） | ⬜ |

---

## 已取消

| # | 任务 | 状态 |
|---|------|------|
| X.1 | 内网浏览器独立部署（非 exe） | ❌ |

---

## 开发命令速查

```powershell
# 方式 A：前后端分离开发（热更新）
# 终端 1
python -m uvicorn backend.main:app --reload --port 8000
# 终端 2
cd frontend && npm run dev

# 方式 B：桌面预览（需先构建前端）
cd frontend && npm run build:desktop
python desktop/launcher.py

# 打包 exe
.\scripts\build-desktop.ps1
```

---

*最后更新：2026-07-09*
