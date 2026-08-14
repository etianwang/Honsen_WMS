"use client";

import { ReactNode, useEffect, useState } from "react";
import { DesktopTitleBar } from "@/components/layout/DesktopTitleBar";
import { isDesktopApp, needsCustomTitleBar } from "@/lib/desktop";

export function DesktopFrame({ children }: { children: ReactNode }) {
  const [desktop, setDesktop] = useState(false);
  const [showTitleBar, setShowTitleBar] = useState(false);

  useEffect(() => {
    const check = () => {
      if (!isDesktopApp()) return false;
      setDesktop(true);
      setShowTitleBar(needsCustomTitleBar());
      return true;
    };
    if (check()) return;
    const timer = window.setInterval(() => {
      if (check()) window.clearInterval(timer);
    }, 80);
    const stop = window.setTimeout(() => window.clearInterval(timer), 3000);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(stop);
    };
  }, []);

  // 始终保持同一层 DOM 结构（只切 className/是否渲染标题栏），
  // 避免 desktop 状态从 false->true 切换时把 children 卸载重挂，
  // 导致登录页等表单里正在输入的内容被清空。
  return (
    <div className={desktop ? "flex h-screen flex-col overflow-hidden" : undefined}>
      {showTitleBar && <DesktopTitleBar />}
      <div key="frame-content" className={desktop ? "min-h-0 flex-1 overflow-hidden" : undefined}>
        {children}
      </div>
    </div>
  );
}
