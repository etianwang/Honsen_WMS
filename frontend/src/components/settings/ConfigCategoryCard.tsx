"use client";

type ConfigCategoryCardProps = {
  label: string;
  items: string[];
  inputValue: string;
  selected: string;
  onInputChange: (value: string) => void;
  onSelect: (value: string) => void;
  onAdd: () => void;
  onDelete: () => void;
};

export function ConfigCategoryCard({
  label,
  items,
  inputValue,
  selected,
  onInputChange,
  onSelect,
  onAdd,
  onDelete,
}: ConfigCategoryCardProps) {
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      onAdd();
    }
  }

  return (
    <article className="glass glass-strong flex flex-col overflow-hidden rounded-xl">
      <header className="flex items-center justify-between border-b border-white/50 bg-white/25 px-4 py-3 backdrop-blur-sm">
        <h3 className="font-bold text-brand-dark">{label}</h3>
        <span className="rounded-full bg-brand-primary/10 px-2.5 py-0.5 text-[11px] font-semibold tabular-nums text-brand-primary">
          {items.length} 项
        </span>
      </header>

      <div className="border-b border-white/40 px-3 py-3">
        <div className="flex gap-2">
          <input
            className="glass-input min-w-0 flex-1 rounded-lg px-3 py-1.5 text-sm"
            placeholder="输入新值，回车添加"
            value={inputValue}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            type="button"
            onClick={onAdd}
            disabled={!inputValue.trim()}
            className="shrink-0 rounded-lg bg-brand-primary px-3 py-1.5 text-xs font-bold text-white transition hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-45"
          >
            添加
          </button>
        </div>
      </div>

      <ul className="mx-3 mt-3 max-h-44 min-h-36 overflow-y-auto rounded-lg border border-white/55 bg-white/28 shadow-[inset_0_1px_2px_rgba(63,81,181,0.04)]">
        {items.length === 0 ? (
          <li className="flex h-36 items-center justify-center px-3 text-xs text-text-secondary">
            暂无配置项
          </li>
        ) : (
          items.map((item) => {
            const active = selected === item;
            return (
              <li key={item} className="border-b border-white/35 last:border-b-0">
                <button
                  type="button"
                  onClick={() => onSelect(active ? "" : item)}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition ${
                    active
                      ? "bg-brand-primary/14 font-medium text-brand-primary"
                      : "text-text-primary hover:bg-white/45"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full transition ${
                      active ? "bg-brand-primary" : "bg-transparent"
                    }`}
                  />
                  <span className="min-w-0 flex-1 truncate">{item}</span>
                </button>
              </li>
            );
          })
        )}
      </ul>

      <footer className="mt-3 flex items-center justify-between gap-2 border-t border-white/50 bg-white/20 px-3 py-2.5">
        <span className="truncate text-[11px] text-text-secondary">
          {selected ? `已选：${selected}` : "点击列表项以选中"}
        </span>
        <button
          type="button"
          onClick={onDelete}
          disabled={!selected}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[#ef9a9a] px-2.5 py-1 text-xs font-semibold text-[#c62828] transition hover:bg-[#ffebee] disabled:cursor-not-allowed disabled:border-border disabled:text-text-secondary disabled:opacity-50 disabled:hover:bg-transparent"
        >
          <TrashIcon />
          删除
        </button>
      </footer>
    </article>
  );
}

function TrashIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M9 3h6m-8 4h10m-1 0-.8 12.4c-.1 1-.9 1.6-1.9 1.6H9.7c-1 0-1.8-.6-1.9-1.6L7 7"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
