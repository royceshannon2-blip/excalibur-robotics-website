#!/usr/bin/env python3
"""Generate the site's icons from its own nav glyph.

The page never declared an icon, so every browser fired an implicit
/favicon.ico request and logged a 404 — the only console error the site
produced. These are drawn from the same four-point star as the nav
mark, so the tab icon and the header can never drift apart.

Run from the repo root:

    python3 tools/make-favicon.py
"""

from __future__ import annotations

from PIL import Image, ImageDraw

# the nav glyph's path, in its own 24x24 space:
#   M12 2.5 L13.4 8.2 L20 9.6 L13.4 11 L12 21.5 L10.6 11 L4 9.6 L10.6 8.2 Z
STAR = [
    (12, 2.5), (13.4, 8.2), (20, 9.6), (13.4, 11),
    (12, 21.5), (10.6, 11), (4, 9.6), (10.6, 8.2),
]
UNITS = 24
PLATE = (11, 6, 22)      # #0B0616 — the site's panel ground
GOLD = (212, 175, 55)    # #D4AF37 — --accent
RADIUS_UNITS = 4.5
SS = 8                   # supersample factor for smooth edges


def draw_icon(size: int, radius_units: float = RADIUS_UNITS) -> Image.Image:
    big = size * SS
    k = big / UNITS
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = radius_units * k
    if r > 0:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=r, fill=PLATE + (255,))
    else:
        d.rectangle([0, 0, big - 1, big - 1], fill=PLATE + (255,))
    d.polygon([(x * k, y * k) for x, y in STAR], fill=GOLD + (255,))
    return im.resize((size, size), Image.LANCZOS)


def main() -> int:
    # A rounded plate for the tab; a full square for iOS, which applies
    # its own mask and would otherwise show plate-less corners.
    draw_icon(180, radius_units=0).save("apple-touch-icon.png")

    ico = [draw_icon(s) for s in (16, 32, 48)]
    ico[0].save("favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {UNITS} {UNITS}" role="img" aria-label="Excalibur">
  <rect width="{UNITS}" height="{UNITS}" rx="{RADIUS_UNITS}" fill="#0B0616"/>
  <path d="M12 2.5 L13.4 8.2 L20 9.6 L13.4 11 L12 21.5 L10.6 11 L4 9.6 L10.6 8.2 Z" fill="#D4AF37"/>
</svg>
"""
    with open("favicon.svg", "w", encoding="utf-8") as fh:
        fh.write(svg)

    print("wrote favicon.svg, favicon.ico (16/32/48), apple-touch-icon.png (180)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())