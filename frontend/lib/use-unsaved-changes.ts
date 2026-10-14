"use client";

import { useEffect } from "react";

/** Guard reload/close and same-tab links. Back/Forward relies on draft recovery. */
export function useUnsavedChanges(dirty: boolean, working = false): void {
  useEffect(() => {
    if (!dirty && !working) return;
    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(anchor instanceof HTMLAnchorElement) || anchor.hasAttribute("download") || (anchor.target && anchor.target.toLowerCase() !== "_self")) return;
      const target = new URL(anchor.href, window.location.href);
      if (target.protocol !== "http:" && target.protocol !== "https:") return;
      if (target.origin === window.location.origin && target.pathname === window.location.pathname && target.search === window.location.search) return;
      const leave = !working && window.confirm("Leave with unsaved changes? Your draft can be restored in this tab for 24 hours if browser storage is available.");
      if (!leave) {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        if (working) window.alert("Please wait for the current request to finish before leaving this report.");
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, [dirty, working]);
}
