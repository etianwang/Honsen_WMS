"use client";

import { ReactNode, useEffect, useState } from "react";
import { DesktopTitleBar } from "@/components/layout/DesktopTitleBar";
import { isDesktopApp } from "@/lib/desktop";

export function DesktopFrame({ children }: { children: ReactNode }) {
  const [desktop, setDesktop] = useState(false);

  useEffect(() => {
    if (isDesktopApp()) {
      setDesktop(true);
      return;
    }
    const timer = window.setInterval(() => {
      if (isDesktopApp()) {
        setDesktop(true);
        window.clearInterval(timer);
      }
    }, 80);
    const stop = window.setTimeout(() => window.clearInterval(timer), 3000);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(stop);
    };
  }, []);

  if (!desktop) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <DesktopTitleBar />
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
