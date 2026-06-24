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

// Two passes, controlled by BUILD_TARGET (see scripts/build.mjs), because they
// need different Rollup output formats and Vite only supports one format per
// `vite build` invocation:
//
// - "module" (default): popup, options, and the background service worker.
//   manifest.json declares `"type": "module"` for the service worker, and the
//   popup/options HTML entries load their scripts as `<script type="module">`,
//   so ES `import`/code-splitting is correct here.
// - "classic": the content script and the warning overlay (injected via
//   `chrome.scripting.executeScript`). Both run as classic, non-module
//   scripts — manifest content_scripts entries cannot declare
//   `"type": "module"`, and executeScript-injected files run the same way.
//   An ES `import` statement in either throws "Cannot use import statement
//   outside a module" at runtime in a real browser (this shipped broken once;
//   see CHANGELOG). IIFE output has no module loader, so Rollup inlines their
//   shared dependencies (e.g. webextension-polyfill) directly into each file
//   instead of extracting a shared chunk.
// IIFE output (required for classic, non-module scripts) only supports a
// single entry per Rollup build — "multiple inputs are not supported when
// output.codeSplitting is false" — so each classic target gets its own pass.
const CLASSIC_TARGETS = {
  content: { domAnalyzer: resolve(__dirname, "src", "content", "dom-analyzer.ts") },
  overlay: { overlay: resolve(__dirname, "src", "warning", "overlay.ts") },
};
const buildTarget = (process.env.BUILD_TARGET ?? "module") as "module" | keyof typeof CLASSIC_TARGETS;

const moduleInput = {
  popup: resolve(__dirname, "src", "popup", "popup.html"),
  options: resolve(__dirname, "src", "options", "options.html"),
  serviceWorker: resolve(__dirname, "src", "background", "service-worker.ts"),
};

function entryFileName(chunkName: string): string {
  if (chunkName === "serviceWorker") return "background/service-worker.js";
  if (chunkName === "domAnalyzer") return "content/dom-analyzer.js";
  if (chunkName === "overlay") return "warning/overlay.js";
  return "assets/[name].js";
}

export default defineConfig({
  plugins: [react(), ...(buildTarget === "module" ? [copyExtensionAssets()] : [])],
  build: {
    outDir: "dist",
    emptyOutDir: buildTarget === "module",
    rollupOptions:
      buildTarget === "module"
        ? {
            input: moduleInput,
            output: {
              entryFileNames: (chunkInfo) => entryFileName(chunkInfo.name),
              chunkFileNames: "assets/[name].js",
              assetFileNames: "assets/[name][extname]",
            },
          }
        : {
            input: CLASSIC_TARGETS[buildTarget],
            output: {
              format: "iife",
              entryFileNames: (chunkInfo) => entryFileName(chunkInfo.name),
              assetFileNames: "assets/[name][extname]",
            },
          },
  },
});
