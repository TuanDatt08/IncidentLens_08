import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<ButtonVariant, string> = {
  primary: "workspace-action bg-vf-primary text-white",
  secondary: "border border-[var(--workspace-border)] bg-[var(--workspace-surface)] text-vf-navy hover:border-vf-primary hover:text-vf-primary",
  ghost: "text-[var(--workspace-muted)] hover:bg-[var(--workspace-primary-soft)] hover:text-vf-navy",
  danger: "border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
};

export function Button({ variant = "primary", className = "", type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return <button type={type} className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`} {...props} />;
}
