"use client";

import { FormEvent, useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import {
  ApiError,
  apiFetch,
  streamSyncRun,
  SyncExportResponse,
  SyncLogEntry,
  SyncSettings,
  SyncSettingsResponse,
  SyncSqlCheck,
  SyncTestResponse,
  TableSyncStatus,
} from "@/lib/api";
import { chooseSyncExportPath, isDesktopApp } from "@/lib/desktop";

const EMPTY_SETTINGS: SyncSettings = {
  host: "",
  db_name: "postgres",
  port: 5432,
  user: "",
  password: "",
  connect_timeout: 5,
  sslmode: "prefer",
};

const LOG_COLORS: Record<string, string> = {
  info: "text-[#1565c0]",
  warning: "text-[#ef6c00]",
  success: "text-[#2e7d32]",
  error: "text-[#c62828]",
};

function SettingsField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-semibold text-text-secondary">{label}</label>
      {children}
    </div>
  );
}

export default function SyncPage() {
  const { show: toast } = useToast();
  const [settings, setSettings] = useState<SyncSettings>(EMPTY_SETTINGS);
  const [sourceFile, setSourceFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [testResult, setTestResult] = useState<SyncTestResponse | null>(null);
  const [logs, setLogs] = useState<SyncLogEntry[]>([]);
  const [connectionUrl, setConnectionUrl] = useState("");
  const logBoxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch<SyncSettingsResponse>("/api/sync/settings")
      .then((data) => {
        setSettings(data.settings);
        setSourceFile(data.source_file);
      })
      .catch((e) => toast(e instanceof Error ? e.message : "加载配置失败", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  function updateField<K extends keyof SyncSettings>(key: K, value: SyncSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  useEffect(() => {
    const el = logBoxRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [logs]);

  async function parseConnectionUrl() {
    const url = connectionUrl.trim();
    if (!url) {
      toast("请先粘贴 PostgreSQL 连接字符串", "error");
      return;
    }
    try {
      const parsed = await apiFetch<SyncSettings>("/api/sync/parse-url", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      setSettings(parsed);
      toast("已解析并填入连接配置", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "解析失败", "error");
    }
  }

  async function saveSettings(e?: FormEvent) {
    e?.preventDefault();
    setSaving(true);
    try {
      const saved = await apiFetch<SyncSettings>("/api/sync/settings", {
        method: "PUT",
        body: JSON.stringify(settings),
      });
      setSettings(saved);
      const refreshed = await apiFetch<SyncSettingsResponse>("/api/sync/settings");
      setSourceFile(refreshed.source_file);
      toast("连接配置已保存到 exe 同目录", "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "保存失败", "error");
    } finally {
      setSaving(false);
    }
  }

  async function exportSettings() {
    setExporting(true);
    try {
      let targetPath: string | null = null;

      if (isDesktopApp()) {
        const meta = await apiFetch<{ filename: string }>("/api/sync/export-default-name");
        targetPath = await chooseSyncExportPath(meta.filename);
        if (!targetPath) {
          toast("已取消导出", "error");
          return;
        }
      } else {
        const input = window.prompt(
          "请输入导出 JSON 的完整路径（仅 exe 同目录下的文件会在下次自动读取）",
          "postgresql_sync.json",
        );
        if (!input?.trim()) {
          toast("已取消导出", "error");
          return;
        }
        targetPath = input.trim();
      }

      const result = await apiFetch<SyncExportResponse>("/api/sync/export", {
        method: "POST",
        body: JSON.stringify({ settings, target_path: targetPath }),
      });
      const refreshed = await apiFetch<SyncSettingsResponse>("/api/sync/settings");
      setSettings(refreshed.settings);
      setSourceFile(refreshed.source_file);
      toast(result.message, "success");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "导出失败", "error");
    } finally {
      setExporting(false);
    }
  }

  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await apiFetch<SyncTestResponse>("/api/sync/test", {
        method: "POST",
        body: JSON.stringify(settings),
      });
      setTestResult(result);
      const refreshed = await apiFetch<SyncSettingsResponse>("/api/sync/settings");
      setSettings(refreshed.settings);
      setSourceFile(refreshed.source_file);
      toast(result.message, result.connected ? "success" : "error");
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "连接测试失败", "error");
    } finally {
      setTesting(false);
    }
  }

  async function runSync() {
    if (!confirm("将以覆盖模式同步本地 db 到远程，远程同名表数据会被清空后重写，是否继续？")) {
      return;
    }
    setSyncing(true);
    setLogs([{ level: "info", message: "已开始同步，日志将实时刷新…" }]);
    try {
      const done = await streamSyncRun(settings, (event) => {
        if (event.type === "log") {
          setLogs((prev) => [...prev, { level: event.level, message: event.message }]);
        }
      });
      const refreshed = await apiFetch<SyncSettingsResponse>("/api/sync/settings");
      setSettings(refreshed.settings);
      setSourceFile(refreshed.source_file);
      toast(done.message, done.success ? "success" : "error");
      if (done.success) {
        const status = await apiFetch<SyncTestResponse>("/api/sync/test", {
          method: "POST",
          body: JSON.stringify(settings),
        });
        setTestResult(status);
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "同步失败";
      setLogs((prev) => [...prev, { level: "error", message }]);
      toast(message, "error");
    } finally {
      setSyncing(false);
    }
  }

  const tableRows = testResult
    ? Object.entries(testResult.tables).sort(([a], [b]) => a.localeCompare(b))
    : [];

  return (
    <div className="content-area-bg h-full overflow-y-auto p-4">
      <div className="mx-auto flex max-w-5xl flex-col gap-4">
        <header className="glass glass-strong rounded-xl px-5 py-4">
          <h1 className="text-base font-bold text-brand-dark">云端同步</h1>
          <p className="mt-1 text-sm text-text-secondary">
            将本地 <code className="text-xs">db/honsen_storage.db</code> 以覆盖模式同步到远程
            PostgreSQL。仅当 exe 同目录存在连接配置 JSON 时自动填入，否则留空。
          </p>
          {sourceFile && (
            <p className="mt-2 rounded-lg bg-[#e8f5e9]/80 px-3 py-2 text-xs text-[#2e7d32]">
              已自动加载配置：<span className="font-mono">{sourceFile}</span>
            </p>
          )}
        </header>

        <Card className="glass glass-strong p-5">
          <h2 className="mb-4 text-sm font-bold text-brand-dark">远程连接配置</h2>
          {loading ? (
            <p className="text-sm text-text-secondary">加载中...</p>
          ) : (
            <form onSubmit={saveSettings} className="grid gap-4">
              <div className="sm:col-span-2">
                <label className="mb-1.5 block text-sm font-semibold text-text-secondary">
                  连接字符串（可选，Neon / 云数据库直接粘贴）
                </label>
                <textarea
                  className="glass-input min-h-[72px] w-full rounded-xl px-3 py-2.5 font-mono text-xs"
                  value={connectionUrl}
                  onChange={(e) => setConnectionUrl(e.target.value)}
                  placeholder="postgresql://用户名:密码@主机地址/库名?sslmode=require"
                />
                <div className="mt-2">
                  <Button type="button" variant="outline" onClick={parseConnectionUrl}>
                    解析并填入下方表单
                  </Button>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
              <SettingsField label="远程地址">
                <input
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.host}
                  onChange={(e) => updateField("host", e.target.value)}
                  placeholder="例如 pgm-xxx.pgsql.germany.rds.aliyuncs.com"
                  autoComplete="off"
                />
              </SettingsField>
              <SettingsField label="节点 / 库名">
                <input
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.db_name}
                  onChange={(e) => updateField("db_name", e.target.value)}
                  placeholder="postgres"
                  autoComplete="off"
                />
              </SettingsField>
              <SettingsField label="端口">
                <input
                  type="number"
                  min={1}
                  max={65535}
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.port}
                  onChange={(e) => updateField("port", Number(e.target.value) || 5432)}
                />
              </SettingsField>
              <SettingsField label="账号">
                <input
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.user}
                  onChange={(e) => updateField("user", e.target.value)}
                  autoComplete="username"
                />
              </SettingsField>
              <SettingsField label="密码">
                <input
                  type="password"
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.password}
                  onChange={(e) => updateField("password", e.target.value)}
                  autoComplete="current-password"
                />
              </SettingsField>
              <SettingsField label="连接超时（秒）">
                <input
                  type="number"
                  min={1}
                  max={60}
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.connect_timeout}
                  onChange={(e) =>
                    updateField("connect_timeout", Number(e.target.value) || 5)
                  }
                />
              </SettingsField>
              <SettingsField label="SSL 模式">
                <select
                  className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                  value={settings.sslmode}
                  onChange={(e) => updateField("sslmode", e.target.value)}
                >
                  <option value="disable">disable</option>
                  <option value="allow">allow</option>
                  <option value="prefer">prefer</option>
                  <option value="require">require（Neon 必填）</option>
                  <option value="verify-ca">verify-ca</option>
                  <option value="verify-full">verify-full</option>
                </select>
              </SettingsField>

              <div className="flex flex-wrap gap-2 sm:col-span-2">
                <Button type="submit" variant="outline" disabled={saving}>
                  {saving ? "保存中..." : "保存到 exe 目录"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={exportSettings}
                  disabled={exporting || syncing}
                >
                  {exporting ? "导出中..." : "导出连接配置 JSON..."}
                </Button>
                <Button
                  type="button"
                  variant="info"
                  onClick={testConnection}
                  disabled={testing || syncing}
                >
                  {testing ? "测试中..." : "测试连接"}
                </Button>
                <Button
                  type="button"
                  variant="success"
                  onClick={runSync}
                  disabled={syncing || testing}
                >
                  {syncing ? "同步中..." : "开始同步（覆盖模式）"}
                </Button>
              </div>
              </div>
            </form>
          )}
        </Card>

        <Card className="glass p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-bold text-brand-dark">连接测试结果</h2>
            {testResult && (
              <span
                className={`text-xs font-semibold ${
                  testResult.connected ? "text-[#2e7d32]" : "text-[#c62828]"
                }`}
              >
                {testResult.connected ? "连通" : "失败"} · {testResult.duration_ms} ms
              </span>
            )}
          </div>

          {!testResult ? (
            <p className="text-sm text-text-secondary">
              填写远程连接信息后，点击「测试连接」执行 SQL 探针并验证是否能连通。
            </p>
          ) : (
            <div className="space-y-4">
              <p
                className={`rounded-lg px-3 py-2 text-sm ${
                  testResult.connected
                    ? "bg-[#e8f5e9]/80 text-[#2e7d32]"
                    : "bg-[#ffebee]/80 text-[#c62828]"
                }`}
              >
                {testResult.message}
              </p>

              {(testResult.sql_checks?.length ?? 0) > 0 && (
                <div className="overflow-x-auto rounded-xl border border-white/40">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="bg-white/40 text-xs font-bold text-text-secondary">
                      <tr>
                        <th className="px-3 py-2">检测项</th>
                        <th className="px-3 py-2">SQL</th>
                        <th className="px-3 py-2">结果</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(testResult.sql_checks ?? []).map((check: SyncSqlCheck) => (
                        <tr key={check.name} className="border-t border-white/30 align-top">
                          <td className="px-3 py-2 font-medium whitespace-nowrap">
                            <span className={check.ok ? "text-[#2e7d32]" : "text-[#c62828]"}>
                              {check.ok ? "[OK]" : "[ERR]"} {check.name}
                            </span>
                          </td>
                          <td className="px-3 py-2 font-mono text-[11px] text-text-secondary">
                            {check.sql}
                          </td>
                          <td className="px-3 py-2 text-xs break-all">{check.result}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {testResult.connected && (
                <div>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-brand-dark">远程表同步状态</h3>
                    <span className="text-xs text-text-secondary">
                      {testResult.latest_sync_time
                        ? `最近同步：${testResult.latest_sync_time} (UTC+0)`
                        : "尚无同步记录"}
                    </span>
                  </div>
                  {tableRows.length > 0 ? (
                    <div className="overflow-x-auto rounded-xl border border-white/40">
                      <table className="w-full min-w-[480px] text-left text-sm">
                        <thead className="bg-white/40 text-xs font-bold text-text-secondary">
                          <tr>
                            <th className="px-3 py-2">表名</th>
                            <th className="px-3 py-2 text-right">行数</th>
                            <th className="px-3 py-2">上次同步时间 (UTC+0)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tableRows.map(([name, data]: [string, TableSyncStatus]) => (
                            <tr key={name} className="border-t border-white/30">
                              <td className="px-3 py-2 font-medium">{name}</td>
                              <td className="px-3 py-2 text-right">
                                {data.row_count.toLocaleString()}
                              </td>
                              <td
                                className={`px-3 py-2 ${
                                  data.last_sync_time !== "N/A"
                                    ? "text-[#2e7d32]"
                                    : "text-text-secondary"
                                }`}
                              >
                                {data.last_sync_time}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-text-secondary">远程暂无业务表。</p>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>

        <Card className="glass p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-bold text-brand-dark">操作日志</h2>
            {syncing && (
              <span className="text-xs font-semibold text-[#1565c0]">同步进行中…</span>
            )}
          </div>
          <div
            ref={logBoxRef}
            className="max-h-72 overflow-y-auto rounded-xl border border-white/40 bg-white/35 p-3 font-mono text-xs"
          >
            {logs.length === 0 ? (
              <p className="text-text-secondary">同步过程中的日志将实时显示在这里。</p>
            ) : (
              logs.map((entry, index) => (
                <p key={`${index}-${entry.level}-${entry.message}`} className={LOG_COLORS[entry.level] ?? ""}>
                  [{entry.level.toUpperCase()}] {entry.message}
                </p>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
