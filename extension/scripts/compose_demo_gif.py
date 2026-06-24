"""Composes the PNG frames captured by record-demo.mjs into docs/screenshots/demo.gif.

Requires Pillow (not a project dependency — install separately: pip install Pillow).

Usage:
    python scripts/compose_demo_gif.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

FRAMES_DIR = Path(tempfile.gettempdir()) / "phishlens-record-demo" / "frames"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "docs" / "screenshots" / "demo.gif"
CANVAS_SIZE = (960, 600)


def load(name: str) -> Image.Image:
    return Image.open(FRAMES_DIR / name).convert("RGB")


def fit_background(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / img.width, target_h / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)))
    left = (resized.width - target_w) // 2
    return resized.crop((left, 0, left + target_w, target_h))


def with_shadow(img: Image.Image, shadow_offset: int = 6, shadow_blur_px: int = 10) -> Image.Image:
    padded = Image.new(
        "RGBA",
        (img.width + shadow_blur_px * 2, img.height + shadow_blur_px * 2 + shadow_offset),
        (0, 0, 0, 0),
    )
    shadow = Image.new("RGBA", padded.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.rectangle(
        [
            shadow_blur_px,
            shadow_blur_px + shadow_offset,
            shadow_blur_px + img.width,
            shadow_blur_px + shadow_offset + img.height,
        ],
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur_px / 2))
    padded.alpha_composite(shadow)
    padded.paste(img.convert("RGBA"), (shadow_blur_px, shadow_blur_px), img.convert("RGBA"))
    return padded


def popup_composite(page_name: str, popup_name: str) -> Image.Image:
    canvas = fit_background(load(page_name), CANVAS_SIZE).convert("RGBA")

    popup = load(popup_name)
    popup_target_h = 560
    scale = popup_target_h / popup.height
    popup = popup.resize((round(popup.width * scale), popup_target_h))
    popup_with_shadow = with_shadow(popup)

    x = CANVAS_SIZE[0] - popup_with_shadow.width - 14
    canvas.alpha_composite(popup_with_shadow, (x, 10))
    return canvas.convert("RGB")


def full_frame(name: str) -> Image.Image:
    return fit_background(load(name), CANVAS_SIZE)


def popup_detail_frame(popup_name: str) -> Image.Image:
    popup = load(popup_name)
    scale = CANVAS_SIZE[1] / popup.height
    resized = popup.resize((round(popup.width * scale), CANVAS_SIZE[1]))
    canvas = Image.new("RGB", CANVAS_SIZE, (245, 246, 248))
    x = (CANVAS_SIZE[0] - resized.width) // 2
    canvas.paste(resized, (x, 0))
    return canvas


def main() -> None:
    if not FRAMES_DIR.exists():
        raise SystemExit(f"{FRAMES_DIR} not found. Run `node scripts/record-demo.mjs` first.")

    frames = [
        popup_composite("01-safe-page.png", "01-safe-popup.png"),
        popup_composite("02-suspicious-page.png", "02-suspicious-popup.png"),
        full_frame("03-dangerous-overlay.png"),
        full_frame("03-dangerous-overlay.png"),
        popup_detail_frame("03-dangerous-popup.png"),
    ]
    # Hold each shot for a few seconds; the overlay frame is duplicated so it
    # gets a longer effective hold (Pillow merges identical consecutive
    # frames and sums their durations).
    durations_ms = [3000, 3000, 1800, 1800, 3200]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUTPUT_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations_ms,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
