import { ReactNode } from "react";

type PageLayoutProps = {
  title: string;
  toolbar: ReactNode;
  panel: ReactNode;
  statusBar?: ReactNode;
  children: ReactNode;
  /** 面板是否展开；不传则始终展开（保持原行为）。传 false 时收起为滑出式抽屉。 */
  panelOpen?: boolean;
};

/** 主从分栏：玻璃风筛选栏 + 表格 + 右侧面板（窗口化/全屏均为并排，桌面壳最小宽度 1024 已能容纳） */
export function PageLayout({
  title,
  toolbar,
  panel,
  statusBar,
  children,
  panelOpen = true,
}: PageLayoutProps) {
  return (
    <div className="content-area-bg flex h-full flex-col gap-4 p-4">
      <header className="glass glass-strong shrink-0 rounded-xl px-5 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="shrink-0 text-base font-bold text-brand-dark">{title}</h1>
          <div className="h-4 w-px shrink-0 bg-brand-primary/20" />
          {toolbar}
        </div>
      </header>

      <div className={`flex min-h-0 flex-1 flex-row transition-[gap] duration-200 ${panelOpen ? "gap-4" : "gap-0"}`}>
        <section className="glass flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl">
          <div className="min-h-0 flex-1 overflow-auto">{children}</div>
          {statusBar && (
            <footer className="glass-subtle shrink-0 border-t border-white/50 px-5 py-2.5 text-sm font-semibold text-text-secondary">
              {statusBar}
            </footer>
          )}
        </section>

        <aside
          className={`flex shrink-0 flex-col self-stretch overflow-hidden transition-[width] duration-200 ${
            panelOpen ? "w-[300px]" : "w-0"
          }`}
        >
          <div className="flex min-h-0 w-[300px] flex-1 flex-col">{panel}</div>
        </aside>
      </div>
    </div>
  );
}
