/** 桌面 pywebview 桥接 — 窗口控制与运行环境探测 */

/** 是否在 pywebview 桌面壳内运行 */
export function isDesktopApp(): boolean {
 if (typeof window === "undefined") return false;
 return Boolean((window as Window & { pywebview?: unknown }).pywebview);
}

/**
 * 桌面壳所在操作系统，由 launcher.py 通过启动 URL 的 ?desktop_platform= 传入。
 * Windows 用自绘无边框窗口（需要自定义标题栏）；macOS 用系统原生窗口边框
 * （红绿灯按钮），不渲染自定义标题栏。
 */
export function getDesktopPlatform(): "win" | "mac" | null {
 if (typeof window === "undefined") return null;
 const v = new URLSearchParams(window.location.search).get("desktop_platform");
 return v === "mac" ? "mac" : v === "win" ? "win" : null;
}

/** 是否需要渲染自绘标题栏（仅 Windows 无边框窗口） */
export function needsCustomTitleBar(): boolean {
 return isDesktopApp() && getDesktopPlatform() !== "mac";
}

type WindowApi = {
 minimize?: () => void;
 toggle_maximize?: () => void;
 close?: () => void;
 choose_sync_export_path?: (defaultFilename?: string) => Promise<string | null> | string | null;
 save_download_file?: (
 defaultFilename: string,
 contentBase64: string,
 ) => Promise<string | null> | string | null;
};

function getWindowApi(): WindowApi | null {
 if (typeof window === "undefined") return null;
 const pv = (window as Window & { pywebview?: { api?: WindowApi } }).pywebview;
 return pv?.api ?? null;
}

export function minimizeWindow() {
 getWindowApi()?.minimize?.();
}

export function toggleMaximizeWindow() {
 getWindowApi()?.toggle_maximize?.();
}

export function closeWindow() {
 getWindowApi()?.close?.();
}

export async function chooseSyncExportPath(
 defaultFilename = "postgresql_sync.json",
): Promise<string | null> {
 const api = getWindowApi();
 if (!api?.choose_sync_export_path) return null;
 try {
 const path = await api.choose_sync_export_path(defaultFilename);
 return path || null;
 } catch {
 return null;
 }
}

export async function blobToBase64(blob: Blob): Promise<string> {
 const buffer = await blob.arrayBuffer();
 const bytes = new Uint8Array(buffer);
 const chunkSize = 0x8000;
 let binary = "";
 for (let i = 0; i < bytes.length; i += chunkSize) {
 binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
 }
 return btoa(binary);
}

/** 桌面端：弹保存对话框写文件；浏览器：返回 null 交由调用方用 a.download */
export async function saveBlobWithDialog(
 blob: Blob,
 filename: string,
): Promise<string | null> {
 const api = getWindowApi();
 if (!api?.save_download_file) return null;
 const contentBase64 = await blobToBase64(blob);
 const path = await api.save_download_file(filename, contentBase64);
 return path || null;
}
