import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // India Twin (dark map) palette, kept for /twin
        dark: {
          50: "#f8fafc",
          100: "#1e1e2e",
          200: "#181825",
          300: "#11111b",
          400: "#0a0a14",
          500: "#05050a",
        },
        // MetroPulse identity: paper and ink, signal vermilion for demand, indigo for supply
        paper: { DEFAULT: "#F4EFE6", deep: "#EAE2D3", edge: "#D8CDB8" },
        ink: { DEFAULT: "#16130F", soft: "#4A443B", faint: "#8A8172" },
        signal: { DEFAULT: "#D9480F", soft: "#F2B391", deep: "#9C3008" },
        supply: { DEFAULT: "#1E3A8A", soft: "#AFC0E8", deep: "#14275C" },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
