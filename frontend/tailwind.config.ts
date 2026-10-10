import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#F5F3EC",
        ink: "#242B25",
        line: "#DADCD2",
        savings: {
          DEFAULT: "#32724B",
          dim: "#EAF1E4",
        },
      },
      fontFamily: {
        sans: ["var(--font-bb-sans)", "Arial", "sans-serif"],
        display: ["var(--font-bb-display)", "Georgia", "serif"],
        mono: ["var(--font-bb-mono)", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
