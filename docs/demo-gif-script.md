# Demo GIF Recording Script

> **Status:** `README.md` shows `docs/screenshots/demo.gif`, a slideshow built
> from still screenshots (see [Current README demo](#current-readme-demo)). The
> shot list and the Playwright pipeline further down describe an earlier scripted
> GIF and are kept for reference.

This is the shot list for the short, header-of-the-README demo GIF
(`docs/screenshots/demo.gif`). It is a condensed,
visual-first cut of the full [Demo Script](demo-script.md) — record that setup
first, then follow this sequence for the GIF itself.

## Current README demo

`docs/screenshots/demo.gif` is a ~16-second slideshow of six real screenshots of
the extension, each held for 2-2.6 s, with a 0.24 s crossfade between them:

1. A fake "PayPal Security" email in a local webmail inbox.
2. A closer crop showing that hovering its button reveals the real link,
   `paypal-verify-account.net`, highlighted in the status bar. The pointer is
   drawn in, because screen grabs do not capture it.
3. The popup rating the cloned login Dangerous 95, with the in-page warning
   behind it.
4. The signal breakdown (URL 32/35, page structure 30/30).
5. The rest of the breakdown: threat intel, TLS, domain age, and ML (0).
6. The in-page warning on its own.

Each slide has a one-line caption in a strip below the screenshot. Slides 3-6
share one framing, so moving between them only changes the popup's content.
The GIF is 1280×796, loops forever, and is ~7.6 MB. Both sites are demo pages
served locally; `paypal-verify-account.net` is not a registered domain.

**Why stills instead of a screen recording.** The walkthrough used to be an
animated WebP cut from a Recordly screen recording: 1280 px at 20 fps, then 30
fps, then 1600 px at 60 fps (up to ~19 MB). Every version still looked laggy.
The recording's camera zooms moved continuously, and frame analysis showed that
the take also held completely still for 2-3 s at a time, which in a silent loop
looks like the player hung. A slideshow holds still on purpose and changes with
short fades, so nothing moves continuously and nothing can stutter. It is also
smaller, and every slide is a sharp full-resolution capture.

**How it is built.** The screenshots are full-resolution (2405×1355) grabs of
the real browser with the built extension, the backend, and the local demo
sites, taken by the recording kit's dry run. A small script crops them, adds the
captions, and builds the 8-step crossfades (30 ms per step). ffmpeg quantizes
each distinct frame to its own 256-color palette without dithering: UI
screenshots have few colors, so text stays crisp. Pillow then writes the GIF
with exact per-frame durations.

Two things did not work:
- Letting ffmpeg write the GIF made the fades uneven (40/80 ms), because its
  image demuxer rounds timestamps to 1/25 s.
- A constant frame rate with repeated hold frames came out about 6 times larger,
  because a new palette on every frame defeats its inter-frame diffing.

The README hero is a separate still: a frame of the 2026-09-29 Recordly
recording, cropped to the browser window (2485×1440) and scaled to 1600×927.

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
   no script needs updating for the GIF.
3. To use it in `README.md`, point the walkthrough image (right under the
   intro paragraph, above "## Quick Start") at `docs/screenshots/demo.gif`.

## Automated capture (alternative to manual screen recording)

An earlier README GIF at the same path was produced this way instead of a real screen recording, using Playwright (already a devDependency) to drive a
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
