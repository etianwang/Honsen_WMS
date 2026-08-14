"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  PanelField,
  panelFieldClass,
  SidePanelCard,
} from "@/components/layout/SidePanel";
import { ConfigMap, InventoryItem } from "@/lib/api";

// 批量出入库面板 — 共享来源柜号/接收人 + 多行物品（POST /api/transactions/batch）

export type BatchTxRow = {
  item_id: number;
  quantity: number;
};

export type BatchTxSubmit = {
  recipient_source: string;
  project_ref: string;
  rows: BatchTxRow[];
};

type RowState = {
  key: number;
  item_id: number;
  quantity: number;
};

type Props = {
  mode: "in" | "out";
  inventory: InventoryItem[];
  config: ConfigMap | null;
  saving: boolean;
  onSubmit: (data: BatchTxSubmit) => void;
  onCancel: () => void;
};

let rowKeySeq = 1;

function newRow(): RowState {
  return { key: rowKeySeq++, item_id: 0, quantity: 1 };
}

export function BatchTransactionPanel({
  mode,
  inventory,
  config,
  saving,
  onSubmit,
  onCancel,
}: Props) {
  const [rows, setRows] = useState<RowState[]>([newRow(), newRow()]);
  const [recipientSource, setRecipientSource] = useState("");
  const [projectRef, setProjectRef] = useState("");
  const [error, setError] = useState("");

  const isIn = mode === "in";
  const sharedLabel = isIn ? "来源柜号" : "接收人";

  function updateRow(key: number, patch: Partial<RowState>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    setError("");
  }

  function addRow() {
    setRows((prev) => [...prev, newRow()]);
  }

  function removeRow(key: number) {
    setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.key !== key) : prev));
    setError("");
  }

  function validate(): string {
    if (!recipientSource.trim()) return `${sharedLabel}不能为空`;
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (!row.item_id) return `第 ${i + 1} 行：请选择物品`;
      if (!Number.isFinite(row.quantity) || row.quantity <= 0) {
        return `第 ${i + 1} 行：数量须为正整数`;
      }
    }
    if (!isIn) {
      // 同一物品多行时按合计校验库存
      const totals = new Map<number, number>();
      for (const row of rows) {
        totals.set(row.item_id, (totals.get(row.item_id) ?? 0) + Math.floor(row.quantity));
      }
      for (const [itemId, total] of totals) {
        const item = inventory.find((i) => i.id === itemId);
        if (!item) return "所选物品不存在，请刷新页面";
        if (item.current_stock < total) {
          return `库存不足：${item.name} 当前 ${item.current_stock}，出库合计 ${total}`;
        }
      }
    }
    return "";
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const msg = validate();
    if (msg) {
      setError(msg);
      return;
    }
    setError("");
    onSubmit({
      recipient_source: recipientSource.trim(),
      project_ref: isIn ? "" : projectRef,
      rows: rows.map((r) => ({ item_id: r.item_id, quantity: Math.floor(r.quantity) })),
    });
  }

  const footer = (
    <div className="space-y-2">
      {error && <p className="text-xs font-semibold text-[#c62828]">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          form="batch-tx-form"
          variant={isIn ? "success" : "danger"}
          disabled={saving}
        >
          {saving ? "提交中..." : `确认批量${isIn ? "入库" : "出库"}（${rows.length} 行）`}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
      </div>
    </div>
  );

  return (
    <SidePanelCard
      title={isIn ? "批量入库 (IN)" : "批量出库 (OUT)"}
      subtitle={`所有行共享${sharedLabel}${isIn ? "" : "与项目"}；整批提交，任一行失败则全部回滚`}
      footer={footer}
    >
      <form id="batch-tx-form" onSubmit={handleSubmit} className="space-y-3">
        <PanelField label={sharedLabel} required>
          <input
            className={panelFieldClass}
            value={recipientSource}
            onChange={(e) => {
              setRecipientSource(e.target.value);
              setError("");
            }}
            placeholder={isIn ? "从哪条柜子入库" : "接收人姓名"}
          />
        </PanelField>

        {!isIn && (
          <PanelField label="项目">
            <select
              className={panelFieldClass}
              value={projectRef}
              onChange={(e) => setProjectRef(e.target.value)}
            >
              <option value="">—</option>
              {(config?.PROJECT ?? []).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </PanelField>
        )}

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-text-secondary">
              物品明细（{rows.length} 行）
            </span>
            <Button type="button" variant="outline" onClick={addRow}>
              + 加一行
            </Button>
          </div>

          {rows.map((row, idx) => (
            <div
              key={row.key}
              className="rounded-lg border border-white/60 bg-white/30 p-2"
            >
              <div className="mb-1 flex items-center justify-between text-xs text-text-secondary">
                <span>第 {idx + 1} 行</span>
                {rows.length > 1 && (
                  <button
                    type="button"
                    className="font-semibold text-[#c62828] hover:underline"
                    onClick={() => removeRow(row.key)}
                  >
                    移除
                  </button>
                )}
              </div>
              <div className="space-y-2">
                <select
                  className={panelFieldClass}
                  value={row.item_id || ""}
                  onChange={(e) => updateRow(row.key, { item_id: Number(e.target.value) })}
                >
                  <option value="">— 请选择物品 —</option>
                  {inventory.map((item) => (
                    <option key={item.id} value={item.id}>
                      [{item.reference}] {item.name} (库存:{item.current_stock})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={1}
                  className={panelFieldClass}
                  value={row.quantity}
                  onChange={(e) =>
                    updateRow(row.key, { quantity: Math.max(1, Number(e.target.value)) })
                  }
                />
              </div>
            </div>
          ))}
        </div>
      </form>
    </SidePanelCard>
  );
}
