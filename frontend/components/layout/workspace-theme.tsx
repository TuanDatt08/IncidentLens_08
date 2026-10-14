"use client";
import { createContext, useContext, useEffect, useState } from "react";
type Mode = "light" | "dark";
const storageKey = "incidentlens:theme";
const ThemeContext = createContext<{ mode: Mode; toggle: () => void }>({ mode: "dark", toggle: () => {} });
export const themeInitScript = `try{var t=localStorage.getItem('${storageKey}');document.documentElement.dataset.theme=t==='light'||t==='dark'?t:'dark'}catch(e){document.documentElement.dataset.theme='dark'}`;
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<Mode>("dark");
  useEffect(() => {
    const sync = () => {
      let next: Mode = "dark";
      try { next = localStorage.getItem(storageKey) === "light" ? "light" : "dark"; } catch {}
      document.documentElement.dataset.theme = next;
      setMode(next);
    };
    sync();
    const onStorage = (event: StorageEvent) => { if (event.key === storageKey || event.key === null) sync(); };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  function toggle() {
    const next = mode === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    setMode(next);
    try { localStorage.setItem(storageKey, next); } catch {}
  }
  return <ThemeContext.Provider value={{ mode, toggle }}>{children}</ThemeContext.Provider>;
}
export function WorkspaceTheme() {
  const { mode, toggle } = useContext(ThemeContext);
  return <button type="button" className="theme-trigger" aria-label="Dark mode" aria-pressed={mode === "dark"} title={mode === "dark" ? "Switch to light mode" : "Switch to dark mode"} onClick={toggle}>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      {mode === "dark" ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></> : <path d="M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z" />}
    </svg><span className="theme-label">{mode === "dark" ? "Light" : "Dark"}</span>
  </button>;
}
