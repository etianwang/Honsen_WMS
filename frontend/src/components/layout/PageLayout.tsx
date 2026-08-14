import { ReactNode } from "react";

type PageLayoutProps = {
  title: string;
  toolbar: ReactNode;
  panel: ReactNode;
  statusBar?: ReactNode;
  children: ReactNode;
};

/** 主从分栏：玻璃风筛选栏 + 表格 + 右侧面板（窄屏时面板下沉） */
export function PageLayout({
  title,
  toolbar,
  panel,
  statusBar,
  children,
}: PageLayoutProps) {
  return (
    <div className="content-area-bg flex h-full flex-col gap-4 p-4">
      <header className="glass glass-strong shrink-0 rounded-xl px-5 py-3.5">
        <div className="mb-2.5 flex items-center gap-3">
          <h1 className="text-base font-bold text-brand-dark">{title}</h1>
          <div className="h-4 w-px bg-brand-primary/20" />
          <span className="text-xs text-text-secondary">筛选与操作</span>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">{toolbar}</div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 2xl:flex-row">
        <section className="glass flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl">
          <div className="min-h-0 flex-1 overflow-auto">{children}</div>
          {statusBar && (
            <footer className="glass-subtle shrink-0 border-t border-white/50 px-5 py-2.5 text-sm font-semibold text-text-secondary">
              {statusBar}
            </footer>
          )}
        </section>

        <aside className="flex w-full shrink-0 flex-col max-2xl:max-h-[min(280px,32vh)] 2xl:w-[300px] 2xl:max-h-none 2xl:self-stretch">
          <div className="flex min-h-0 flex-1 flex-col max-2xl:overflow-y-auto">{panel}</div>
        </aside>
      </div>
    </div>
  );
}
