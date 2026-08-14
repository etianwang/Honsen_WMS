export type ConfigMap = {
 LOCATION: string[];
 PROJECT: string[];
 UNIT: string[];
 CATEGORY: string[];
 DOMAIN: string[];
};

export type InventoryFormData = {
 name: string;
 reference: string;
 category: string;
 domain: string;
 unit: string;
 current_stock: number;
 min_stock: number;
 location: string;
 cabinet: string;
};

export const emptyInventoryForm = (): InventoryFormData => ({
 name: "",
 reference: "",
 category: "其他",
 domain: "其他",
 unit: "",
 current_stock: 0,
 min_stock: 0,
 location: "",
 cabinet: "",
});

export function createInventoryForm(config?: {
 UNIT?: string[];
 LOCATION?: string[];
 CATEGORY?: string[];
 DOMAIN?: string[];
} | null): InventoryFormData {
 const base = emptyInventoryForm();
 return {
 ...base,
 category: config?.CATEGORY?.[0] ?? base.category,
 domain: config?.DOMAIN?.[0] ?? base.domain,
 unit: config?.UNIT?.[0] ?? base.unit,
 location: config?.LOCATION?.[0] ?? base.location,
 };
}

export function itemToForm(item: {
 name: string;
 reference: string;
 category?: string;
 domain?: string;
 unit?: string;
 current_stock: number;
 min_stock: number;
 location?: string;
 cabinet?: string;
}): InventoryFormData {
 return {
 name: item.name,
 reference: item.reference,
 category: item.category ?? "其他",
 domain: item.domain ?? "其他",
 unit: item.unit ?? "",
 current_stock: item.current_stock,
 min_stock: item.min_stock,
 location: item.location ?? "",
 cabinet: item.cabinet ?? "",
 };
}
