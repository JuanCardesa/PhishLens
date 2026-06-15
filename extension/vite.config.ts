import react from "@vitejs/plugin-react";
import { cpSync, copyFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "vite";

function copyExtensionAssets() {
  return {
    name: "copy-extension-assets",
    closeBundle() {
      const dist = resolve(__dirname, "dist");
      mkdirSync(dist, { recursive: true });
      copyFileSync(resolve(__dirname, "manifest.json"), resolve(dist, "manifest.json"));

      const iconSource = resolve(__dirname, "public", "icons");
      if (existsSync(iconSource)) {
        cpSync(iconSource, resolve(dist, "icons"), { recursive: true });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), copyExtensionAssets()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        popup: resolve(__dirname, "src", "popup", "popup.html"),
        serviceWorker: resolve(__dirname, "src", "background", "service-worker.ts"),
        domAnalyzer: resolve(__dirname, "src", "content", "dom-analyzer.ts"),
        overlay: resolve(__dirname, "src", "warning", "overlay.ts"),
      },
      output: {
        entryFileNames(chunkInfo) {
          if (chunkInfo.name === "serviceWorker") {
            return "background/service-worker.js";
          }
          if (chunkInfo.name === "domAnalyzer") {
            return "content/dom-analyzer.js";
          }
          if (chunkInfo.name === "overlay") {
            return "warning/overlay.js";
          }
          return "assets/[name].js";
        },
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
