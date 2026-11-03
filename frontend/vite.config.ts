import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

// In dev, /api is proxied to the API; in Docker, nginx does it.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
