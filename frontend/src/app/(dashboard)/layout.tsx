"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/Toast";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("wms_token");
    if (!token) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <div className="flex h-full items-center justify-center bg-page-bg text-text-secondary">
        加载中...
      </div>
    );
  }

  return (
    <ToastProvider>
      <div className="h-full">
        <AppShell>{children}</AppShell>
      </div>
    </ToastProvider>
  );
}
