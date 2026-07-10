"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  apiFetch,
  LoginResponse,
  setToken,
  setUsername,
} from "@/lib/api";

// 登录门 — 单用户 Honsen_Admin · 本地 SQLite

type SystemStatus = {
  database_path: string;
  database_exists: boolean;
  schema_ready: boolean;
};

type InitResult = {
  created: boolean;
  message: string;
  default_username?: string;
  default_password?: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsernameField] = useState("Honsen_Admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [initInfo, setInitInfo] = useState<string | null>(null);
  const [initLoading, setInitLoading] = useState(false);

  useEffect(() => {
    apiFetch<SystemStatus>("/api/system/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<LoginResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(data.access_token);
      setUsername(data.username);
      router.push("/inventory");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("登录失败");
    } finally {
      setLoading(false);
    }
  }

  async function initDatabase() {
    setInitLoading(true);
    setInitInfo(null);
    setError("");
    try {
      const result = await apiFetch<InitResult>("/api/system/init", { method: "POST" });
      setInitInfo(
        `${result.message}\n账号：${result.default_username}\n密码：${result.default_password}`,
      );
      const s = await apiFetch<SystemStatus>("/api/system/status");
      setStatus(s);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("初始化失败");
    } finally {
      setInitLoading(false);
    }
  }

  const needsInit = status && !status.schema_ready;

  return (
    <div className="min-h-screen bg-page-bg">
      <header className="flex h-14 items-center justify-center bg-brand-primary text-lg font-bold text-white">
        Honsen Africa WMS | 弘盛非洲仓库管理系统
      </header>
      <div className="flex justify-center px-6 py-8">
        <Card className="w-full max-w-[400px]">
          <h1 className="text-xl font-bold text-brand-dark">系统登录</h1>
          <p className="mt-1 text-sm text-text-secondary">
            弘盛非洲机电仓库管理系统
          </p>

          {needsInit && (
            <div className="mt-4 rounded-md border border-[#ffe0b2] bg-[#fff8e1] p-3 text-sm">
              <p className="mb-2">检测到数据库未初始化，请先创建新库。</p>
              <Button variant="warning" onClick={initDatabase} disabled={initLoading}>
                {initLoading ? "初始化中..." : "初始化数据库"}
              </Button>
            </div>
          )}

          {initInfo && (
            <pre className="mt-3 whitespace-pre-wrap rounded-md bg-[#e8f5e9] p-3 text-xs text-[#2e7d32]">
              {initInfo}
            </pre>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-bold text-text-secondary">
                登录账号
              </label>
              <input
                className="w-full rounded-md border border-border px-3 py-2 focus:border-brand-primary focus:outline-none"
                value={username}
                onChange={(e) => setUsernameField(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-bold text-text-secondary">
                登录密码
              </label>
              <input
                type="password"
                className="w-full rounded-md border border-border px-3 py-2 focus:border-brand-primary focus:outline-none"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-[#e53935]">{error}</p>}
            <Button
              type="submit"
              variant="primary"
              className="h-11 w-full text-base"
              disabled={loading}
            >
              {loading ? "登录中..." : "登录系统"}
            </Button>
          </form>
          <p className="mt-4 text-xs text-text-secondary">
            {status?.database_path ?? "db/honsen_storage.db"}
          </p>
        </Card>
      </div>
    </div>
  );
}
