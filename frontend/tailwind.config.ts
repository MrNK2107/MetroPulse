import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@tremor/react/dist/esm/**/*.mjs",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          50: "#f8fafc",
          100: "#1e1e2e",
          200: "#181825",
          300: "#11111b",
          400: "#0a0a14",
          500: "#05050a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
