import { spawnSync } from "node:child_process";

// Two `vite build` passes (see vite.config.ts for why): the default pass
// builds the ES-module entries (popup, options, service worker) and empties
// dist/ first; the "classic" pass builds the content script and overlay as
// IIFE bundles into the same dist/ without re-emptying it.
function runViteBuild(buildTarget) {
  const result = spawnSync("npx", ["vite", "build"], {
    stdio: "inherit",
    shell: true,
    env: { ...process.env, BUILD_TARGET: buildTarget },
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

runViteBuild("module");
runViteBuild("content");
runViteBuild("overlay");
