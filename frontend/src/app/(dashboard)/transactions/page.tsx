"use client";

import { useCallback, useEffect, useState } from "react";
import { TransactionPanel } from "@/components/transactions/TransactionPanel";
import {
  BatchTransactionPanel,
  BatchTxSubmit,
} from "@/components/transactions/BatchTransactionPanel";
import {
  DataTable,
  DataTableBody,
  DataTableEmpty,
  DataTableHead,
  DataTableLoading,
  DataTableTh,
} from "@/components/layout/DataTable";
import {
  FilterDate,
  FilterDivider,
  FilterSearch,
  FilterSelect,
} from "@/components/layout/FilterToolbar";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { exportCsv } from "@/lib/csv";
import {
  ApiError,
  apiFetch,
  ConfigMap,
  InventoryItem,
} from "@/lib/api";
import {
  cabinetDisplay,
  emptyTxForm,
  isReversal,
  rowBackground,
  TransactionItem,
  TransactionListResponse,
  TxFormData,
  TxPanelMode,
  txToForm,
  typeBadgeClass,
} from "@/lib/transactions";

export default function TransactionsPage() {
  const { show: toast } = useToast();
  const [items, setItems] = useState<TransactionItem[]>([]);
  const [stats, setStats] = useState<TransactionListResponse["stats"] | null>(null);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [config, setConfig] = useState<ConfigMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [txType, setTxType] = useState("ALL");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("ALL");
  const [domain, setDomain] = useState("ALL");
  const [location, setLocation] = useState("ALL");
  const [project, setProject] = useState("ALL");

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [panelMode, setPanelMode] = useState<TxPanelMode>("none");
  const [form, setForm] = useState<TxFormData>(emptyTxForm());
  const [confirmReverse, setConfirmReverse] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [batchMode, setBatchMode] = useState<"none" | "in" | "out">("none");

  const selectedTx = items.find((t) => t.id === selectedId) ?? null;

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (txType !== "ALL") params.set("type", txType);
    if (search) params.set("search", search);
    if (category !== "ALL") params.set("category", category);
    if (domain !== "ALL") params.set("domain", domain);
    if (location !== "ALL") params.set("location", location);
    if (project !== "ALL") params.set("project", project);

    const data = await apiFetch<TransactionListResponse>(
      `/api/transactions?${params.toString()}`,
    );
    setItems(data.items);
    setStats(data.stats);
    setLoading(false);
  }, [startDate, endDate, txType, search, category, domain, location, project]);

  useEffect(() => {
    load().catch((e) => toast(e instanceof Error ? e.message : "加载失败", "error"));
  }, [load, toast]);

  useEffect(() => {
    apiFetch<InventoryItem[]>("/api/inventory")
      .then(setInventory)
      .catch((e) =>
        toast(e instanceof Error ? e.message : "库存列表加载失败", "error"),
      );
    apiFetch<ConfigMap>("/api/config").then(setConfig).catch(() => {});
  }, [toast]);

  function selectRow(tx: TransactionItem) {
    setBatchMode("none");
    if (isReversal(tx.type)) {
      setSelectedId(tx.id);
      setPanelMode("none");
      setConfirmReverse(false);
      setConfirmDelete(false);
      return;
    }
    setSelectedId(tx.id);
    setPanelMode("edit");
    setForm(txToForm(tx));
    setConfirmReverse(false);
    setConfirmDelete(false);
  }

  function startIn() {
    setBatchMode("none");
    setSelectedId(null);
    setPanelMode("in");
    setForm(emptyTxForm());
    setConfirmReverse(false);
    setConfirmDelete(false);
  }

  function startOut() {
    setBatchMode("none");
    setSelectedId(null);
    setPanelMode("out");
    setForm(emptyTxForm());
    setConfirmReverse(false);
    setConfirmDelete(false);
  }

  function startBatch(mode: "in" | "out") {
    setSelectedId(null);
    setPanelMode("none");
    setConfirmReverse(false);
    setConfirmDelete(false);
    setBatchMode(mode);
  }

  // 打开出入库面板时，若仅一项库存则自动选中
  useEffect(() => {
    if ((panelMode !== "in" && panelMode !== "out") || inventory.length !== 1) return;
    if (form.item_id) return;
    setForm((prev) => ({ ...prev, item_id: inventory[0].id }));
  }, [panelMode, inventory, form.item_id]);

  function cancelPanel() {
    setPanelMode("none");
    setConfirmReverse(false);
    setConfirmDelete(false);
    if (selectedId && selectedTx && !isReversal(selectedTx.type)) {
      setForm(txToForm(selectedTx));
    }
  }

  async function saveForm() {
    if (panelMode === "in" || panelMode === "out") {
      if (!form.item_id || form.item_id <= 0) {
        toast("请选择物品", "error");
        return;
      }
      if (!Number.isFinite(form.quantity) || form.quantity <= 0) {
        toast("数量须为正整数", "error");
        return;
      }
      if (!form.recipient_source.trim()) {
        toast(panelMode === "in" ? "来源柜号不能为空" : "接收人不能为空", "error");
        return;
      }
      const picked = inventory.find((i) => i.id === form.item_id);
      if (!picked) {
        toast("所选物品不存在，请刷新页面", "error");
        return;
      }
      if (panelMode === "out" && picked.current_stock < form.quantity) {
        toast(`库存不足：当前 ${picked.current_stock}，出库 ${form.quantity}`, "error");
        return;
      }
      setSaving(true);
      try {
        await apiFetch("/api/transactions", {
          method: "POST",
          body: JSON.stringify({
            item_id: form.item_id,
            type: panelMode === "in" ? "IN" : "OUT",
            quantity: Math.floor(form.quantity),
            recipient_source: form.recipient_source.trim(),
            project_ref: panelMode === "out" ? form.project_ref : "",
          }),
        });
        toast(panelMode === "in" ? "入库成功" : "出库成功", "success");
        setPanelMode("none");
        setSelectedId(null);
        await load();
        apiFetch<InventoryItem[]>("/api/inventory").then(setInventory).catch(() => {});
      } catch (e) {
        toast(e instanceof ApiError ? e.message : "交易失败", "error");
      } finally {
        setSaving(false);
      }
      return;
    }

    if (panelMode === "edit" && selectedId) {
      if (!form.recipient_source.trim()) {
        toast(selectedTx?.type === "IN" ? "来源柜号不能为空" : "接收人不能为空", "error");
        return;
      }
      setSaving(true);
      try {
        await apiFetch(`/api/transactions/${selectedId}`, {
          method: "PUT",
          body: JSON.stringify({
            quantity: form.quantity,
            date: form.date,
            recipient_source: form.recipient_source.trim(),
            project_ref: form.project_ref,
          }),
        });
        toast("已更新", "success");
        await load();
      } catch (e) {
        toast(e instanceof ApiError ? e.message : "更新失败", "error");
      } finally {
        setSaving(false);
      }
    }
  }

  async function saveBatch(data: BatchTxSubmit) {
    if (batchMode === "none") return;
    setSaving(true);
    try {
      const result = await apiFetch<{ successful_count: number }>(
        "/api/transactions/batch",
        {
          method: "POST",
          body: JSON.stringify({
            type: batchMode === "in" ? "IN" : "OUT",
            recipient_source: data.recipient_source,
            items: data.rows.map((r) => ({
              item_id: r.item_id,
              quantity: r.quantity,
              project_ref: data.project_ref,
            })),
          }),
        },
      );
      toast(
        `批量${batchMode === "in" ? "入库" : "出库"}成功：${result.successful_count} 笔`,
        "success",
      );
      setBatchMode("none");
      await load();
      apiFetch<InventoryItem[]>("/api/inventory").then(setInventory).catch(() => {});
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "批量交易失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function reverseTx() {
    if (!selectedId) return;
    setSaving(true);
    try {
      await apiFetch(`/api/transactions/${selectedId}/reverse`, { method: "POST" });
      toast("已冲销", "success");
      setConfirmReverse(false);
      setPanelMode("none");
      await load();
      apiFetch<InventoryItem[]>("/api/inventory").then(setInventory).catch(() => {});
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "冲销失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function deleteTx() {
    if (!selectedId) return;
    setSaving(true);
    try {
      await apiFetch(`/api/transactions/${selectedId}`, { method: "DELETE" });
      toast("已删除", "success");
      setConfirmDelete(false);
      setSelectedId(null);
      setPanelMode("none");
      await load();
      apiFetch<InventoryItem[]>("/api/inventory").then(setInventory).catch(() => {});
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "删除失败", "error");
    } finally {
      setSaving(false);
    }
  }

  function exportFiltered() {
    const headers = [
      "日期/时间", "物品名称", "物品型号", "数量",
      "储存位置", "柜号", "专业", "类型", "来源柜号/接收人", "项目",
    ];
    const rows = items.map((tx) => [
      tx.date,
      tx.item_name ?? "",
      tx.item_ref ?? "",
      String(tx.quantity),
      tx.location ?? "",
      cabinetDisplay(tx),
      tx.domain ?? "",
      tx.type,
      tx.recipient_source ?? "",
      tx.project_ref ?? "",
    ]);
    exportCsv(headers, rows, `transactions_${new Date().toISOString().slice(0, 10)}.csv`);
    toast("已导出筛选结果", "success");
  }

  const categoryOptions = ["ALL", ...new Set(items.map((t) => t.category).filter(Boolean) as string[])];
  const domainOptions = ["ALL", ...new Set(items.map((t) => t.domain).filter(Boolean) as string[])];
  const locationOptions = ["ALL", ...new Set(items.map((t) => t.location).filter(Boolean) as string[])];
  const projectOptions = ["ALL", ...new Set(items.map((t) => t.project_ref).filter(Boolean) as string[])];

  return (
    <PageLayout
      title="交易记录"
      toolbar={
        <>
          <Button variant="success" onClick={startIn}>
            入库 IN
          </Button>
          <Button variant="danger" onClick={startOut}>
            出库 OUT
          </Button>
          <Button variant="success" onClick={() => startBatch("in")}>
            批量入库
          </Button>
          <Button variant="danger" onClick={() => startBatch("out")}>
            批量出库
          </Button>
          <FilterDivider />
          <FilterDate label="从" value={startDate} onChange={setStartDate} />
          <FilterDate label="到" value={endDate} onChange={setEndDate} />
          <FilterSelect label="类别" value={category} options={categoryOptions} onChange={setCategory} />
          <FilterSelect label="专业" value={domain} options={domainOptions} onChange={setDomain} />
          <FilterSelect label="地点" value={location} options={locationOptions} onChange={setLocation} />
          <FilterSelect label="项目" value={project} options={projectOptions} onChange={setProject} />
          <FilterSelect label="类型" value={txType} options={["ALL", "IN", "OUT"]} onChange={setTxType} />
          <FilterSearch value={search} onChange={setSearch} placeholder="物品搜索" className="min-w-[140px]" />
          <Button variant="warning" onClick={() => load().catch((e) => toast(String(e), "error"))}>
            筛选
          </Button>
          <div className="flex-1" />
          <Button variant="info" onClick={exportFiltered} disabled={items.length === 0}>
            导出 CSV
          </Button>
        </>
      }
      panel={
        batchMode !== "none" ? (
          <BatchTransactionPanel
            key={batchMode}
            mode={batchMode}
            inventory={inventory}
            config={config}
            saving={saving}
            onSubmit={saveBatch}
            onCancel={() => setBatchMode("none")}
          />
        ) : (
        <TransactionPanel
          mode={panelMode}
          tx={selectedTx}
          form={form}
          inventory={inventory}
          config={config}
          saving={saving}
          confirmReverse={confirmReverse}
          confirmDelete={confirmDelete}
          onChange={setForm}
          onSave={saveForm}
          onCancel={cancelPanel}
          onReverseRequest={() => setConfirmReverse(true)}
          onReverseConfirm={reverseTx}
          onReverseCancel={() => setConfirmReverse(false)}
          onDeleteRequest={() => setConfirmDelete(true)}
          onDeleteConfirm={deleteTx}
          onDeleteCancel={() => setConfirmDelete(false)}
        />
        )
      }
      statusBar={
        stats ? (
          <>
            共 {stats.total} 条 · 入库 {stats.total_in_qty} · 出库 {stats.total_out_qty}
            {" · "}
            {stats.unique_domains} 个专业 · {stats.unique_locations} 个地点 · {stats.unique_projects} 个项目
          </>
        ) : (
          "—"
        )
      }
    >
      <DataTable minWidth={1058}>
        <DataTableHead>
          <tr>
            {[
              ["日期", "w-[92px]"],
              ["名称", "w-[220px]"],
              ["型号", "w-[140px]"],
              ["数量", "w-[64px]"],
              ["位置", "w-[84px]"],
              ["柜号", "w-[100px]"],
              ["专业", "w-[64px]"],
              ["类型", "w-[64px]"],
              ["来源/接收人", "w-[120px]"],
              ["项目", "w-[110px]"],
            ].map(([h, w]) => (
              <DataTableTh key={h} className={`whitespace-nowrap ${w}`}>
                {h}
              </DataTableTh>
            ))}
          </tr>
        </DataTableHead>
        <DataTableBody>
          {loading ? (
            <DataTableLoading colSpan={10} />
          ) : items.length === 0 ? (
            <DataTableEmpty colSpan={10} />
          ) : (
            items.map((tx) => {
              const selected = selectedId === tx.id;
              return (
                <tr
                  key={tx.id}
                  className={`cursor-pointer ${rowBackground(tx.type)} ${
                    selected ? "ring-2 ring-inset ring-brand-primary/50" : ""
                  } hover:bg-white/30`}
                  onClick={() => selectRow(tx)}
                >
                  <td className="px-2 py-1.5 text-xs leading-tight tabular-nums">
                    <div className="whitespace-nowrap">{tx.date.slice(0, 10)}</div>
                    <div className="whitespace-nowrap text-text-secondary">{tx.date.slice(11)}</div>
                  </td>
                  <td className="px-3 py-1.5 leading-tight">{tx.item_name}</td>
                  <td className="px-3 py-1.5 leading-tight" title={tx.item_ref ?? undefined}>
                    {tx.item_ref}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{tx.quantity}</td>
                  <td className="px-3 py-1.5 leading-tight">{tx.location}</td>
                  <td className="px-3 py-1.5 leading-tight">{cabinetDisplay(tx)}</td>
                  <td className="px-3 py-1.5 whitespace-nowrap">{tx.domain}</td>
                  <td className="px-3 py-1.5 whitespace-nowrap">
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${typeBadgeClass(tx.type)}`}>
                      {tx.type}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 leading-tight">{tx.recipient_source}</td>
                  <td className="px-3 py-1.5 leading-tight">{tx.project_ref}</td>
                </tr>
              );
            })
          )}
        </DataTableBody>
      </DataTable>
    </PageLayout>
  );
}
