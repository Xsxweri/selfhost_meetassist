import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const proxy = {
  "/api": { target: "http://localhost:8000", changeOrigin: true },
  "/ws": { target: "ws://localhost:8000", ws: true, rewrite: (p: string) => p.replace(/^\/ws/, "/api/v1") },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
});