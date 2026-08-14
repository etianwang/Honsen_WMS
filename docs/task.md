# Honsen WMS 桌面版 — 任务清单

> 技术栈：**React (Next.js)** → 本地 **FastAPI** → `db_manager.py` → SQLite → **pywebview exe**  
> 状态图例：[ ] 未开始 · [~] 进行中 · [OK] 完成 · [=] 暂停

> **不是浏览器 Web 部署**：API 仅监听 `127.0.0.1`，由 pywebview 窗口加载，最终 PyInstaller 打成 exe。  
> **PyQt6 界面**：已下线（原 `login.py`/`main.py` 等文件已从仓库移除，历史版本见 Git 记录）。

---

## Phase 0 — 文档与约定

| # | 任务 | 状态 |
|---|------|------|
| 0.1 | 产品文档 `docs/PD.md`（React 桌面 exe） | [OK] |
| 0.2 | 界面规范 `docs/ui-spec.md`（React） | [OK] |
| 0.3 | 任务清单 `docs/task.md` | [OK] |
| 0.4 | 数据库说明 `docs/database-policy.md` | [OK] |

---

## Phase 1 — 后端 API（本地 FastAPI）

| # | 任务 | 状态 |
|---|------|------|
| 1.1 | `backend/` 骨架、JWT 认证 | [OK] |
| 1.2 | 库存 / 配置 / 交易 / 导入导出 API | [OK] |
| 1.3 | 入库必填来源柜号校验 | [OK] |
| 1.4 | FastAPI 托管前端静态资源 `frontend/out` | [OK] |
| 1.5 | 打包后 `db/` 路径指向 exe 同目录 | [OK] |
| 1.6 | 后端单元测试 | [ ] |

---

## Phase 2 — React 前端（Next.js）

| # | 任务 | 状态 |
|---|------|------|
| 2.1 | 登录页、AppShell、设计 Token | [OK] |
| 2.2 | 库存页（列表 + 右侧面板） | [OK] |
| 2.3 | 交易页（筛选 + 表格 + 出入库 + 冲销/删除） | [OK] |
| 2.4 | 设置页（配置 + CSV 导入导出 + 改密码） | [OK] |
| 2.5 | 静态导出 `output: 'export'`，API 同源 | [OK] |
| 2.6 | Toast、加载态、行内确认 | [OK] |

---

## Phase 3 — 桌面壳与打包

| # | 任务 | 状态 |
|---|------|------|
| 3.1 | `desktop/launcher.py`（uvicorn + pywebview） | [OK] |
| 3.2 | `desktop/honsen_wms.spec` + `scripts/build-desktop.ps1` | [OK] |
| 3.3 | 构建 `dist/Honsen WMS.exe` 并冒烟测试 | [ ] |
| 3.4 | 未装 Python 的 Windows 10+ 验证 | [ ] |
| 3.5 | 登录页「初始化数据库」（`POST /api/system/init`） | [OK] |

---

## Phase 4 — 业务对齐与验收

| # | 任务 | 状态 |
|---|------|------|
| 4.1 | 柜号规则与 PyQt6 一致（来源柜号、不改 inventory.cabinet） | [OK] |
| 4.2 | 完整流程 UAT：登录 → 库存 → 出入库 → 冲销 → CSV | [ ] |
| 4.3 | 下线 PyQt6 入口（根目录 `login.py`/`main.py` 等旧文件已删除） | [OK] |

---

## Phase 5 — 批量操作 UI（Sprint 2026-07-25）

> 目标：为已有后端批量 API 补齐前端界面。测试规则见 `docs/test-rules.md`（BATCH-*）。

### TASK 5.1 库存批量编辑 UI（`PATCH /api/inventory/batch`）

- [x] 新组件 `InventoryBatchEditPanel`：字段勾选启用（类别/专业/单位/最小库存/位置/柜号），未勾选字段不提交
- [x] 库存页工具栏在多选时显示「批量编辑 (N)」按钮，打开右侧批量面板
- [x] 提交成功后刷新列表、清空选中、Toast 显示更新条数
- [x] 不修改 `InventoryPanel` 及现有单条 CRUD / 批量删除逻辑
- [ ] 自动化用例通过（BATCH-INV-01 ~ 03）—— 用例已写入 selftest，因 shell 环境故障未能执行，待环境恢复后运行 `python scripts/selftest_api.py`

### TASK 5.2 批量出入库 UI（`POST /api/transactions/batch`）

- [x] 新组件 `BatchTransactionPanel`：共享来源柜号/接收人 + 多行（物品 + 数量）可增删
- [x] 交易页工具栏新增「批量入库」「批量出库」按钮
- [x] 出库前端预校验库存不足并提示（同一物品多行按合计校验）；提交成功后刷新交易与库存
- [x] 不修改 `TransactionPanel` 及现有单笔出入库 / 冲销 / 删除逻辑
- [ ] 自动化用例通过（BATCH-TX-01 ~ 04）—— 用例已写入 selftest，因 shell 环境故障未能执行，待环境恢复后运行 `python scripts/selftest_api.py`

---

## 已取消

| # | 任务 | 状态 |
|---|------|------|
| X.1 | 内网浏览器独立部署（非 exe） | [ERR] |

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
