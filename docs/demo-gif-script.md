# README Demo GIF

How the walkthrough under the README intro (`docs/screenshots/demo.gif`) and the
hero image above it (`docs/screenshots/hero-phishing-detection.png`) are made.
For a live walkthrough of the extension, see the [Demo Script](demo-script.md).

## The walkthrough GIF

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

**How it is built.** The screenshots are full-resolution (2405×1355) grabs of
the real browser with the built extension, the backend, and the local demo
sites. A small script (kept with the recording kit, outside this repository)
crops them, adds the captions, and builds the 8-step crossfades (30 ms per
step). ffmpeg quantizes each distinct frame to its own 256-color palette without
dithering: UI screenshots have few colors, so text stays crisp. Pillow then
writes the GIF with exact per-frame durations.

Two ffmpeg-only approaches failed:
- Letting ffmpeg write the GIF made the fades uneven (40/80 ms), because its
  image demuxer rounds timestamps to 1/25 s.
- A constant frame rate with repeated hold frames came out about 6 times larger,
  because a new palette on every frame defeats its inter-frame diffing.

## The hero image

A frame of a 2026-09-29 Recordly screen recording of the same story: the popup
at Dangerous 95 with the in-page warning and the red toolbar badge. It is cropped
to the browser window (2485×1440) and scaled to 1600×927.

## Earlier approaches

- **Scripted GIF (June 2026).** Playwright drove Chromium with the built
  extension through the three `demo/pages/` fixtures, and a Pillow script
  composited the frames. That session also found a real production bug. The
  content script and the danger overlay shipped with an ES `import` inside
  files that run as classic scripts, so they failed in a real browser while
  every unit test and the build passed. See `CHANGELOG.md` and the two-pass
  build in `vite.config.ts`. `scripts/record-demo.mjs` still captures the README
  and store screenshots; the compositor was removed.
- **Screen recording as animated WebP (September 2026).** A Recordly
  recording of the story above, converted at 1280 px / 20 fps, then 30 fps,
  then 1600 px / 60 fps (up to ~19 MB). Every version still looked laggy. The
  camera zooms moved continuously, and the take held completely still for 2-3 s
  at a time, which in a silent loop looks like the player hung. The slideshow
  replaced it: it holds still on purpose, changes with short fades, and weighs
  less than half as much.
