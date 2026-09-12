/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Production: FastAPI serves this app's built static output itself
// (app/main.py's StaticFiles mount), so the API is same-origin there and
// no proxy/CORS is needed. In dev, proxy every backend path prefix so the
// browser sees everything as same-origin too.
const API_PREFIXES = ["/auth", "/members", "/calls", "/bot-settings", "/executor", "/ws"];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      API_PREFIXES.map((prefix) => [
        prefix,
        { target: "http://localhost:8000", changeOrigin: true, ws: prefix === "/ws" },
      ]),
    ),
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary"],
    },
  },
});
