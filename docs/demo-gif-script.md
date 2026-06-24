# Demo GIF Recording Script

This is the shot list for the short, header-of-the-README demo GIF
(`docs/screenshots/demo.gif`, referenced from `README.md`). It is a condensed,
visual-first cut of the full [Demo Script](demo-script.md) — record that setup
first, then follow this sequence for the GIF itself.

## Output target

- **File:** `docs/screenshots/demo.gif`
- **Dimensions:** 960×600 (matches the existing screenshot aspect ratio; keep
  the popup and the page both legible at GitHub's rendered README width).
- **Duration:** ~15-20 seconds total, looping.
- **Frame rate:** 8-12 fps is enough for UI interactions and keeps file size
  reasonable for a README header (aim under ~5 MB).
- **No audio**, no cursor-trail effects, no webcam overlay — just the browser.

## Recommended tools

- **Windows:** [ScreenToGif](https://www.screentogif.com/) (free, OSS, records
  directly to GIF with a built-in editor for trimming/cropping frames) — this
  matches the project's Windows dev environment.
- **macOS:** QuickTime screen recording → `gifski` (or `ffmpeg`) to convert to GIF.
- **Cross-platform CLI alternative:** record with `ffmpeg -f gdigrab` (Windows)
  or `ffmpeg -f avfoundation` (macOS) to MP4, then convert with `gifski` for a
  much smaller, higher-quality GIF than a direct screen-to-GIF capture.

## Setup (do this before hitting record)

Follow [Demo Script § Setup](demo-script.md#setup) steps 1-4: start the backend
with the demo threat source enabled, serve the local demo pages, build and load
the extension, and confirm the Options page settings. Arrange the window so the
browser tab and the extension popup are both visible without overlapping
other windows, at the target 960×600 capture region.

## Shot sequence

1. **(0:00-0:03) Safe page.** Open `http://localhost:8080/pages/safe.html`,
   click the PhishLens toolbar icon. Hold on the popup long enough to read
   "Safe" and the green risk score.
2. **(0:03-0:08) Suspicious page.** Navigate to
   `http://localhost:8080/pages/suspicious.html`, click the toolbar icon again.
   Hold on the popup showing the "Suspicious" result with at least one signal
   group expanded (e.g. "Page structure" or "URL") so a real reason string is
   visible.
3. **(0:08-0:15) Dangerous page + overlay.** Navigate to
   `http://localhost:8080/pages/phishlens-demo-dangerous-login-secure-update.html`.
   Let the dismissible danger overlay appear on the page itself (not just the
   popup) — this is the most visually compelling beat, showing the actionable
   "do not enter your password" instruction. Hold for ~3 seconds, then click
   "Continue" to dismiss it.
4. **(0:15-0:18) Close on the badge.** Briefly show the toolbar badge color
   changing between the safe/suspicious/dangerous pages (this is easy to miss
   live — a 1-2 second hold on the toolbar icon between page switches sells it).

Trim dead time between steps in the editor so the loop feels continuous; a
GIF with no pauses longer than ~1 second (outside the deliberate holds above)
reads as more polished.

## After recording

1. Save the file as `docs/screenshots/demo.gif`.
2. Re-run `extension/scripts/take-screenshots.mjs` is unrelated (PNG only) —
   no script needs updating for the GIF; the README reference is already wired.
3. Open `README.md` and confirm the image renders where the placeholder is
   (right under the intro paragraph, above "## Quick Start").

## Automated capture (alternative to manual screen recording)

The current `docs/screenshots/demo.gif` was produced this way instead of a
real screen recording, using Playwright (already a devDependency) to drive a
real Chromium instance with the built extension loaded, plus Pillow to
composite the captured frames into a GIF:

```bash
cd extension
npm run build
node scripts/record-demo.mjs        # captures PNG frames to a temp dir (path printed at the end)
python scripts/compose_demo_gif.py  # requires Pillow: pip install Pillow
```

Prerequisites: backend running with `PHISHLENS_ENABLE_DEMO_THREAT_SOURCE=true`
and `python demo/serve_demo.py` running, per [Demo Script § Setup](demo-script.md#setup).

`record-demo.mjs` documents inline why it needs a patched, temporary copy of
the extension (added `tabs` permission, `web_accessible_resources` for
`popup.html`, an extra host permission for the demo origin) — none of that
ships; it only exists to make Playwright's simulated "click the toolbar icon"
(opening `popup.html` as a real tab, since there is no real toolbar to click)
resolve to the actual page tab instead of the popup's own tab.

**This recording session is also how a real production bug was found**: the
content script and the danger overlay shipped with an ES `import` statement
(`import browser from "webextension-polyfill"`, added when Firefox support
was wired up) inside files that execute as classic, non-module scripts —
`chrome.tabs.sendMessage` to the content script failed with "Could not
establish connection" in a real browser, even though every unit test and
`tsc`/build passed, because Vitest mocks modules and Vite's build step
doesn't statically check module-format compatibility at runtime. Fixed by
splitting the build into two passes (see `vite.config.ts` and
`scripts/build.mjs`): one ES-module pass for popup/options/service-worker,
one IIFE pass (no module loader, dependencies inlined) for the content
script and the overlay. See `CHANGELOG.md` for details.
