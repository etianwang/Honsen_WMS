"use client";

import { FormEvent, ReactNode, useState } from "react";
import { Button } from "@/components/ui/Button";
import { panelFieldClass, SidePanelCard } from "@/components/layout/SidePanel";
import { ConfigMap } from "@/lib/api";

// 库存批量编辑面板 — 勾选启用的字段才会提交（PATCH /api/inventory/batch）

export type InventoryBatchPayload = {
  category?: string;
  domain?: string;
  unit?: string;
  min_stock?: number;
  location?: string;
  cabinet?: string;
};

type FieldKey = keyof InventoryBatchPayload;

type Props = {
  count: number;
  config: ConfigMap | null;
  saving: boolean;
  onSubmit: (payload: InventoryBatchPayload) => void;
  onCancel: () => void;
};

export function InventoryBatchEditPanel({
  count,
  config,
  saving,
  onSubmit,
  onCancel,
}: Props) {
  const [enabled, setEnabled] = useState<Record<FieldKey, boolean>>({
    category: false,
    domain: false,
    unit: false,
    min_stock: false,
    location: false,
    cabinet: false,
  });
  const [category, setCategory] = useState("");
  const [domain, setDomain] = useState("");
  const [unit, setUnit] = useState("");
  const [minStock, setMinStock] = useState(0);
  const [location, setLocation] = useState("");
  const [cabinet, setCabinet] = useState("");
  const [error, setError] = useState("");

  function toggle(key: FieldKey) {
    setEnabled((prev) => ({ ...prev, [key]: !prev[key] }));
    setError("");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const payload: InventoryBatchPayload = {};
    if (enabled.category) payload.category = category;
    if (enabled.domain) payload.domain = domain;
    if (enabled.unit) payload.unit = unit;
    if (enabled.min_stock) payload.min_stock = Math.max(0, Math.floor(minStock));
    if (enabled.location) payload.location = location;
    if (enabled.cabinet) payload.cabinet = cabinet;
    if (Object.keys(payload).length === 0) {
      setError("请至少勾选一个要修改的字段");
      return;
    }
    setError("");
    onSubmit(payload);
  }

  const footer = (
    <div className="space-y-2">
      {error && <p className="text-xs font-semibold text-[#c62828]">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          form="inventory-batch-edit-form"
          variant="success"
          disabled={saving}
        >
          {saving ? "提交中..." : `应用到 ${count} 项`}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
      </div>
    </div>
  );

  return (
    <SidePanelCard
      title={`批量编辑（已选 ${count} 项）`}
      subtitle="仅勾选的字段会被修改；名称、型号与当前库存不受影响"
      footer={footer}
    >
      <form id="inventory-batch-edit-form" onSubmit={handleSubmit} className="space-y-3">
        <BatchField label="材料类别" checked={enabled.category} onToggle={() => toggle("category")}>
          <BatchSelect
            value={category}
            options={config?.CATEGORY ?? []}
            disabled={!enabled.category}
            onChange={setCategory}
          />
        </BatchField>
        <BatchField label="专业类别" checked={enabled.domain} onToggle={() => toggle("domain")}>
          <BatchSelect
            value={domain}
            options={config?.DOMAIN ?? []}
            disabled={!enabled.domain}
            onChange={setDomain}
          />
        </BatchField>
        <BatchField label="单位" checked={enabled.unit} onToggle={() => toggle("unit")}>
          <BatchSelect
            value={unit}
            options={config?.UNIT ?? []}
            disabled={!enabled.unit}
            onChange={setUnit}
          />
        </BatchField>
        <BatchField label="最小库存" checked={enabled.min_stock} onToggle={() => toggle("min_stock")}>
          <input
            type="number"
            min={0}
            className={panelFieldClass}
            value={minStock}
            disabled={!enabled.min_stock}
            onChange={(e) => setMinStock(Number(e.target.value))}
          />
        </BatchField>
        <BatchField label="储存位置" checked={enabled.location} onToggle={() => toggle("location")}>
          <BatchSelect
            value={location}
            options={config?.LOCATION ?? []}
            disabled={!enabled.location}
            onChange={setLocation}
          />
        </BatchField>
        <BatchField label="柜号" checked={enabled.cabinet} onToggle={() => toggle("cabinet")}>
          <input
            className={panelFieldClass}
            value={cabinet}
            disabled={!enabled.cabinet}
            onChange={(e) => setCabinet(e.target.value)}
          />
        </BatchField>
      </form>
    </SidePanelCard>
  );
}

function BatchField({
  label,
  checked,
  onToggle,
  children,
}: {
  label: string;
  checked: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <div className={checked ? "" : "opacity-60"}>
      <label className="mb-1 flex cursor-pointer items-center gap-2 text-sm font-semibold text-text-secondary">
        <input type="checkbox" checked={checked} onChange={onToggle} />
        {label}
      </label>
      {children}
    </div>
  );
}

function BatchSelect({
  value,
  options,
  disabled,
  onChange,
}: {
  value: string;
  options: string[];
  disabled: boolean;
  onChange: (v: string) => void;
}) {
  if (options.length === 0) {
    return (
      <input
        className={panelFieldClass}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <select
      className={panelFieldClass}
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">请选择</option>
      {!options.includes(value) && value && <option value={value}>{value}</option>}
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}