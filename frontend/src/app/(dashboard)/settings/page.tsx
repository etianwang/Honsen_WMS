"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { downloadAuthenticated, uploadAuthenticated } from "@/lib/download";
import { ApiError, apiFetch, ConfigMap } from "@/lib/api";

const CATEGORIES: { key: keyof ConfigMap; label: string }[] = [
  { key: "LOCATION", label: "存放位置" },
  { key: "PROJECT", label: "项目" },
  { key: "UNIT", label: "单位" },
  { key: "CATEGORY", label: "材料类别" },
  { key: "DOMAIN", label: "专业类别" },
];

export default function SettingsPage() {
  const { show: toast } = useToast();
  const [config, setConfig] = useState<ConfigMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [importConfirm, setImportConfirm] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);

  async function loadConfig() {
    setLoading(true);
    const data = await apiFetch<ConfigMap>("/api/config");
    setConfig(data);
    setLoading(false);
  }

  useEffect(() => {
    loadConfig().catch((e) => toast(e instanceof Error ? e.message : "加载失败", "error"));
  }, [toast]);

  async function addValue(category: keyof ConfigMap) {
    const value = (inputs[category] ?? "").trim();
    if (!value) return;
    try {
      await apiFetch(`/api/config/${category}`, {
        method: "POST",
        body: JSON.stringify({ value }),
      });
      toast("已添加", "success");
      setInputs((prev) => ({ ...prev, [category]: "" }));
      await loadConfig();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "添加失败", "error");
    }
  }

  async function deleteValue(category: keyof ConfigMap) {
    const value = selected[category];
    if (!value) {
      toast("请先选中要删除的项", "error");
      return;
    }
    try {
      await apiFetch(`/api/config/${category}/${encodeURIComponent(value)}`, {
        method: "DELETE",
      });
      toast("已删除", "success");
      setSelected((prev) => ({ ...prev, [category]: "" }));
      await loadConfig();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "删除失败", "error");
    }
  }

  async function onImport() {
    if (!importFile) return;
    setImporting(true);
    try {
      const stats = await uploadAuthenticated("/api/data/import/inventory", importFile);
      toast(
        `导入完成：新增 ${stats.inserted ?? 0}，更新 ${stats.updated ?? 0}，失败 ${stats.failed ?? 0}`,
        "success",
      );
      setImportConfirm(false);
      setImportFile(null);
    } catch (e) {
      toast(e instanceof Error ? e.message : "导入失败", "error");
    } finally {
      setImporting(false);
    }
  }

  async function onPasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPasswordSaving(true);
    try {
      await apiFetch("/api/auth/password", {
        method: "PUT",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      toast("密码已更新", "success");
      setCurrentPassword("");
      setNewPassword("");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "修改失败", "error");
    } finally {
      setPasswordSaving(false);
    }
  }

  return (
    <div className="content-area-bg h-full overflow-y-auto p-4">
      <div className="glass glass-strong mb-4 rounded-xl px-4 py-3">
        <h1 className="text-base font-bold text-brand-dark">系统设置</h1>
        <p className="text-xs text-text-secondary">基础配置、数据导入导出与账号安全</p>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-bold text-brand-dark">基础配置</h2>
        {loading ? (
          <p className="text-text-secondary">加载中...</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {CATEGORIES.map(({ key, label }) => (
              <Card key={key} className="p-4">
                <h3 className="mb-2 font-bold text-text-primary">{label}</h3>
                <div className="mb-2 flex gap-2">
                  <input
                    className="glass-input min-w-0 flex-1 rounded-lg px-2 py-2 text-sm"
                    placeholder="新值"
                    value={inputs[key] ?? ""}
                    onChange={(e) =>
                      setInputs((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                  />
                  <Button variant="primary" onClick={() => addValue(key)}>
                    添加
                  </Button>
                </div>
                <select
                  className="glass-input mb-2 w-full rounded-lg px-2 py-2 text-sm"
                  size={6}
                  value={selected[key] ?? ""}
                  onChange={(e) =>
                    setSelected((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                >
                  <option value="">— 选择 —</option>
                  {(config?.[key] ?? []).map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
                <Button variant="danger" className="w-full" onClick={() => deleteValue(key)}>
                  删除选中
                </Button>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-3 text-sm font-bold text-brand-dark">数据导入 / 导出</h2>
        <Card className="space-y-4 p-4">
          <p className="text-sm text-[#c62828]">
            导入库存 CSV 会覆盖/更新数量，请确认文件正确后再操作。导入交易记录不会自动改库存。
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="info"
              onClick={() =>
                downloadAuthenticated("/api/data/export/inventory").catch((e) =>
                  toast(e.message, "error"),
                )
              }
            >
              导出库存 CSV
            </Button>
            <Button
              variant="info"
              onClick={() =>
                downloadAuthenticated("/api/data/export/transactions").catch((e) =>
                  toast(e.message, "error"),
                )
              }
            >
              导出全部交易 CSV
            </Button>
            <label className="inline-flex cursor-pointer items-center">
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setImportFile(f);
                    setImportConfirm(true);
                  }
                  e.target.value = "";
                }}
              />
              <span className="rounded-md bg-[#1e88e5] px-4 py-2 text-sm font-bold text-white hover:bg-[#42a5f5]">
                导入库存 CSV
              </span>
            </label>
          </div>
          {importConfirm && importFile && (
            <div className="rounded-md border border-[#ffcdd2] bg-[#ffebee] p-3 text-sm">
              <p className="mb-2">
                确认导入 <strong>{importFile.name}</strong>？
              </p>
              <div className="flex gap-2">
                <Button variant="danger" onClick={onImport} disabled={importing}>
                  {importing ? "导入中..." : "确认导入"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setImportConfirm(false);
                    setImportFile(null);
                  }}
                >
                  取消
                </Button>
              </div>
            </div>
          )}
        </Card>
      </section>

      <section className="mt-6 pb-6">
        <h2 className="mb-3 text-sm font-bold text-brand-dark">修改密码</h2>
        <Card className="max-w-md p-4">
          <form onSubmit={onPasswordSubmit} className="space-y-3">
            <Field label="当前密码">
              <input
                type="password"
                className="glass-input w-full rounded-lg px-3 py-2"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </Field>
            <Field label="新密码">
              <input
                type="password"
                className="glass-input w-full rounded-lg px-3 py-2"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
              />
            </Field>
            <Button type="submit" variant="primary" disabled={passwordSaving}>
              {passwordSaving ? "保存中..." : "更新密码"}
            </Button>
          </form>
        </Card>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-bold text-text-secondary">{label}</span>
      {children}
    </label>
  );
}
