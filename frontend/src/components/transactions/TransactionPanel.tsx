"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  PanelField,
  panelFieldClass,
  SidePanelCard,
  SidePanelEmpty,
} from "@/components/layout/SidePanel";
import { ConfigMap, InventoryItem } from "@/lib/api";
import { TxFormData, TxPanelMode, TransactionItem } from "@/lib/transactions";

function itemLabel(item: InventoryItem): string {
  return `[${item.reference}] ${item.name}`;
}

// 出入库操作面板 — IN/OUT 与冲正

type Props = {
  mode: TxPanelMode;
  tx: TransactionItem | null;
  form: TxFormData;
  inventory: InventoryItem[];
  config: ConfigMap | null;
  saving: boolean;
  confirmReverse: boolean;
  confirmDelete: boolean;
  onChange: (f: TxFormData) => void;
  onSave: () => void;
  onCancel: () => void;
  onReverseRequest: () => void;
  onReverseConfirm: () => void;
  onReverseCancel: () => void;
  onDeleteRequest: () => void;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
};

export function TransactionPanel({
  mode,
  tx,
  form,
  inventory,
  config,
  saving,
  confirmReverse,
  confirmDelete,
  onChange,
  onSave,
  onCancel,
  onReverseRequest,
  onReverseConfirm,
  onReverseCancel,
  onDeleteRequest,
  onDeleteConfirm,
  onDeleteCancel,
}: Props) {
  const [itemQuery, setItemQuery] = useState("");
  const [itemMenuOpen, setItemMenuOpen] = useState(false);

  const selectedInventoryItem = inventory.find((i) => i.id === form.item_id) ?? null;

  // 面板未在筛选态时，输入框始终展示当前选中物品的名称
  useEffect(() => {
    if (itemMenuOpen) return;
    setItemQuery(selectedInventoryItem ? itemLabel(selectedInventoryItem) : "");
  }, [selectedInventoryItem, itemMenuOpen]);

  const filteredInventory = useMemo(() => {
    const needle = itemQuery.trim().toLowerCase();
    if (!needle) return inventory;
    return inventory.filter((item) => {
      const haystack = [item.name, item.reference, item.cabinet, item.location]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [inventory, itemQuery]);

  if (mode === "none") {
    return (
      <SidePanelEmpty title="出入库面板">
        <p>选择一条交易记录进行编辑，或点击「入库」「出库」办理新交易。</p>
        <p className="mt-3 text-xs">入库须填写来源柜号；出库须填写接收人。</p>
      </SidePanelEmpty>
    );
  }

  const isIn = mode === "in";
  const title =
    mode === "in" ? "入库 (IN)" : mode === "out" ? "出库 (OUT)" : "修改交易";
  const subtitle =
    mode === "edit" && tx ? `${tx.item_name} · ${tx.type}` : undefined;

  function update<K extends keyof TxFormData>(key: K, value: TxFormData[K]) {
    onChange({ ...form, [key]: value });
  }

  const primaryFooter = (
    <div className="flex flex-wrap gap-2">
      <Button variant="primary" onClick={onSave} disabled={saving}>
        {saving ? "提交中..." : "确认"}
      </Button>
      <Button variant="outline" onClick={onCancel}>
        取消
      </Button>
    </div>
  );

  const dangerFooter =
    mode === "edit" && tx && !isReversalType(tx.type) ? (
      <div className="mt-3 space-y-2 border-t border-border pt-3">
        {!confirmReverse ? (
          <Button variant="warning" className="w-full" onClick={onReverseRequest}>
            冲销此记录
          </Button>
        ) : (
          <div className="rounded-md border border-[#ffe0b2] bg-[#fff8e1] p-2 text-sm">
            <p className="mb-2">确认冲销？将生成反向记录。</p>
            <div className="flex gap-2">
              <Button variant="warning" onClick={onReverseConfirm} disabled={saving}>
                确认冲销
              </Button>
              <Button variant="outline" onClick={onReverseCancel}>
                取消
              </Button>
            </div>
          </div>
        )}
        {!confirmDelete ? (
          <Button variant="danger" className="w-full" onClick={onDeleteRequest}>
            删除此记录
          </Button>
        ) : (
          <div className="rounded-md border border-[#ffcdd2] bg-[#ffebee] p-2 text-sm">
            <p className="mb-2">确认删除？库存将回滚。</p>
            <div className="flex gap-2">
              <Button variant="danger" onClick={onDeleteConfirm} disabled={saving}>
                确认删除
              </Button>
              <Button variant="outline" onClick={onDeleteCancel}>
                取消
              </Button>
            </div>
          </div>
        )}
      </div>
    ) : null;

  return (
    <SidePanelCard title={title} subtitle={subtitle} footer={<>{primaryFooter}{dangerFooter}</>}>
      <div className="space-y-3">
        {(mode === "in" || mode === "out") && (
          <PanelField label="选择物品" required>
            <div className="relative">
              <input
                type="text"
                className={panelFieldClass}
                placeholder="输入名称/型号/柜号/位置搜索物品"
                value={itemQuery}
                onChange={(e) => {
                  setItemQuery(e.target.value);
                  setItemMenuOpen(true);
                }}
                onFocus={() => setItemMenuOpen(true)}
                onBlur={() => setTimeout(() => setItemMenuOpen(false), 150)}
              />
              {itemMenuOpen && (
                <ul className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border border-border bg-white shadow-lg">
                  {filteredInventory.length === 0 ? (
                    <li className="px-3 py-2 text-sm text-text-secondary">无匹配物品</li>
                  ) : (
                    filteredInventory.map((item) => (
                      <li
                        key={item.id}
                        className={`cursor-pointer px-3 py-2 text-sm hover:bg-brand-primary/10 ${
                          item.id === form.item_id ? "bg-brand-primary/10 font-medium" : ""
                        }`}
                        onMouseDown={(e) => {
                          // 阻止 input 的 onBlur 先于点击触发，导致列表提前关闭
                          e.preventDefault();
                          update("item_id", item.id);
                          setItemQuery(itemLabel(item));
                          setItemMenuOpen(false);
                        }}
                      >
                        {itemLabel(item)}（库存:{item.current_stock}）
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>
          </PanelField>
        )}

        {mode === "edit" && tx && (
          <div className="rounded-md border border-border bg-[#f8fafc] p-3 text-xs text-text-secondary">
            <div className="font-semibold text-text-primary">{tx.item_name}</div>
            <div>{tx.item_ref}</div>
          </div>
        )}

        <PanelField label="数量" required>
          <input
            type="number"
            min={1}
            className={panelFieldClass}
            value={form.quantity}
            onChange={(e) => update("quantity", Math.max(1, Number(e.target.value)))}
          />
        </PanelField>

        {mode === "edit" && (
          <PanelField label="日期/时间">
            <input
              className={panelFieldClass}
              value={form.date}
              onChange={(e) => update("date", e.target.value)}
            />
          </PanelField>
        )}

        <PanelField
          label={isIn || (mode === "edit" && tx?.type === "IN") ? "来源柜号" : "接收人"}
          required
        >
          <input
            className={panelFieldClass}
            value={form.recipient_source}
            onChange={(e) => update("recipient_source", e.target.value)}
            placeholder={isIn ? "从哪条柜子入库" : "接收人姓名"}
          />
        </PanelField>

        {(mode === "out" || (mode === "edit" && tx?.type === "OUT")) && (
          <PanelField label="项目">
            <select
              className={panelFieldClass}
              value={form.project_ref}
              onChange={(e) => update("project_ref", e.target.value)}
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
      </div>
    </SidePanelCard>
  );
}

function isReversalType(type: string) {
  return type.toUpperCase().startsWith("REVERSAL");
}
