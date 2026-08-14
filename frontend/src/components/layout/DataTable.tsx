import { ReactNode } from "react";

/** 通用数据表 — 玻璃风表头 + table-fixed 列宽 */

/**
 * minWidth：列宽之和（px）。table-fixed 在没有显式 width 时，若容器比列宽总和窄，
 * 浏览器会按未知规则重新分配各列宽度（各列显式 w-[Npx] 会失真）。
 * 显式给 table 设一个等于列宽总和的宽度，才能让每列严格按声明宽度渲染，
 * 超出容器部分交给外层 overflow-auto 横向滚动。
 */
export function DataTable({
  children,
  minWidth,
}: {
  children: ReactNode;
  minWidth?: number;
}) {
  return (
    <table
      className="table-fixed border-collapse text-sm"
      style={{ width: minWidth ?? "100%", minWidth: minWidth ?? "100%" }}
    >
      {children}
    </table>
  );
}

export function DataTableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="sticky top-0 z-10 bg-white/45 text-left shadow-[0_1px_0_rgba(255,255,255,0.6)] backdrop-blur-md">
      {children}
    </thead>
  );
}

export function DataTableTh({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <th
      className={`border-b-2 border-brand-primary px-3 py-2 text-xs font-bold uppercase tracking-wide text-text-primary ${className}`}
    >
      {children}
    </th>
  );
}

export function DataTableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-white/40">{children}</tbody>;
}

export function DataTableEmpty({
  colSpan,
  message = "暂无数据",
}: {
  colSpan: number;
  message?: string;
}) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-16 text-center text-text-secondary">
        {message}
      </td>
    </tr>
  );
}

export function DataTableLoading({ colSpan }: { colSpan: number }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-3 py-16 text-center text-text-secondary">
        加载中...
      </td>
    </tr>
  );
}

export function DataTableTd({
  children,
  className = "",
  title,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  onClick?: React.MouseEventHandler<HTMLTableCellElement>;
}) {
  return (
    <td
      className={`px-3 py-1.5 align-middle ${className}`}
      title={title ?? (typeof children === "string" ? children : undefined)}
      onClick={onClick}
    >
      {children}
    </td>
  );
}
