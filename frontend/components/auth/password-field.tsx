"use client";

import { useId, useState, type InputHTMLAttributes } from "react";

export function PasswordField({ label, hint, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: string; hint?: string }) {
  const generatedId = useId();
  const id = props.id ?? generatedId;
  const [visible, setVisible] = useState(false);
  return <div>
    <label htmlFor={id} className="field-label">{label}</label>
    <div className="relative">
      <input {...props} id={id} type={visible ? "text" : "password"} aria-describedby={hint ? `${id}-hint` : undefined} className="auth-input pr-12" />
      <button type="button" aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`} aria-pressed={visible} disabled={props.disabled} onClick={() => setVisible(value => !value)} className="absolute inset-y-1 right-1 flex w-10 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-vf-navy disabled:opacity-50">
        <svg aria-hidden className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" strokeLinejoin="round" /><circle cx="12" cy="12" r="3" />{visible && <path d="m3 3 18 18" strokeLinecap="round" />}</svg>
      </button>
    </div>
    {hint && <p id={`${id}-hint`} className="mt-2 text-xs leading-5 text-slate-400">{hint}</p>}
  </div>;
}
