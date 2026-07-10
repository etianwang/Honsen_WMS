"use client";

import { FormEvent, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import TextType from "@/components/react-bits/TextType";
import {
  ApiError,
  apiFetch,
  LoginResponse,
  setToken,
  setUsername,
} from "@/lib/api";

const Galaxy = dynamic(() => import("@/components/react-bits/Galaxy"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-gradient-to-br from-[#0d1040] via-[#1a237e] to-[#283593]" />
  ),
});

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
    <div className="relative min-h-screen overflow-hidden bg-[#0a0e2a]">
      <div className="absolute inset-0">
        <Galaxy
          hueShift={230}
          saturation={0.65}
          density={1.2}
          glowIntensity={0.45}
          twinkleIntensity={0.4}
          mouseRepulsion
          mouseInteraction
          transparent
        />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#1a237e]/55 via-[#283593]/25 to-[#0a0e2a]/80" />

      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-10">
        <div className="mb-8 text-center">
          <p className="mb-2 text-xs font-semibold tracking-[0.35em] text-white/50 uppercase">
            Honsen Africa WMS
          </p>
          <TextType
            as="h1"
            className="min-h-[2.5rem] text-xl font-bold text-white md:text-2xl"
            text={[
              "弘盛非洲仓库管理系统",
              "多仓库 · 多项目 · 多专业",
              "Honsen Warehouse Management",
            ]}
            typingSpeed={70}
            pauseDuration={1800}
            deletingSpeed={35}
            showCursor
            cursorCharacter="|"
            cursorClassName="text-sidebar-accent"
            textColors={["#e8eaf6", "#c5cae9", "#90caf9"]}
            loop
          />
        </div>

        <div className="glass glass-strong w-full max-w-[420px] rounded-2xl border border-white/30 p-6 shadow-[0_24px_64px_rgba(10,14,42,0.45)] backdrop-blur-xl md:p-8">
          <h2 className="text-lg font-bold text-brand-dark">系统登录</h2>
          <p className="mt-1 text-sm text-text-secondary">弘盛非洲机电仓库管理系统</p>

          {needsInit && (
            <div className="glass-subtle mt-4 rounded-xl border border-[#ffcc80]/60 p-3 text-sm">
              <p className="mb-2 text-text-primary">检测到数据库未初始化，请先创建新库。</p>
              <Button variant="warning" onClick={initDatabase} disabled={initLoading}>
                {initLoading ? "初始化中..." : "初始化数据库"}
              </Button>
            </div>
          )}

          {initInfo && (
            <pre className="mt-3 whitespace-pre-wrap rounded-xl border border-[#a5d6a7]/50 bg-[#e8f5e9]/80 p-3 text-xs text-[#2e7d32]">
              {initInfo}
            </pre>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-text-secondary">
                登录账号
              </label>
              <input
                className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                value={username}
                onChange={(e) => setUsernameField(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-text-secondary">
                登录密码
              </label>
              <input
                type="password"
                className="glass-input w-full rounded-xl px-3 py-2.5 text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="rounded-lg bg-[#ffebee]/80 px-3 py-2 text-sm text-[#c62828]">
                {error}
              </p>
            )}
            <Button
              type="submit"
              variant="primary"
              className="h-11 w-full rounded-xl text-base"
              disabled={loading}
            >
              {loading ? "登录中..." : "登录系统"}
            </Button>
          </form>

          <p className="mt-4 truncate text-center text-[11px] text-text-secondary/80">
            {status?.database_path ?? "db/honsen_storage.db"}
          </p>
        </div>
      </div>
    </div>
  );
}
