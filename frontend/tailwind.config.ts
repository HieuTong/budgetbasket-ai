import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF7F0",
        ink: "#1F2A24",
        savings: "#2F6F4F",
        "savings-dim": "#E4E9E1",
        rising: "#C97A2B",
        over: "#B5482E",
        line: "#D8D2C4",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
