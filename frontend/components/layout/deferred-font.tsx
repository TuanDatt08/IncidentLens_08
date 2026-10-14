"use client";

import { useEffect } from "react";

const FONT_STYLESHEET = "https://fonts.googleapis.com/css2?family=Mulish:wght@400..900&display=swap";

export function DeferredFont() {
  useEffect(() => {
    // A dynamically inserted stylesheet leaves the initial render on the system fallback.
    // Keep one shared link across Strict Mode effects and route transitions.
    if (document.getElementById("incidentlens-font-stylesheet")) return;
    const link = document.createElement("link");
    link.id = "incidentlens-font-stylesheet";
    link.rel = "stylesheet";
    link.href = FONT_STYLESHEET;
    document.head.appendChild(link);
  }, []);
  return null;
}
