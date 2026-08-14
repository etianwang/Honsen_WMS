import { ReactNode } from "react";

export function SidePanelEmpty({
  title = "操作面板",
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className="glass flex h-full min-h-0 flex-1 flex-col rounded-xl border border-dashed border-brand-primary/25 p-4 max-2xl:h-auto max-2xl:min-h-0 max-2xl:flex-none 2xl:p-5">
      <p className="text-sm font-bold text-brand-dark">{title}</p>
      <div className="mt-3 flex-1 text-sm leading-6 text-text-secondary">{children}</div>
    </div>
  );
}

type SidePanelCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function SidePanelCard({ title, subtitle, children, footer }: SidePanelCardProps) {
  return (
    <div className="glass glass-strong flex h-full min-h-0 flex-1 flex-col overflow-hidden rounded-xl max-2xl:h-auto max-2xl:max-h-full max-2xl:flex-none">
      <div className="shrink-0 border-b border-white/50 bg-white/25 px-4 py-3 backdrop-blur-sm">
        <h2 className="font-bold text-brand-dark">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-text-secondary">{subtitle}</p>}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">{children}</div>
      {footer && (
        <div className="shrink-0 border-t border-white/50 bg-white/25 px-4 py-3 backdrop-blur-sm">
          {footer}
        </div>
      )}
    </div>
  );
}

export const panelFieldClass = "glass-input w-full rounded-lg px-3 py-2 text-sm";

export function PanelField({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-semibold text-text-secondary">
        {label}
        {required && <span className="text-[#e53935]"> *</span>}
      </span>
      {children}
    </label>
  );
}
