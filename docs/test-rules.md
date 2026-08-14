# 测试规则（Test Rules）

> 自动化载体：`python scripts/selftest_api.py`（FastAPI TestClient，无需启动服务）。
> 前端无独立测试框架，UI 用例以 `npm run build`（TypeScript 编译通过）+ 手动路径验证为准；API 契约由 selftest 覆盖。

## Sprint 2026-07-25 — 批量操作 UI

### 库存批量编辑（BATCH-INV）

| 用例 ID | 条件 / 输入 | Expected |
|---------|-------------|----------|
| BATCH-INV-01 | 已存在 2 个测试物品；`PATCH /api/inventory/batch`，ids=[两个 id]，仅传 `location="__BATCH_LOC__"` | 200；`updated=2`；两物品 `location` 均为新值；`name/reference/cabinet/min_stock` 不变 |
| BATCH-INV-02 | 同上，仅传 `min_stock=9` | 200；`updated=2`；两物品 `min_stock=9`；`current_stock` 不变 |
| BATCH-INV-03 | ids 含一个不存在的 id（如 99999999）+ 一个有效 id，传 `cabinet="__B__"` | 200；`updated=1`（无效 id 跳过，不报错） |
| BATCH-INV-UI-01 | 库存页勾选 ≥2 行 | 工具栏出现「批量编辑 (N)」按钮 |
| BATCH-INV-UI-02 | 打开批量编辑面板，仅勾选「位置」并填值后提交 | 仅位置字段更新；列表刷新；选中清空；Toast 提示更新条数 |
| BATCH-INV-UI-03 | 面板中不勾选任何字段直接提交 | 前端拦截并提示「请至少勾选一个要修改的字段」，不发请求 |

### 批量出入库（BATCH-TX）

| 用例 ID | 条件 / 输入 | Expected |
|---------|-------------|----------|
| BATCH-TX-01 | 2 个测试物品（库存 a=10, b=10）；`POST /api/transactions/batch`，type=IN，recipient_source="__BATCH_SRC__"，items=[{a,3},{b,4}] | 200；`successful_count=2`；a 库存 13、b 库存 14；生成 2 条 IN 交易 |
| BATCH-TX-02 | 同上物品；type=OUT，recipient_source="__BATCH_RCV__"，items=[{a,3},{b,4}] | 200；`successful_count=2`；a 库存 10、b 库存 10 |
| BATCH-TX-03 | type=OUT，items 含超库存数量（{a, 99999}） | 400（库存不足）；两物品库存均不变（整批回滚） |
| BATCH-TX-04 | type=IN，recipient_source 为空串 | 422（Pydantic 校验「来源柜号不能为空」） |
| BATCH-TX-UI-01 | 交易页点「批量入库」/「批量出库」 | 右侧出现批量面板：共享来源柜号（IN）或接收人（OUT）、行列表（物品+数量）、可加行/删行 |
| BATCH-TX-UI-02 | OUT 模式某行数量 > 该物品当前库存，点提交 | 前端拦截并提示库存不足，不发请求 |
| BATCH-TX-UI-03 | 正常提交批量 IN/OUT | Toast 显示成功条数；交易列表与库存下拉刷新；面板关闭 |
| BATCH-TX-UI-04 | 存在重复选择同一物品的两行 | 允许（后端按顺序累计），提交正常 |

## 回归护栏（本次改动不得破坏）

| 用例 ID | 说明 | Expected |
|---------|------|----------|
| REG-01 | `scripts/selftest_api.py` 原有全部用例 | 全部 PASS |
| REG-02 | 库存页单条新增/编辑/删除、批量删除 | 行为不变 |
| REG-03 | 交易页单笔入库/出库/修改/冲销/删除 | 行为不变 |
| REG-04 | `cd frontend && npm run build` | 编译零错误 |
