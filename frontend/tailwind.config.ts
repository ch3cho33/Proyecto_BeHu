import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14221b",
        moss: "#1f7a4d",
        sand: "#f3efe6",
        clay: "#c46b3a",
      },
    },
  },
  plugins: [],
};

export default config;
