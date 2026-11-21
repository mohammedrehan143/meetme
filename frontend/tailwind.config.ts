import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#090909",
          secondary: "#111111",
          card: "#191919",
          elevated: "#202020",
        },
        accent: {
          orange: "#FF7900",
          "orange-hover": "#E56D00",
          "orange-subtle": "rgba(255, 121, 0, 0.12)",
          neon: "#B6FF00",
          "neon-subtle": "rgba(182, 255, 0, 0.12)",
        },
        text: {
          primary: "#FFFFFF",
          secondary: "#A0A0A0",
          muted: "#666666",
        },
        border: {
          subtle: "#303030",
          strong: "#444444",
        },
      },
      borderRadius: {
        card: "6px",
        btn: "5px",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "SF Mono",
          "Fira Code",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
export default config;
