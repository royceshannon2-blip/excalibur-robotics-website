#!/usr/bin/env python3
"""Generate the site's icons from the Excalibur logo.

The tab icon and the touch icon both come from `excaliburlogo.png`, so
they can never drift from the mark the team actually uses.

Run from the repo root:

    python3 tools/make-favicon.py
"""

from __future__ import annotations

from PIL import Image

SOURCE = "excaliburlogo.png"
PLATE = (11, 6, 22)       # #0B0616 — the site's panel ground
PAD = 0.06                # breathing room around the mark, as a ratio


def load_mark() -> Image.Image:
    """The logo, trimmed to its ink and squared off with a little padding."""
    im = Image.open(SOURCE).convert("RGBA")
    im = im.crop(im.split()[3].getbbox())
    side = round(max(im.size) * (1 + PAD * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return canvas


def icon(mark: Image.Image, size: int, *, opaque: bool = False) -> Image.Image:
    out = mark.resize((size, size), Image.LANCZOS)
    if not opaque:
        return out
    # iOS ignores transparency and would paint the corners black.
    plate = Image.new("RGBA", (size, size), PLATE + (255,))
    plate.alpha_composite(out)
    return plate


def main() -> int:
    mark = load_mark()

    icon(mark, 180, opaque=True).save("apple-touch-icon.png")
    icon(mark, 192).save("favicon-192.png")

    sizes = [16, 32, 48]
    icon(mark, max(sizes)).save(
        "favicon.ico", sizes=[(s, s) for s in sizes]
    )

    print("wrote favicon.ico (16/32/48), favicon-192.png, apple-touch-icon.png (180)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
