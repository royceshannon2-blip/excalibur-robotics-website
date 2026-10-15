# Excalibur Robotics — FTC 22972

The team site, built as a **single self-contained HTML file** (`index.html`):
nav, hero, team, the machine, build timeline, achievements, outreach, and
contact — all inline, with no runtime dependencies. Three.js is vendored
inline for the one 3D scene.

Sourced from the open-design project `78216650-fc48-4866-a7f4-8d21aa11ba73`.

## Run

```bash
npm install
npm run dev        # vite on http://localhost:3000 — serves the deployment
npm start          # byte-exact static server (also: npm run preview)
npm run check      # deployment guard: every referenced asset exists + is committed
```

`npm run dev` and `npm start` both serve **the deployment**, not a build of
it. Use `npm start` when you want the exact bytes, since it applies no
transforms at all.

## Deploy

GitHub Pages publishes **the repository root as it sits on disk** — there is no
build step, and `vite` is not part of the deploy. `.nojekyll` is committed so
Pages serves the tree verbatim.

The live site is a *project* page:

    https://royceshannon2-blip.github.io/excalibur-robotics-website/

so it is served from a **sub-path**, and every asset reference must stay
relative (`img/…`, `fonts/…`). A root-absolute reference (`/fonts/…`) points
outside the site and 404s. `npm run check` enforces this.

There is no `dist/`: `vite build` produces a hashed, rewritten bundle that is
**not** what Pages serves, so keeping one around only invites the mistake of
previewing the wrong thing.

## Assets

Two generators keep the shipped assets in step with the source artwork. Both
are dependency-light (`Pillow`) and safe to re-run:

```bash
python3 tools/make-images.py     # AVIF/WebP/JPEG ladders at 480/960/1280/1600
python3 tools/make-favicon.py    # favicon.svg, favicon.ico, apple-touch-icon.png
```

`index.html` offers the image tiers through `<picture>` + `srcset`/`sizes`; the
full-resolution originals stay in the repo as the generators' source and are
never served. `tools/check-deploy.py` (`npm run check`) verifies that
everything the page references exists **and is committed** — the failure that
shipped was a page referencing fonts, photographs and logos that were never in
the repo, so every one of them 404'd in production.

## Mobile

- The 3D roster is desktop/tablet only. It is scroll-scrubbed, so on a phone it
  cost six viewport-heights of scrolling to show twelve people and made the
  device rasterise twelve card textures before the visitor reached it. Phones
  get the flat designed grid; the gate requires a **coarse pointer**, so a
  narrow desktop window keeps the wall.
- Layout breakpoints are width-based, with an extra
  `(pointer: coarse) and (max-height: 560px)` clause so phones in landscape get
  the compact layout instead of the desktop one.
- Touch ergonomics (44px targets, safe-area insets for the notch and home
  indicator) are gated on `pointer: coarse`, so desktop cannot match them.
- `svh` rather than `vh` for the hero and roster stage: on iOS Safari `100vh`
  is the *large* viewport, which made the sticky stage resize as the URL bar
  hid.

## Notes

- Sections are tagged with `data-od-id` and reflow for mobile at ≤920px.
- The dev server differs from the deployment by exactly three things: vite's
  HMR client tag, one blank line from its HTML transform, and inline-CSS
  `url()`s rewritten to root-absolute. That last one is why `npm run check`
  refuses root-absolute references — it is a dev-only rewrite, and it must not
  reach the file.
