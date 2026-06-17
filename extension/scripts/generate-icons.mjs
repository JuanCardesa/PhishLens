/**
 * Generates PNG icon assets from the master SVG for Chrome extension and
 * Chrome Web Store requirements. Run once when the icon design changes.
 *
 * Usage: node scripts/generate-icons.mjs
 */

import { createRequire } from "node:module";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("sharp");

const __dir = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dir, "..");
const svgPath = resolve(root, "public", "icons", "phishlens.svg");
const outDir = resolve(root, "public", "icons");

const SIZES = [16, 48, 128, 512];

if (!existsSync(svgPath)) {
  console.error(`SVG source not found: ${svgPath}`);
  process.exit(1);
}

mkdirSync(outDir, { recursive: true });

const svgBuffer = readFileSync(svgPath);

await Promise.all(
  SIZES.map(async (size) => {
    const outPath = resolve(outDir, `phishlens-${size}.png`);
    await sharp(svgBuffer).resize(size, size).png().toFile(outPath);
    console.log(`  ✓ ${size}x${size} → ${outPath}`);
  }),
);

console.log("Icons generated.");
