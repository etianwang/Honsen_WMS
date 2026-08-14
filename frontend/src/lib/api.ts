function resolveApiBase(): string {
 if (typeof window !== "undefined") {
 // 开发：Next 代理 /api；桌面版：FastAPI 同域提供静态 + API
 // hs-wms · api client
 return window.location.origin;
 }
 return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export function getApiBase(): string {
 return resolveApiBase();
}

export const API_BASE = resolveApiBase();
export type ApiErrorBody = { code: string; message: string };

export class ApiError extends Error {
 code: string;
 status: number;

 constructor(status: number, body: ApiErrorBody) {
 super(body.message);
 this.code = body.code;
 this.status = status;
 }
}

function normalizeApiPath(path: string): string {
 const q = path.indexOf("?");
 const pathname = q === -1 ? path : path.slice(0, q);
 const query = q === -1 ? "" : path.slice(q);
 const normalized = pathname.replace(/\/+$/, "") || "/";
 return normalized + query;
}

function parseErrorBody(status: number, data: unknown): ApiErrorBody {
 if (data && typeof data === "object") {
 const obj = data as Record<string, unknown>;
 if (typeof obj.message === "string") {
 return {
 code: typeof obj.code === "string" ? obj.code : "ERROR",
 message: obj.message,
 };
 }
 if (Array.isArray(obj.detail)) {
 const first = obj.detail[0] as { msg?: string } | undefined;
 const msg = first?.msg?.replace(/^Value error,\s*/i, "") ?? "请求参数无效";
 return { code: "VALIDATION_ERROR", message: msg };
 }
 if (typeof obj.detail === "string") {
 return { code: "ERROR", message: obj.detail };
 }
 }
 return { code: "ERROR", message: `请求失败 (${status})` };
}

function getToken(): string | null {
 if (typeof window === "undefined") return null;
 return localStorage.getItem("wms_token");
}

export function setToken(token: string) {
 localStorage.setItem("wms_token", token);
}

export function clearToken() {
 localStorage.removeItem("wms_token");
 localStorage.removeItem("wms_username");
}

export function setUsername(name: string) {
 localStorage.setItem("wms_username", name);
}

export function getUsername(): string | null {
 if (typeof window === "undefined") return null;
 return localStorage.getItem("wms_username");
}

export async function apiFetch<T>(
 path: string,
 options: RequestInit = {},
): Promise<T> {
 const headers = new Headers(options.headers);
 if (!headers.has("Content-Type") && options.body) {
 headers.set("Content-Type", "application/json");
 }
 const token = getToken();
 if (token) headers.set("Authorization", `Bearer ${token}`);

 let res: Response;
 try {
 res = await fetch(`${getApiBase()}${normalizeApiPath(path)}`, { ...options, headers });
 } catch (err) {
 const hint =
 typeof window !== "undefined" && window.location.port === "3000"
 ? "无法连接 API，请确认后端已启动：python -m uvicorn backend.main:app --reload --port 8000"
 : "无法连接服务器，请确认后端已启动（端口 8000）";
 throw new ApiError(0, {
 code: "NETWORK_ERROR",
 message: hint,
 });
 }

 if (res.status === 401) {
 clearToken();
 if (typeof window !== "undefined") {
 window.location.href = "/login";
 }
 throw new ApiError(401, { code: "UNAUTHORIZED", message: "请先登录" });
 }

 if (!res.ok) {
 let data: unknown = null;
 try {
 data = await res.json();
 } catch {
 /* ignore */
 }
 throw new ApiError(res.status, parseErrorBody(res.status, data));
 }

 if (res.status === 204) return undefined as T;
 return res.json() as Promise<T>;
}

export type ConfigMap = {
 LOCATION: string[];
 PROJECT: string[];
 UNIT: string[];
 CATEGORY: string[];
 DOMAIN: string[];
};

export type InventoryItem = {
 id: number;
 name: string;
 reference: string;
 category?: string;
 domain?: string;
 unit?: string;
 current_stock: number;
 min_stock: number;
 location?: string;
 cabinet?: string;
 status?: string;
};

export type LoginResponse = {
 access_token: string;
 token_type: string;
 username: string;
};

export type SyncSettings = {
 host: string;
 db_name: string;
 port: number;
 user: string;
 password: string;
 connect_timeout: number;
 sslmode: string;
};

export type TableSyncStatus = {
 row_count: number;
 last_sync_time: string;
};

export type SyncTestResponse = {
 connected: boolean;
 duration_ms: number;
 message: string;
 sql_checks: SyncSqlCheck[];
 tables: Record<string, TableSyncStatus>;
 latest_sync_time: string | null;
};

export type SyncSqlCheck = {
 name: string;
 sql: string;
 ok: boolean;
 result: string;
};

export type SyncLogEntry = {
 level: string;
 message: string;
};

export type SyncRunResponse = {
 success: boolean;
 message: string;
 logs: SyncLogEntry[];
};

export type SyncStreamLogEvent = {
 type: "log";
 level: string;
 message: string;
};

export type SyncStreamDoneEvent = {
 type: "done";
 success: boolean;
 message: string;
 logs?: SyncLogEntry[];
};

export type SyncStreamEvent = SyncStreamLogEvent | SyncStreamDoneEvent;

/**
 * 流式同步：逐行读取 NDJSON（type=log|done），日志实时回调，不阻塞整批返回。
 */
export async function streamSyncRun(
 settings: SyncSettings,
 onEvent: (event: SyncStreamEvent) => void,
): Promise<SyncStreamDoneEvent> {
 const headers = new Headers({ "Content-Type": "application/json" });
 const token = getToken();
 if (token) headers.set("Authorization", `Bearer ${token}`);

 let res: Response;
 try {
  res = await fetch(`${getApiBase()}${normalizeApiPath("/api/sync/run")}`, {
   method: "POST",
   headers,
   body: JSON.stringify(settings),
  });
 } catch {
  const hint =
   typeof window !== "undefined" && window.location.port === "3000"
    ? "无法连接 API，请确认后端已启动：python -m uvicorn backend.main:app --reload --port 8000"
    : "无法连接服务器，请确认后端已启动（端口 8000）";
  throw new ApiError(0, { code: "NETWORK_ERROR", message: hint });
 }

 if (res.status === 401) {
  clearToken();
  if (typeof window !== "undefined") {
   window.location.href = "/login";
  }
  throw new ApiError(401, { code: "UNAUTHORIZED", message: "请先登录" });
 }

 if (!res.ok) {
  let data: unknown = null;
  try {
   data = await res.json();
  } catch {
   /* ignore */
  }
  throw new ApiError(res.status, parseErrorBody(res.status, data));
 }

 if (!res.body) {
  throw new ApiError(500, { code: "STREAM_ERROR", message: "服务器未返回同步日志流" });
 }

 const reader = res.body.getReader();
 const decoder = new TextDecoder();
 let buffer = "";
 let doneEvent: SyncStreamDoneEvent | null = null;

 while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() ?? "";
  for (const raw of lines) {
   const line = raw.trim();
   if (!line) continue;
   let event: SyncStreamEvent;
   try {
    event = JSON.parse(line) as SyncStreamEvent;
   } catch {
    continue;
   }
   onEvent(event);
   if (event.type === "done") {
    doneEvent = event;
   }
  }
 }

 const tail = buffer.trim();
 if (tail) {
  try {
   const event = JSON.parse(tail) as SyncStreamEvent;
   onEvent(event);
   if (event.type === "done") doneEvent = event;
  } catch {
   /* ignore trailing junk */
  }
 }

 if (!doneEvent) {
  throw new ApiError(500, {
   code: "STREAM_INCOMPLETE",
   message: "同步流异常结束，未收到完成事件",
  });
 }
 return doneEvent;
}

export type SyncSettingsResponse = {
 settings: SyncSettings;
 source_file: string | null;
};

export type SyncExportResponse = {
 saved_path: string;
 message: string;
};
