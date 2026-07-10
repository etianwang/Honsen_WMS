const styles: Record<string, string> = {
  正常: "bg-[#e8f5e9] text-[#2e7d32]",
  预警: "bg-[#fff3e0] text-[#e65100]",
  缺货: "bg-[#ffebee] text-[#c62828]",
};

export function Badge({ status }: { status?: string }) {
  const label = status ?? "正常";
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${styles[label] ?? styles["正常"]}`}
    >
      {label}
    </span>
  );
}
