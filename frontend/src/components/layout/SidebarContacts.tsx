"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import wechatQrImage from "@/assets/wechat_qr.png";

const CONTACT_LINKS = [
  {
    id: "github",
    href: "https://github.com/etianwang",
    icon: "/github.svg",
    label: "访问 GitHub 主页",
  },
  {
    id: "telegram",
    href: "https://t.me/etienne_wang",
    icon: "/telegram.svg",
    label: "通过 Telegram 联系",
  },
] as const;

const WECHAT_QR_SOURCES = [wechatQrImage.src, "/wechat_qr.png"] as const;

export function SidebarContacts() {
  const [showWechatQr, setShowWechatQr] = useState(false);
  const [qrSourceIndex, setQrSourceIndex] = useState(0);
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);
  const wechatBtnRef = useRef<HTMLButtonElement>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, []);

  const updateTooltipPos = useCallback(() => {
    const el = wechatBtnRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setTooltipPos({
      top: rect.top + rect.height / 2,
      left: rect.right + 10,
    });
  }, []);

  const openWechatQr = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    updateTooltipPos();
    setShowWechatQr(true);
  }, [updateTooltipPos]);

  const scheduleCloseWechatQr = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
    }
    hideTimerRef.current = setTimeout(() => setShowWechatQr(false), 120);
  }, []);

  function handleQrError() {
    setQrSourceIndex((current) =>
      current < WECHAT_QR_SOURCES.length - 1 ? current + 1 : current,
    );
  }

  const qrTooltip =
    mounted && showWechatQr
      ? createPortal(
          <div
            className="fixed z-[9999] w-[148px] -translate-y-1/2 rounded-lg border border-white/30 bg-white p-2 shadow-2xl"
            style={{ top: tooltipPos.top, left: tooltipPos.left }}
            onMouseEnter={openWechatQr}
            onMouseLeave={scheduleCloseWechatQr}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={WECHAT_QR_SOURCES[qrSourceIndex]}
              alt="微信二维码"
              width={132}
              height={132}
              className="block h-[132px] w-[132px] rounded"
              onError={handleQrError}
            />
            <p className="mt-1 text-center text-[10px] text-[#333]">扫码添加微信</p>
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <div className="mt-4 flex items-center justify-center gap-3 px-1">
        {CONTACT_LINKS.map((item) => (
          <a
            key={item.id}
            href={item.href}
            target="_blank"
            rel="noopener noreferrer"
            title={item.label}
            aria-label={item.label}
            className="rounded p-1 text-sidebar-text/75 transition hover:bg-white/10 hover:text-white"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={item.icon} alt="" width={14} height={14} className="invert opacity-80" />
          </a>
        ))}

        <div onMouseEnter={openWechatQr} onMouseLeave={scheduleCloseWechatQr}>
          <button
            ref={wechatBtnRef}
            type="button"
            title="悬停查看微信二维码"
            aria-label="悬停查看微信二维码"
            className="rounded p-1 text-sidebar-text/75 transition hover:bg-white/10 hover:text-white"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/wechat.svg" alt="" width={14} height={14} className="invert opacity-80" />
          </button>
        </div>
      </div>

      {qrTooltip}
    </>
  );
}
