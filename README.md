# Excalibur Robotics — FTC 22972

The team site, built as a **single self-contained HTML file** (`index.html`):
nav, hero, team, the machine, build timeline, achievements, outreach, and
contact — all inline, with no runtime dependencies.

Sourced from the open-design project `78216650-fc48-4866-a7f4-8d21aa11ba73`.

## Run

```bash
npm install
npm run dev        # Vite dev server on http://localhost:3000
npm run build      # production build to dist/
npm run preview    # serve the production build
npm start          # zero-dependency static server (node server.js)
```

## Deploy

`index.html` is the entire site. It can be published directly to any static
host (GitHub Pages, Netlify, S3, …) with no build step — `npm run build`
exists only to produce an identical `dist/` for convenience.

## Notes

- The prototype is fully self-contained: no external requests at runtime,
  no fonts, images, or models to host.
- Sections are tagged with `data-od-id` and reflow for mobile at ≤920px.
- Fonts referenced by the design fall back to system stacks.
