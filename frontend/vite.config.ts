/// <reference types="vitest/config" />
import preact from "@preact/preset-vite";
import { defineConfig } from "vite";

// The built UI is served by the Python back end and shipped inside the wheel.
// Everything is bundled locally, nothing is loaded from a CDN (UI-070).
export default defineConfig({
  plugins: [preact()],
  base: "./",
  build: {
    outDir: "../src/brewberrypi/web/static",
    emptyOutDir: true,
  },
  test: {
    environment: "node",
  },
});
