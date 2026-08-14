# Agent Audit Log

> 记录格式：Intent / Changed / Tests / Acceptance / Next。每完成一个 TASK（或明确子步骤）追加一条。

---

## 2026-07-25 — Sprint「批量操作 UI」启动

- **Intent**：为已有后端批量 API 补齐前端 UI：①库存批量编辑（`PATCH /api/inventory/batch`）；②批量出入库（`POST /api/transactions/batch`）。硬约束：不修改现有 `InventoryPanel` / `TransactionPanel` 与单条操作逻辑，新功能以独立组件 + 独立状态接入。
- **Planned tasks**：`docs/task.md` Phase 5（TASK 5.1、TASK 5.2）；测试规则 `docs/test-rules.md`（BATCH-INV-*、BATCH-TX-*、REG-*）。
- **验证方式**：`python scripts/selftest_api.py`（新增批量 API 用例 + 原有用例回归）+ `npm run build` 编译验证。

---

## 2026-07-25 — TASK 5.1 库存批量编辑 UI

- **Intent**：为 `PATCH /api/inventory/batch` 补前端界面。
- **Changed**：
  - 新增 `frontend/src/components/inventory/InventoryBatchEditPanel.tsx`（独立组件，字段勾选启用，未勾选不提交；空提交前端拦截）。
  - `frontend/src/app/(dashboard)/inventory/page.tsx`：新增 `batchEditOpen` 状态、`startBatchEdit`/`batchEdit` 函数、工具栏「批量编辑 (N)」按钮、panel 条件渲染。现有 `InventoryPanel`、单条 CRUD、批量删除代码未改动（仅在 `selectRow`/`startCreate` 追加关闭批量面板一行）。
- **Tests**：BATCH-INV-01~03 已写入 `scripts/selftest_api.py`；**未执行**（shell 环境故障，`echo` 亦无返回，子代理确认同样失败）。
- **Acceptance**：代码完成；自动化验证 pending。
- **Next**：TASK 5.2。

## 2026-07-25 — TASK 5.2 批量出入库 UI

- **Intent**：为 `POST /api/transactions/batch` 补前端界面。
- **Changed**：
  - 新增 `frontend/src/components/transactions/BatchTransactionPanel.tsx`（共享来源柜号/接收人 + 项目（仅 OUT）；多行物品可增删；OUT 按同物品合计预校验库存）。
  - `frontend/src/app/(dashboard)/transactions/page.tsx`：新增 `batchMode` 状态、`startBatch`/`saveBatch` 函数、工具栏「批量入库」「批量出库」按钮、panel 条件渲染。现有 `TransactionPanel` 与单笔出入库/修改/冲销/删除逻辑未改动（仅在 `selectRow`/`startIn`/`startOut` 追加 `setBatchMode("none")`）。
  - `scripts/selftest_api.py`：cleanup 前追加 BATCH-INV-01~03、BATCH-TX-01~04 共 8 个用例（含 setup），测试物品以 `__SELFTEST` 前缀命名，复用既有 cleanup。
- **Tests**：**未执行** —— shell 执行环境故障（所有命令返回 no exit status），需重启环境后运行：
  1. `python scripts/selftest_api.py` → 期望全部 PASS（含 BATCH-*）
  2. `cd frontend && npm run build` → 期望编译零错误
- **Acceptance**：代码完成；两条自动化验证 pending，task.md 对应复选框留空。
- **Next**：环境恢复后执行上述两条命令，通过后勾选 task.md 中「自动化用例通过」两项。

---

## 2026-07-26 — 同步日志流式化（不卡 UI）

- **Intent**：`/api/sync/run` 改为异步流式输出日志，避免点击同步后 UI 卡住、结束后才一次性刷日志。
- **Changed**：
  - `backend/services/remote_sync.py`：`sync_sqlite_to_postgres(..., on_log=)`，每条日志即时回调。
  - `backend/routers/sync.py`：`POST /api/sync/run` 改为 NDJSON `StreamingResponse`（工作线程同步 + 主生成器推送 `log`/`done`）；保留 `POST /api/sync/run-sync` 阻塞兼容。
  - `frontend/src/lib/api.ts`：新增 `streamSyncRun`。
  - `frontend/src/app/(dashboard)/sync/page.tsx`：逐行追加日志、自动滚底、「同步进行中」提示。
  - `scripts/selftest_api.py`：增加 NDJSON stream 用例。
- **Tests**：`python scripts/selftest_api.py` → passed=37 failed=0（含 `POST /api/sync/run NDJSON stream`）。
- **Acceptance**：同步过程中日志实时出现；UI 不整段卡死等待结束。
- **Next**：无。
