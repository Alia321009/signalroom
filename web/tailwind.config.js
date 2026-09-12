/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // A trading-signal product's own identity, deliberately distinct
      // from the trading-bot project's deep-neutral instrument-panel
      // look: gold (the product's own instrument, XAU/USD) as the accent
      // against a warm charcoal ground, not another cool-grey dashboard.
      colors: {
        ground: "#171310",
        panel: "#1D1712",
        line: "#2B241C",
        primary: "#F3EDE3",
        secondary: "#9C8F7A",
        gold: "#D4A24C",
        profit: "#4FAE7C",
        loss: "#D2604A",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
}
