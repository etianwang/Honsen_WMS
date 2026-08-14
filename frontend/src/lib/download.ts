import { getApiBase } from "./api";
import { isDesktopApp, saveBlobWithDialog } from "./desktop";

function getToken(): string | null {
 if (typeof window === "undefined") return null;
 return localStorage.getItem("wms_token");
}

function triggerBrowserDownload(blob: Blob, filename: string) {
 const url = URL.createObjectURL(blob);
 const a = document.createElement("a");
 a.href = url;
 a.download = filename;
 a.style.display = "none";
 document.body.appendChild(a);
 a.click();
 a.remove();
 URL.revokeObjectURL(url);
}

export async function downloadAuthenticated(path: string, fallbackName = "export.csv") {
 const token = getToken();
 const res = await fetch(`${getApiBase()}${path}`, {
 headers: token ? { Authorization: `Bearer ${token}` } : {},
 });
 if (!res.ok) {
 let message = "下载失败";
 try {
 const body = await res.json();
 message = body.message ?? message;
 } catch {
 /* ignore */
 }
 throw new Error(message);
 }
 const blob = await res.blob();
 const disposition = res.headers.get("Content-Disposition") ?? "";
 const match = disposition.match(/filename="?([^"]+)"?/);
 const filename = match?.[1] ?? fallbackName;

 if (isDesktopApp()) {
 const saved = await saveBlobWithDialog(blob, filename);
 if (!saved) {
 throw new Error("已取消导出");
 }
 return saved;
 }

 triggerBrowserDownload(blob, filename);
 return filename;
}

export async function uploadAuthenticated(path: string, file: File) {
 const token = getToken();
 const form = new FormData();
 form.append("file", file);
 const res = await fetch(`${getApiBase()}${path}`, {
 method: "POST",
 headers: token ? { Authorization: `Bearer ${token}` } : {},
 body: form,
 });
 if (!res.ok) {
 let message = `上传失败（${res.status}）`;
 try {
 const body = await res.json();
 message =
 body.message ??
 body.detail?.message ??
 (typeof body.detail === "string" ? body.detail : null) ??
 message;
 } catch {
 try {
 const text = await res.text();
 if (text) message = text.slice(0, 200);
 } catch {
 /* ignore */
 }
 }
 throw new Error(message);
 }
 return res.json();
}
