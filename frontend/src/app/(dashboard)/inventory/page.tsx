"use client";

import { useCallback, useEffect, useState } from "react";
import { InventoryPanel } from "@/components/inventory/InventoryPanel";
import {
  InventoryBatchEditPanel,
  InventoryBatchPayload,
} from "@/components/inventory/InventoryBatchEditPanel";
import {
  DataTable,
  DataTableBody,
  DataTableEmpty,
  DataTableHead,
  DataTableLoading,
  DataTableTd,
  DataTableTh,
} from "@/components/layout/DataTable";
import {
  FilterDivider,
  FilterSearch,
  FilterSelect,
} from "@/components/layout/FilterToolbar";
import { PageLayout } from "@/components/layout/PageLayout";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import {
  ApiError,
  apiFetch,
  ConfigMap,
  InventoryItem,
} from "@/lib/api";
import {
  createInventoryForm,
  emptyInventoryForm,
  itemToForm,
  InventoryFormData,
} from "@/lib/inventory";

// 库存主视图 — 列表、筛选与批量操作

type PanelMode = "none" | "create" | "edit";

export default function InventoryPage() {
  const { show: toast } = useToast();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [config, setConfig] = useState<ConfigMap | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("ALL");
  const [domain, setDomain] = useState("ALL");
  const [location, setLocation] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [panelMode, setPanelMode] = useState<PanelMode>("none");
  const [form, setForm] = useState<InventoryFormData>(emptyInventoryForm());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false);
  const [batchEditOpen, setBatchEditOpen] = useState(false);
  const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());

  const selectedItem = items.find((i) => i.id === selectedId) ?? null;

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category !== "ALL") params.set("category", category);
    if (domain !== "ALL") params.set("domain", domain);
    if (location !== "ALL") params.set("location", location);
    const data = await apiFetch<InventoryItem[]>(
      `/api/inventory?${params.toString()}`,
    );
    setItems(data);
    setLoading(false);
  }, [search, category, domain, location]);

  useEffect(() => {
    load().catch((e) => toast(e instanceof Error ? e.message : "加载失败", "error"));
  }, [load, toast]);

  useEffect(() => {
    apiFetch<ConfigMap>("/api/config")
      .then(setConfig)
      .catch(() => toast("配置项加载失败", "error"));
  }, [toast]);

  function selectRow(item: InventoryItem) {
    setSelectedId(item.id);
    setPanelMode("edit");
    setForm(itemToForm(item));
    setConfirmDelete(false);
    setBatchDeleteConfirm(false);
    setBatchEditOpen(false);
  }

  function startCreate() {
    setSelectedId(null);
    setPanelMode("create");
    setForm(createInventoryForm(config));
    setConfirmDelete(false);
    setBatchDeleteConfirm(false);
    setBatchEditOpen(false);
  }

  function startBatchEdit() {
    setPanelMode("none");
    setSelectedId(null);
    setConfirmDelete(false);
    setBatchDeleteConfirm(false);
    setBatchEditOpen(true);
  }

  function cancelPanel() {
    setPanelMode("none");
    setSelectedId(null);
    setConfirmDelete(false);
    setForm(emptyInventoryForm());
  }

  async function saveForm() {
    setSaving(true);
    try {
      if (panelMode === "create") {
        await apiFetch<InventoryItem>("/api/inventory", {
          method: "POST",
          body: JSON.stringify(form),
        });
        toast("物品已创建", "success");
        cancelPanel();
        await load();
      } else if (panelMode === "edit" && selectedId) {
        await apiFetch<InventoryItem>(`/api/inventory/${selectedId}`, {
          method: "PUT",
          body: JSON.stringify({
            name: form.name,
            reference: form.reference,
            category: form.category,
            domain: form.domain,
            unit: form.unit,
            min_stock: form.min_stock,
            location: form.location,
            cabinet: form.cabinet,
          }),
        });
        toast("已保存", "success");
        cancelPanel();
        await load();
      }
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "保存失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function deleteSelected() {
    if (!selectedId) return;
    setSaving(true);
    try {
      await apiFetch(`/api/inventory/${selectedId}`, { method: "DELETE" });
      toast("已删除", "success");
      setConfirmDelete(false);
      cancelPanel();
      setCheckedIds((prev) => {
        const next = new Set(prev);
        next.delete(selectedId);
        return next;
      });
      await load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "删除失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function batchDelete() {
    if (checkedIds.size === 0) return;
    setSaving(true);
    try {
      const result = await apiFetch<{ deleted: number }>("/api/inventory/batch", {
        method: "DELETE",
        body: JSON.stringify({ ids: [...checkedIds] }),
      });
      toast(`已删除 ${result.deleted} 条`, "success");
      setBatchDeleteConfirm(false);
      setCheckedIds(new Set());
      cancelPanel();
      await load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "批量删除失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function batchEdit(payload: InventoryBatchPayload) {
    if (checkedIds.size === 0) return;
    setSaving(true);
    try {
      const result = await apiFetch<{ updated: number }>("/api/inventory/batch", {
        method: "PATCH",
        body: JSON.stringify({ ids: [...checkedIds], ...payload }),
      });
      toast(`已更新 ${result.updated} 条`, "success");
      setBatchEditOpen(false);
      setCheckedIds(new Set());
      await load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "批量编辑失败", "error");
    } finally {
      setSaving(false);
    }
  }

  function toggleCheck(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.checked) setCheckedIds(new Set(items.map((i) => i.id)));
    else setCheckedIds(new Set());
  }

  const filterOptions = (key: keyof InventoryItem) =>
    ["ALL", ...new Set(items.map((i) => i[key]).filter(Boolean) as string[])];

  const panelOpen = panelMode !== "none" || batchEditOpen;

  return (
    <PageLayout
      title="库存管理"
      panelOpen={panelOpen}
      toolbar={
        <>
          <FilterSearch
            value={search}
            onChange={setSearch}
            placeholder="搜索：名称、型号或柜号"
            className="min-w-[220px]"
          />
          <FilterSelect label="类别" value={category} options={filterOptions("category")} onChange={setCategory} />
          <FilterSelect label="专业" value={domain} options={filterOptions("domain")} onChange={setDomain} />
          <FilterSelect label="位置" value={location} options={filterOptions("location")} onChange={setLocation} />
          <Button variant="warning" onClick={() => load()}>
            刷新
          </Button>
          <FilterDivider />
          <div className="flex-1" />
          <Button variant="success" onClick={startCreate}>
            新增物品
          </Button>
          {checkedIds.size > 0 && !batchDeleteConfirm && (
            <>
              <Button variant="info" onClick={startBatchEdit}>
                批量编辑 ({checkedIds.size})
              </Button>
              <Button variant="danger" onClick={() => setBatchDeleteConfirm(true)}>
                删除选中 ({checkedIds.size})
              </Button>
            </>
          )}
          {batchDeleteConfirm && (
            <div className="flex items-center gap-2 rounded-md border border-[#ffcdd2] bg-[#ffebee] px-3 py-1.5 text-sm">
              <span>确认删除 {checkedIds.size} 项？</span>
              <Button variant="danger" onClick={batchDelete} disabled={saving}>
                确认
              </Button>
              <Button variant="outline" onClick={() => setBatchDeleteConfirm(false)}>
                取消
              </Button>
            </div>
          )}
        </>
      }
      panel={
        batchEditOpen ? (
          <InventoryBatchEditPanel
            count={checkedIds.size}
            config={config}
            saving={saving}
            onSubmit={batchEdit}
            onCancel={() => setBatchEditOpen(false)}
          />
        ) : (
          <InventoryPanel
            mode={panelMode}
            item={selectedItem}
            form={form}
            config={config}
            saving={saving}
            confirmDelete={confirmDelete}
            onChange={setForm}
            onSave={saveForm}
            onCancel={cancelPanel}
            onDeleteRequest={() => setConfirmDelete(true)}
            onDeleteConfirm={deleteSelected}
            onDeleteCancel={() => setConfirmDelete(false)}
          />
        )
      }
      statusBar={
        <>
          总计 {items.length} 条
          {checkedIds.size > 0 && ` · 已选 ${checkedIds.size} 条`}
        </>
      }
    >
      <DataTable minWidth={1114}>
        <DataTableHead>
          <tr>
            <DataTableTh className="w-10">
              <input
                type="checkbox"
                checked={items.length > 0 && checkedIds.size === items.length}
                onChange={toggleAll}
              />
            </DataTableTh>
            {[
              ["名称", "w-[220px]"],
              ["型号", "w-[160px]"],
              ["类别", "w-[100px]"],
              ["专业", "w-[80px]"],
              ["单位", "w-[64px]"],
              ["当前库存", "w-[90px]"],
              ["最小库存", "w-[90px]"],
              ["位置", "w-[90px]"],
              ["柜号", "w-[100px]"],
              ["状态", "w-[80px]"],
            ].map(([h, w]) => (
              <DataTableTh key={h} className={w}>
                {h}
              </DataTableTh>
            ))}
          </tr>
        </DataTableHead>
        <DataTableBody>
          {loading ? (
            <DataTableLoading colSpan={11} />
          ) : items.length === 0 ? (
            <DataTableEmpty colSpan={11} />
          ) : (
            items.map((item, idx) => {
              const isSelected = selectedId === item.id;
              const rowBg = isSelected
                ? "bg-brand-primary/25 ring-1 ring-inset ring-brand-primary/35"
                : idx % 2
                  ? "bg-white/20"
                  : "bg-white/35";
              return (
                <tr
                  key={item.id}
                  className={`cursor-pointer ${rowBg} hover:bg-brand-primary/15`}
                  onClick={() => selectRow(item)}
                >
                  <DataTableTd className="w-10" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={checkedIds.has(item.id)}
                      onChange={() => {}}
                      onClick={(e) => toggleCheck(item.id, e)}
                    />
                  </DataTableTd>
                  <DataTableTd title={item.name}>
                    <div className="line-clamp-2 leading-tight font-medium">{item.name}</div>
                  </DataTableTd>
                  <DataTableTd title={item.reference}>
                    <div className="line-clamp-2 leading-tight font-medium">{item.reference}</div>
                  </DataTableTd>
                  <DataTableTd title={item.category}>
                    <div className="line-clamp-2 leading-tight">{item.category}</div>
                  </DataTableTd>
                  <DataTableTd title={item.domain}>
                    <div className="line-clamp-2 leading-tight">{item.domain}</div>
                  </DataTableTd>
                  <DataTableTd>
                    <div className="line-clamp-2 leading-tight">{item.unit}</div>
                  </DataTableTd>
                  <DataTableTd className="whitespace-nowrap text-right tabular-nums">
                    {item.current_stock}
                  </DataTableTd>
                  <DataTableTd className="whitespace-nowrap text-right tabular-nums">
                    {item.min_stock}
                  </DataTableTd>
                  <DataTableTd title={item.location}>
                    <div className="line-clamp-2 leading-tight">{item.location}</div>
                  </DataTableTd>
                  <DataTableTd title={item.cabinet}>
                    <div className="line-clamp-2 leading-tight">{item.cabinet}</div>
                  </DataTableTd>
                  <DataTableTd>
                    <Badge status={item.status} />
                  </DataTableTd>
                </tr>
              );
            })
          )}
        </DataTableBody>
      </DataTable>
    </PageLayout>
  );
}
