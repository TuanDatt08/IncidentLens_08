import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth/auth-provider";
import { DeferredFont } from "@/components/layout/deferred-font";
import "./globals.css";
import "./interaction-theme.css";
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
        <DeferredFont />
        <ThemeProvider><AuthProvider><RouteTransition>{children}</RouteTransition></AuthProvider></ThemeProvider>
      </body>
    </html>
  );
}
