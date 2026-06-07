import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#e8edf3",
          100: "#c5d1e0",
          500: "#1e3a5f",
          600: "#192f4d",
          700: "#14243b",
          900: "#0a1520",
        },
        accent: {
          DEFAULT: "#f97316",
          hover: "#ea6c0a",
        },
      },
      fontFamily: {
        sans: [
          "Hiragino Kaku Gothic ProN",
          "Hiragino Sans",
          "Meiryo",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
export default config;
