"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";

// Animate the container without remounting editors or resetting unsaved drafts.
export function RouteTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = container.current;
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (motionPreference.matches || !element?.animate) return;

    // A global transform would change the containing block of fixed dialogs
    // and sticky navigation. Fade only, keeping content readable throughout.
    const animation = element.animate(
      [{ opacity: 0.72 }, { opacity: 1 }],
      { duration: 220, easing: "cubic-bezier(.22,1,.36,1)" },
    );
    const cancelOnReducedMotion = () => {
      if (motionPreference.matches) animation.cancel();
    };
    motionPreference.addEventListener("change", cancelOnReducedMotion);
    return () => {
      animation.cancel();
      motionPreference.removeEventListener("change", cancelOnReducedMotion);
    };
  }, [pathname]);
  return <div ref={container} className="workspace-route">{children}</div>;
}
