export type TransactionItem = {
 id: number;
 date: string;
 type: string;
 quantity: number;
 recipient_source?: string | null;
 project_ref?: string | null;
 item_id: number;
 item_name?: string | null;
 item_ref?: string | null;
 location?: string | null;
 category?: string | null;
 domain?: string | null;
 cabinet?: string | null;
};

export type TransactionStats = {
 total: number;
 total_in_qty: number;
 total_out_qty: number;
 unique_domains: number;
 unique_locations: number;
 unique_projects: number;
};

export type TransactionListResponse = {
 items: TransactionItem[];
 stats: TransactionStats;
};

export type TxPanelMode = "none" | "in" | "out" | "edit";

export type TxFormData = {
 item_id: number;
 quantity: number;
 recipient_source: string;
 project_ref: string;
 date: string;
};

export function emptyTxForm(): TxFormData {
 return {
 item_id: 0,
 quantity: 1,
 recipient_source: "",
 project_ref: "",
 date: new Date().toISOString().slice(0, 16).replace("T", " "),
 };
}

export function txToForm(tx: TransactionItem): TxFormData {
 return {
 item_id: tx.item_id,
 quantity: tx.quantity,
 recipient_source: tx.recipient_source ?? "",
 project_ref: tx.project_ref ?? "",
 date: tx.date,
 };
}

/** 入库显示来源柜号，出库显示库存柜号 */
export function cabinetDisplay(tx: TransactionItem): string {
 if (tx.type.toUpperCase() === "IN") {
 return tx.recipient_source ?? "";
 }
 return tx.cabinet ?? "";
}

export function rowBackground(type: string): string {
 const t = type.toUpperCase();
 if (t.startsWith("REVERSAL")) return "bg-[#fffde7]/55";
 if (t === "OUT") return "bg-[#ffebee]/50";
 return "bg-[#e8f5e9]/50";
}

export function typeBadgeClass(type: string): string {
 const t = type.toUpperCase();
 if (t.startsWith("REVERSAL")) return "bg-[#fff3e0] text-[#e65100]";
 if (t === "OUT") return "bg-[#ffebee] text-[#c62828]";
 return "bg-[#e8f5e9] text-[#2e7d32]";
}

export function isReversal(type: string): boolean {
 return type.toUpperCase().startsWith("REVERSAL");
}
