import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api is proxied to the API; in Docker, nginx does it.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
