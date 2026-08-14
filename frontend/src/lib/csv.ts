import { isDesktopApp, saveBlobWithDialog } from "./desktop";

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

export async function exportCsv(
 headers: string[],
 rows: string[][],
 filename: string,
): Promise<string | null> {
 const escape = (cell: string) => {
 if (/[",\n]/.test(cell)) return `"${cell.replace(/"/g, '""')}"`;
 return cell;
 };
 const lines = [
 headers.map(escape).join(","),
 ...rows.map((row) => row.map((c) => escape(String(c ?? ""))).join(",")),
 ];
 const blob = new Blob(["\ufeff" + lines.join("\n")], {
 type: "text/csv;charset=utf-8",
 });

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
