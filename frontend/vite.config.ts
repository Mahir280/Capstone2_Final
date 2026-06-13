import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // The analytics route lazily loads ECharts into its own on-demand chunk.
    // That chunk is inherently large but is never part of the initial app load,
    // so we raise the warning threshold above its size rather than over-split it.
    chunkSizeWarningLimit: 700,
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  preview: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});
