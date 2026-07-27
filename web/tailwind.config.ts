import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        moss: "#2f6f4e",
        berry: "#b83a4b",
        apricot: "#f59e42",
        sea: "#1d7c8c",
        panel: "#f7faf7",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(31, 41, 51, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
