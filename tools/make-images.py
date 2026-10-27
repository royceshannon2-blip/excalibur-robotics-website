#!/usr/bin/env python3
"""Responsive image derivatives for the Biobuzz26-27 site.

The site shipped full-resolution camera files: the worst offenders were a
5712x4284 frame (3.0 MB) shown in a ~370px card and a 4284x5712 frame
(5.3 MB) shown in a ~520px card. Between them, ~11 MB of images were
downloaded eagerly by every visitor, including phones on cellular.

This script writes right-sized AVIF/WebP/JPEG (and PNG/WebP for artwork
with alpha) into img/, so the markup can offer a useful ladder instead of
one enormous file. Originals are left untouched in the repo — they are
the source of truth and are not served at small widths.

Two things it deliberately gets right:

  * ORIENTATION. Phone JPEGs carry an EXIF orientation tag. Baking the
    rotation in (exif_transpose) before stripping metadata is what keeps
    a portrait photo from rendering on its side once the tag is gone.
  * COLOUR. iPhone frames are tagged Display P3. Re-encoding without
    converting the profile to sRGB shifts every colour, so the embedded
    profile is converted through ImageCms rather than discarded.

Run from the repo root:

    python3 tools/make-images.py
"""

from __future__ import annotations

import io
import os
import sys

from PIL import Image, ImageCms, ImageOps

OUT_DIR = "img"

# (source, widths, kind). `photo` -> avif/webp/jpg, `alpha` -> webp/png
# (JPEG cannot carry the alpha the logo artwork relies on).
SOURCES = [
    ("IMG_3115.jpg", [480, 960, 1280, 1600], "photo"),
    ("92415ebd-3534-4c94-9191-896d8cabd3a9.jpg", [480, 960, 1280, 1600], "photo"),
    ("20251118_123144.jpg", [480, 960, 1280, 1600], "photo"),
    ("IMG_8479.jpg", [480, 960, 1280, 1600], "photo"),
    ("foundation.png", [480, 960], "alpha"),
    # Phoenix: the 2025-26 DECODE robot render. It is a cut-out (74% of the
    # frame is transparent), so it ships as webp/png and is placed with
    # object-fit: contain rather than cover -- cropping it would cut the
    # robot, not the empty air around it.
    ("Phoenix.png", [480, 960, 1280, 1600], "alpha"),
    # Member portraits. Cards render at ~300px (3D capture at 900px), so a
    # 480/960 ladder is enough; the smaller scans only earn the 480 tier.
    # Alumni shots (Abhi, Ansh, Arpan, Matthew, Vishwanth) and Yichen's
    # 217px WebP are already small originals and ship from the repo root
    # as-is — a ladder would only upscale them.
    ("Trey.jpg", [480, 960], "photo"),
    ("Sanjey.jpg", [480, 960], "photo"),
    ("Lamont.jpg", [480, 960], "photo"),
    ("Royce.jpg", [480, 960], "photo"),
    ("Kahlan.png", [480, 960], "photo"),
    ("Lucas.jpg", [480, 960], "photo"),
    ("Sanjay.png", [480, 960], "photo"),
    ("SJ.jpg", [480, 960], "photo"),
    ("Eshan.jpg", [480, 960], "photo"),
    ("Peyton.jpg", [480, 960], "photo"),
    ("Keerthika.png", [480], "photo"),
    ("Audrey.png", [480], "photo"),
    ("Reese.png", [480, 960], "photo"),
    ("Zach.jpg", [480, 960], "photo"),
]

AVIF_QUALITY = 62
WEBP_QUALITY = 84
JPEG_QUALITY = 87


def to_srgb(im: Image.Image) -> Image.Image:
    """Convert an embedded ICC profile to sRGB, or pass through untagged."""
    icc = im.info.get("icc_profile")
    if not icc:
        return im
    try:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        dst = ImageCms.createProfile("sRGB")
        mode = "RGBA" if "A" in im.getbands() else "RGB"
        return ImageCms.profileToProfile(im, src, dst, outputMode=mode)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"    ! ICC conversion failed ({exc}); using raw pixels", file=sys.stderr)
        return im


def encode(im: Image.Image, path: str, kind: str, fmt: str) -> int:
    if fmt == "avif":
        im.save(path, "AVIF", quality=AVIF_QUALITY)
    elif fmt == "webp":
        im.save(path, "WEBP", quality=WEBP_QUALITY, method=5)
    elif fmt == "jpg":
        im.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    elif fmt == "png":
        im.save(path, "PNG", optimize=True)
    else:  # pragma: no cover
        raise ValueError(fmt)
    return os.path.getsize(path)


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    missing = [s for s, _, _ in SOURCES if not os.path.exists(s)]
    if missing:
        print("missing sources: " + ", ".join(missing), file=sys.stderr)
        return 1

    total_src = 0
    total_out = 0
    rows = []

    for name, widths, kind in SOURCES:
        src_bytes = os.path.getsize(name)
        total_src += src_bytes
        stem = os.path.splitext(name)[0]
        stem = stem.replace(" ", "")

        im = Image.open(name)
        im = ImageOps.exif_transpose(im)
        im = to_srgb(im)
        im = im.convert("RGBA" if kind == "alpha" else "RGB")
        src_w, src_h = im.size

        fmts = ("webp", "png") if kind == "alpha" else ("avif", "webp", "jpg")
        made = 0

        for w in widths:
            if w > src_w:  # never upscale; the tier would be a lie
                continue
            h = round(src_h * w / src_w)
            tier = im.resize((w, h), Image.LANCZOS)
            for fmt in fmts:
                path = os.path.join(OUT_DIR, f"{stem}-{w}.{fmt}")
                n = encode(tier, path, kind, fmt)
                made += n
                total_out += n
                rows.append((f"{stem}-{w}.{fmt}", w, h, n))

        rows.append((f"-- {stem} source {src_w}x{src_h}", 0, 0, src_bytes))
        print(f"{name}: {src_w}x{src_h} {src_bytes/1024:.0f} KB -> {made/1024:.0f} KB of derivatives")

    print()
    print(f"{'file':44s} {'w x h':>12s} {'size':>10s}")
    for fn, w, h, n in rows:
        dim = f"{w}x{h}" if w else "-"
        print(f"{fn:44s} {dim:>12s} {n/1024:>8.0f} KB")
    print()
    print(f"originals      {total_src/1024/1024:.1f} MB")
    print(f"all derivatives {total_out/1024/1024:.1f} MB  (every format, every tier)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())