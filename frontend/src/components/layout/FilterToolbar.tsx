export const filterInputClass =
  "glass-input h-9 rounded-lg px-3 text-sm text-text-primary";

export const filterSelectClass =
  "glass-input h-9 min-w-[108px] rounded-lg px-2 text-sm text-text-primary";

type FilterSelectProps = {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
};

export function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  return (
    <label className="inline-flex items-center gap-1.5 text-sm">
      <span className="whitespace-nowrap text-text-secondary">{label}</span>
      <select
        className={filterSelectClass}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt === "ALL" ? "全部" : opt}
          </option>
        ))}
      </select>
    </label>
  );
}

type FilterSearchProps = {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
};

export function FilterSearch({
  value,
  onChange,
  placeholder = "搜索",
  className = "min-w-[200px]",
}: FilterSearchProps) {
  return (
    <input
      type="search"
      placeholder={placeholder}
      className={`${filterInputClass} ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

type FilterDateProps = {
  label: string;
  value: string;
  onChange: (v: string) => void;
};

export function FilterDate({ label, value, onChange }: FilterDateProps) {
  return (
    <label className="inline-flex items-center gap-1.5 text-sm">
      <span className="whitespace-nowrap text-text-secondary">{label}</span>
      <input
        type="date"
        className={filterInputClass}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export function FilterDivider() {
  return <div className="mx-1 hidden h-6 w-px bg-brand-primary/20 sm:block" />;
}

export function FilterRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex w-full flex-wrap items-center gap-2 border-t border-white/45 pt-2 first:border-t-0 first:pt-0">
      {children}
    </div>
  );
}
