import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-vf-primary text-white shadow-[0_7px_15px_rgba(20,100,244,0.18)] hover:bg-blue-700",
  secondary: "border border-slate-200 bg-white text-vf-navy hover:border-vf-primary hover:text-vf-primary",
  ghost: "text-slate-600 hover:bg-slate-100 hover:text-vf-navy",
  danger: "border border-red-200 bg-white text-red-600 hover:bg-red-50",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return <button className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-extrabold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`} {...props} />;
}