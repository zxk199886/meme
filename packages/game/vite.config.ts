import { defineConfig } from "vite";

// Phase 2：纯 Phaser + TS 的 Vite 应用（离线、无链）。
// base 用相对路径，方便后续部署到静态托管（Vercel/Cloudflare Pages）。
export default defineConfig({
  base: "./",
  server: {
    host: true,
    port: 5173,
  },
  build: {
    target: "es2022",
    outDir: "dist",
    sourcemap: true,
  },
});
