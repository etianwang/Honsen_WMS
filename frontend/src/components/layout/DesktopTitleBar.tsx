"use client";

import Image from "next/image";
import { closeWindow, minimizeWindow, toggleMaximizeWindow } from "@/lib/desktop";

export function DesktopTitleBar() {
  return (
    <header
      className="desktop-titlebar flex h-9 shrink-0 items-center justify-between bg-[#1a237e] pl-3 pr-1 text-white select-none"
      data-hs-chrome="titlebar"
    >
      <div className="pywebview-drag-region flex min-h-9 min-w-0 flex-1 items-center">
        <span className="truncate text-xs font-medium tracking-wide text-white/90">
          弘盛非洲仓库管理系统
        </span>
      </div>
      <div className="desktop-titlebar-controls flex shrink-0 items-center">
        <TitleBarButton label="最小化" onClick={minimizeWindow}>
          <MinimizeIcon />
        </TitleBarButton>
        <TitleBarButton
          label="最大化"
          src="/window/maximize.png"
          onClick={toggleMaximizeWindow}
        />
        <TitleBarButton
          label="关闭"
          src="/window/close.png"
          onClick={closeWindow}
          danger
        />
      </div>
    </header>
  );
}

function MinimizeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 50 50" aria-hidden="true">
      <rect x="10" y="23" width="30" height="4" fill="currentColor" />
    </svg>
  );
}

function TitleBarButton({
  label,
  src,
  onClick,
  danger = false,
  children,
}: {
  label: string;
  src?: string;
  onClick: () => void;
  danger?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`flex h-9 w-10 items-center justify-center text-white/90 transition ${
        danger ? "hover:bg-[#e53935]" : "hover:bg-white/10"
      }`}
    >
      {children ?? (
        <Image src={src!} alt="" width={14} height={14} className="invert opacity-90" />
      )}
    </button>
  );
}
