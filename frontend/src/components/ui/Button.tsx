import { ButtonHTMLAttributes } from "react";

const variants: Record<string, string> = {
  primary: "bg-brand-primary hover:bg-brand-hover text-white",
  success: "bg-[#43a047] hover:bg-[#66bb6a] text-white",
  danger: "bg-[#e53935] hover:bg-[#ef5350] text-white",
  info: "bg-[#1e88e5] hover:bg-[#42a5f5] text-white",
  warning: "bg-[#ff9800] hover:bg-[#ffb74d] text-white",
  outline:
    "bg-transparent border border-border text-text-primary hover:border-brand-primary hover:text-brand-primary",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: Props) {
  return (
    <button
      className={`rounded-md px-4 py-2 text-sm font-bold transition disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
