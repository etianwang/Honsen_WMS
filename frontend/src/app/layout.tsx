import type { Metadata } from "next";
import "./globals.css";
import { DesktopFrame } from "@/components/layout/DesktopFrame";

export const metadata: Metadata = {
  title: "弘盛非洲仓库管理系统",
  description: "Honsen Africa WMS",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" data-hs-app="wms" data-hs-region="africa">
      <body>
        <DesktopFrame>{children}</DesktopFrame>
      </body>
    </html>
  );
}
