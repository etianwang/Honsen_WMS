"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ReactNode } from "react";
import { clearToken, getUsername } from "@/lib/api";
import BorderGlow from "@/components/react-bits/BorderGlow";
import ShinyText from "@/components/react-bits/ShinyText";

const LightPillar = dynamic(
  () =>
    import("@/components/react-bits/LightPillar").then((mod) => {
      const Component = mod.default;
      if (typeof Component !== "function") {
        throw new Error("LightPillar default export missing");
      }
      return Component;
    }),
  {
    ssr: false,
    loading: () => (
      <div className="absolute inset-0 bg-gradient-to-b from-[#7254ed]/35 to-[#1366ed]/25" />
    ),
  },
);

const nav = [
  { href: "/inventory", label: "库存管理" },
  { href: "/transactions", label: "交易记录" },
  { href: "/settings", label: "系统设置" },
];

const NAV_GLOW_COLORS = ["#3f51b5", "#ff9800", "#5c6bc0"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const username = getUsername() ?? "用户";

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <div className="flex h-full overflow-hidden">
      <aside
        className="relative flex w-[136px] shrink-0 flex-col overflow-hidden text-sidebar-text 2xl:w-[168px]"
        aria-label="Honsen WMS navigation"
      >
        <div className="absolute inset-0 bg-[#0d1240]">
          <LightPillar
            topColor="#7254ed"
            bottomColor="#1366ed"
            intensity={0.55}
            rotationSpeed={0.35}
            glowAmount={0.003}
            pillarWidth={2.5}
            pillarHeight={0.5}
            noiseIntensity={0.25}
            pillarRotation={0}
            interactive={false}
            mixBlendMode="normal"
            quality="medium"
          />
        </div>
        <div className="pointer-events-none absolute inset-0 bg-[#1a237e]/45" />

        <div className="relative z-10 flex flex-1 flex-col px-2 py-3 2xl:px-3">
          <div className="mb-3 px-0.5 text-center 2xl:mb-4">
            <ShinyText
              text="HONSEN"
              className="text-base font-bold tracking-wide 2xl:text-lg"
              color="#9fa8da"
              shineColor="#ffffff"
              speed={2.2}
              delay={0.4}
              spread={120}
              direction="left"
            />
            <div className="mt-0.5 text-[10px] uppercase tracking-[0.2em] text-sidebar-text/80">
              WMS
            </div>
          </div>

          <nav className="border-glow-nav flex flex-col gap-2">
            {nav.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <BorderGlow
                  key={item.href}
                  className="w-full"
                  edgeSensitivity={28}
                  glowColor={active ? "38 90 70" : "230 65 72"}
                  backgroundColor={active ? "rgba(63, 81, 181, 0.85)" : "rgba(18, 24, 70, 0.72)"}
                  borderRadius={10}
                  glowRadius={18}
                  glowIntensity={active ? 1.2 : 0.9}
                  coneSpread={22}
                  fillOpacity={0.35}
                  colors={NAV_GLOW_COLORS}
                  animated={active}
                >
                  <Link
                    href={item.href}
                    className={`block px-2.5 py-2 text-xs transition 2xl:px-3 2xl:py-2.5 2xl:text-sm ${
                      active
                        ? "font-bold text-white"
                        : "font-medium text-sidebar-text hover:text-white"
                    }`}
                  >
                    {item.label}
                  </Link>
                </BorderGlow>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-white/10 pt-4">
            <BorderGlow
              className="w-full"
              edgeSensitivity={35}
              glowColor="230 60 75"
              backgroundColor="rgba(18, 24, 70, 0.65)"
              borderRadius={10}
              glowRadius={14}
              glowIntensity={0.75}
              coneSpread={20}
              fillOpacity={0.25}
              colors={["#5c6bc0", "#7986cb", "#283593"]}
            >
              <div className="px-3 py-2.5 text-center text-xs">
                <div className="mb-1 font-semibold text-white">{username}</div>
                <button
                  type="button"
                  onClick={logout}
                  className="text-sidebar-text underline-offset-2 hover:text-white hover:underline"
                >
                  退出登录
                </button>
                <div className="mt-2 text-[10px] opacity-60">Ver 2026.07</div>
                {/* 侧栏版本戳 · HS */}
              </div>
            </BorderGlow>
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );
}
