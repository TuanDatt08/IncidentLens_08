import type { Metadata } from "next";
import { NightSky } from "@/components/layout/night-sky";

import { AuthProvider } from "@/components/auth/auth-provider";
import { DeferredFont } from "@/components/layout/deferred-font";
import "./globals.css";
import "./interaction-theme.css";
import "./night-sky.css";
import "./daylight-clouds.css";
import { DaylightClouds } from "@/components/layout/daylight-clouds";
import { ThemeProvider, themeInitScript } from "@/components/layout/workspace-theme";
import { RouteTransition } from "@/components/layout/route-transition";

export const metadata: Metadata = {
  title: "IncidentLens | ADAS Incident Analysis",
  description: "AI-assisted ADAS incident analysis for RAV-18.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeInitScript }} /></head>
      <body>
        <DeferredFont /><NightSky /><div className="global-day-sky" aria-hidden="true"><DaylightClouds thin /></div>
        <div className="site-content"><ThemeProvider><AuthProvider><RouteTransition>{children}</RouteTransition></AuthProvider></ThemeProvider></div>
      </body>
    </html>
  );
}
