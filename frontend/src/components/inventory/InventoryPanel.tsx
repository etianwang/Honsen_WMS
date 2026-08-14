"use client";

import { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import {
  PanelField,
  panelFieldClass,
  SidePanelCard,
  SidePanelEmpty,
} from "@/components/layout/SidePanel";
import { InventoryFormData } from "@/lib/inventory";
import { ConfigMap, InventoryItem } from "@/lib/api";

// 库存操作面板 — 出入库以外的新增/编辑入口

type PanelMode = "none" | "create" | "edit";

type Props = {
  mode: PanelMode;
  item: InventoryItem | null;
  form: InventoryFormData;
  config: ConfigMap | null;
  saving: boolean;
  confirmDelete: boolean;
  onChange: (form: InventoryFormData) => void;
  onSave: () => void;
  onCancel: () => void;
  onDeleteRequest: () => void;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
};

export function InventoryPanel({
  mode,
  item,
  form,
  config,
  saving,
  confirmDelete,
  onChange,
  onSave,
  onCancel,
  onDeleteRequest,
  onDeleteConfirm,
  onDeleteCancel,
}: Props) {
  if (mode === "none") {
    return (
      <SidePanelEmpty>
        <p>点击表格行查看或编辑物品，或点击「新增物品」创建记录。</p>
        <p className="mt-3 text-xs">当前库存仅能通过出入库变动；编辑时不可直接改数量。</p>
      </SidePanelEmpty>
    );
  }

  function update<K extends keyof InventoryFormData>(key: K, value: InventoryFormData[K]) {
    onChange({ ...form, [key]: value });
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    onSave();
  }

  const title = mode === "create" ? "新增物品" : `编辑物品 #${item?.id}`;
  const subtitle =
    mode === "edit" && item
      ? `当前库存 ${item.current_stock} · ${item.status ?? "正常"}`
      : undefined;

  const footer = confirmDelete ? (
    <div className="rounded-md border border-[#ffcdd2] bg-[#ffebee] p-3 text-sm">
      <p className="font-semibold text-[#c62828]">确认删除此物品？</p>
      <p className="mt-1 text-xs text-text-secondary">将同时删除关联交易，不可恢复。</p>
      <div className="mt-3 flex gap-2">
        <Button type="button" variant="danger" onClick={onDeleteConfirm} disabled={saving}>
          确认删除
        </Button>
        <Button type="button" variant="outline" onClick={onDeleteCancel}>
          取消
        </Button>
      </div>
    </div>
  ) : (
    <div className="flex flex-wrap gap-2">
      <Button type="submit" form="inventory-panel-form" variant="success" disabled={saving}>
        {saving ? "保存中..." : "保存"}
      </Button>
      <Button type="button" variant="outline" onClick={onCancel}>
        取消
      </Button>
      {mode === "edit" && (
        <Button type="button" variant="danger" onClick={onDeleteRequest}>
          删除
        </Button>
      )}
    </div>
  );

  return (
    <SidePanelCard title={title} subtitle={subtitle} footer={footer}>
      <form id="inventory-panel-form" onSubmit={onSubmit} className="space-y-3">
        <PanelField label="名称" required>
          <input
            className={panelFieldClass}
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            required
          />
        </PanelField>
        <PanelField label="物品型号" required>
          <input
            className={panelFieldClass}
            value={form.reference}
            onChange={(e) => update("reference", e.target.value)}
            required
          />
        </PanelField>
        <PanelField label="材料类别">
          <SelectOrInput
            value={form.category}
            options={config?.CATEGORY ?? []}
            onChange={(v) => update("category", v)}
          />
        </PanelField>
        <PanelField label="专业类别">
          <SelectOrInput
            value={form.domain}
            options={config?.DOMAIN ?? []}
            onChange={(v) => update("domain", v)}
          />
        </PanelField>
        <PanelField label="单位">
          <SelectOrInput
            value={form.unit}
            options={config?.UNIT ?? []}
            onChange={(v) => update("unit", v)}
          />
        </PanelField>
        {mode === "create" && (
          <PanelField label="初始库存">
            <input
              type="number"
              min={0}
              className={panelFieldClass}
              value={form.current_stock}
              onChange={(e) => update("current_stock", Number(e.target.value))}
            />
          </PanelField>
        )}
        <PanelField label="最小库存">
          <input
            type="number"
            min={0}
            className={panelFieldClass}
            value={form.min_stock}
            onChange={(e) => update("min_stock", Number(e.target.value))}
          />
        </PanelField>
        <PanelField label="储存位置">
          <SelectOrInput
            value={form.location}
            options={config?.LOCATION ?? []}
            onChange={(v) => update("location", v)}
          />
        </PanelField>
        <PanelField label="柜号">
          <input
            className={panelFieldClass}
            value={form.cabinet}
            onChange={(e) => update("cabinet", e.target.value)}
          />
        </PanelField>
      </form>
    </SidePanelCard>
  );
}

function SelectOrInput({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  if (options.length === 0) {
    return (
      <input className={panelFieldClass} value={value} onChange={(e) => onChange(e.target.value)} />
    );
  }
  const selected = options.includes(value) ? value : value || "";
  return (
    <select
      className={panelFieldClass}
      value={selected}
      onChange={(e) => onChange(e.target.value)}
    >
      {!value && <option value="">请选择</option>}
      {!options.includes(value) && value && <option value={value}>{value}</option>}
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}
