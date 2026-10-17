/// <reference types="vitest/config" />
import preact from "@preact/preset-vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// The built UI is served by the Python back end and shipped inside the wheel.
// Everything is bundled locally, nothing is loaded from a CDN (UI-070).
export default defineConfig({
  plugins: [preact(), tailwindcss()],
  base: "./",
  // Dev server (`npm run dev`, `make dev`): Node resolves "localhost" to ::1 only, but VS Code's port
  // forwarding connects to 127.0.0.1. The fixed port matches forwardPorts in devcontainer.json.
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    // `make dev`: the REST API, the event stream and /healthz (version) go to the back end (`make run`, port 8080).
    proxy: { "/api": { target: "http://127.0.0.1:8080" }, "/healthz": { target: "http://127.0.0.1:8080" } },
  },
  build: {
    outDir: "../src/brewberrypi/web/static",
    emptyOutDir: true,
  },
  test: {
    environment: "node",
  },
});
