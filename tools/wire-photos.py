#!/usr/bin/env python3
"""One-shot: wire the real member photos into index.html.

Run once from the repo root:  python3 tools/wire-photos.py
"""
import re
import sys

PATH = "index.html"
html = open(PATH, encoding="utf-8").read()
orig = html

def picture(stem, alt, tiers):
    """Responsive <picture> for the derivative ladder tools/make-images.py makes."""
    a = ", ".join(f"img/{stem}-{w}.avif {w}w" for w in tiers)
    w = ", ".join(f"img/{stem}-{w}.webp {w}w" for w in tiers)
    j = ", ".join(f"img/{stem}-{w}.jpg {w}w" for w in tiers)
    return (
        f'<picture>\n'
        f'            <source type="image/avif" srcset="{a}">\n'
        f'            <source type="image/webp" srcset="{w}">\n'
        f'            <img src="img/{stem}-{tiers[0]}.jpg" srcset="{j}" alt="{alt}">\n'
        f'          </picture>'
    )

MEDIA = re.compile(r'<div class="profile-media">.*?</div>\s*</div>', re.S)

def swap_media(block, new_media):
    return MEDIA.sub(lambda m: new_media, block, count=1)

# ── 1 · roster cards (display name in <h3> → derivative stem) ──────────
# Yichen and Zach have no photos yet — they keep the labelled placeholder.
ROSTER = [
    ("Royce", "Royce", [480, 960]),
    ("Kahlan", "Kahlan", [480, 960]),
    ("Lucas", "Lucas", [480, 960]),
    ("Sanjay K.", "Sanjay K.", [480, 960]),
    ("SJ", "SJ", [480, 960]),
    ("Eshaw", "Eshan", [480, 960]),
    ("Peyton", "Peyton", [480, 960]),
    ("Keerthika", "Keerthika", [480]),
    ("Audrey", "Audrey", [480]),
    ("Reese", "Reese", [480, 960]),
]
for display, stem, tiers in ROSTER:
    done = False
    for m in re.finditer(r'<article class="profile-card".*?</article>', html, re.S):
        block = m.group(0)
        if re.search(r"<h3 class=\"profile-name\">\s*" + re.escape(display) + r"\s*</h3>", block):
            new_media = ('<div class="profile-media">\n          '
                         + picture(stem, display.strip(), tiers)
                         + '\n        </div>')
            html = html.replace(block, swap_media(block, new_media), 1)
            done = True
            break
    if not done:
        print(f"  ! roster card not found: {display}", file=sys.stderr)

# ── 2 · captain cards (three lead-profile panels, in page order) ──────
CAPTAINS = [("Trey", [480, 960]), ("Sanjey", [480, 960]), ("Lamont", [480, 960])]
lead_blocks = list(re.finditer(r'<article class="lead-profile".*?</article>', html, re.S))
assert len(lead_blocks) == 3, f"expected 3 captain cards, found {len(lead_blocks)}"
for m, (name, tiers) in zip(lead_blocks, CAPTAINS):
    block = m.group(0)
    new_media = ('<div class="profile-media">\n          '
                 + picture(name, name, tiers)
                 + '\n        </div>')
    html = html.replace(block, swap_media(block, new_media), 1)

# ── 3 · alumni grid — the people without current-team cards ────────────
ALUMNI = ["Abhi", "Ansh", "Arpan", "Matthew", "Vishwanth"]  # small WebP originals
cards = []
for name in ALUMNI:
    cards.append(
        f'''      <article class="alumni-card">
        <div class="profile-media">
          <img src="{name}.webp" alt="{name}">
        </div>
        <div class="alumni-meta">
          <span class="alumni-role">Alumni</span>
          <span class="alumni-name">{name}</span>
        </div>
      </article>'''
    )
m = re.search(r'<div class="alumni-grid">.*?</article>\s*</div>', html, re.S)
assert m, "alumni-grid block not found"
html = html.replace(m.group(0), '<div class="alumni-grid">\n' + "\n\n".join(cards) + '\n    </div>', 1)

# ── 4 · CSS: size the real photos in the slots the placeholders owned ──
html = html.replace(
    ".lead-profile .profile-media img { width: 100%; height: 100%; object-fit: cover; display: block; }",
    ".lead-profile .profile-media img { width: 100%; aspect-ratio: 4 / 5; object-fit: cover; display: block; }",
)
html = html.replace(
    ".alumni-card .profile-media { border-bottom: 1px solid var(--border); }",
    ".alumni-card .profile-media { border-bottom: 1px solid var(--border); }\n"
    ".alumni-card .profile-media img { width: 100%; aspect-ratio: 5 / 4; object-fit: cover; display: block; }",
)

assert html != orig
open(PATH, "w", encoding="utf-8").write(html)
print("index.html updated")