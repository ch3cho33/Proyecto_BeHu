import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        elevated: "var(--bg-elevated)",
        surface: "var(--surface)",
        "surface-hover": "var(--surface-hover)",
        "surface-strong": "var(--surface-strong)",
        line: "var(--border)",
        "line-strong": "var(--border-strong)",
        ink: "var(--text)",
        muted: "var(--text-muted)",
        dim: "var(--text-dim)",
        primary: "var(--primary)",
        success: "var(--success)",
        danger: "var(--danger)",
        warning: "var(--warning)",
      },
      borderRadius: {
        behu: "8px",
        card: "12px",
        sheet: "16px",
      },
      maxWidth: {
        app: "1200px",
      },
    },
  },
  plugins: [],
};

export default config;
