import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./services/**/*.{js,ts,jsx,tsx,mdx}",
    "./types/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vf: {
          primary: "#1464F4",
          navy: "#0D1528",
          secondary: "#ACCAED",
          text: "#3C3C3C",
          muted: "#6B7280",
          canvas: "#F8F9FA",
        },
      },
      boxShadow: {
        card: "0 12px 32px rgba(13, 21, 40, 0.06)",
        soft: "0 6px 18px rgba(13, 21, 40, 0.05)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;