import { defineConfig } from "vite";
import { gzipSync } from "node:zlib";

/* ═══ serving the actual deployment ═══════════════════════════════════
   There is no build step here. GitHub Pages publishes the repository
   root exactly as it sits on disk — one index.html plus img/, fonts/ and
   the icons — so the deployed bytes ARE the working-tree bytes, and
   `vite build` is not part of the deploy at all.

   That makes the dev server 99% faithful already: vite does not rewrite
   the inline CSS, the <picture> srcsets or the asset URLs. Two things
   are left, and both are fixed below.

   1. Compression. Pages gzips text, the dev server does not, so a local
      page load is ~4x heavier than production — which makes phones look
      slow for no real reason. The middleware below mirrors the CDN.
   2. The dev error overlay, which is a dev affordance and never ships.

   The one remaining difference is the `<script src="/@vite/client">`
   tag vite injects for reload-on-save (58 bytes, no effect on what you
   see). `npm start` serves the deployment byte-for-byte if you want to
   check against that.
   ═══════════════════════════════════════════════════════════════════ */

/** What Pages compresses: text, and anything that is really text. */
const COMPRESSIBLE = /^(?:text\/|application\/(?:javascript|json|xml|manifest\+json)|image\/svg\+xml)/i;
const MIN_BYTES = 1024; /* below one packet, gzip costs more than it saves */

function pagesLikeCompression() {
  const middleware = (req, res, next) => {
    if (!/\bgzip\b/i.test(String(req.headers["accept-encoding"] || ""))) return next();

    const rawWrite = res.write.bind(res);
    const rawEnd = res.end.bind(res);
    const chunks = [];
    const toBuf = (chunk, enc) =>
      Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, typeof enc === "string" ? enc : undefined);

    res.write = (chunk, enc) => {
      if (chunk) chunks.push(toBuf(chunk, enc));
      return true;
    };

    res.end = (chunk, enc) => {
      if (chunk && typeof chunk !== "function") chunks.push(toBuf(chunk, enc));
      const body = Buffer.concat(chunks);

      /* Some handlers (vite's static middleware, for one) call writeHead and
         then stream the file, so the head is already on the wire by the time
         we get here. Their Content-Length was computed against the raw bytes,
         so the only correct move is to replay the raw bytes and stop —
         touching a header now throws ERR_HTTP_HEADERS_SENT. */
      if (res.headersSent) {
        if (body.length) rawWrite(body);
        return rawEnd();
      }

      const compressible =
        req.method !== "HEAD" &&
        res.statusCode === 200 &&
        body.length >= MIN_BYTES &&
        COMPRESSIBLE.test(String(res.getHeader("content-type") || "")) &&
        !res.hasHeader("content-encoding");

      if (!compressible) {
        if (!res.hasHeader("content-length")) res.setHeader("content-length", body.length);
        return rawEnd(body);
      }

      const zipped = gzipSync(body, { level: 6 });
      res.removeHeader("content-length");
      res.setHeader("content-encoding", "gzip");
      res.setHeader("vary", "Accept-Encoding");
      res.setHeader("content-length", zipped.length);
      return rawEnd(zipped);
    };

    next();
  };

  return {
    name: "pages-like-compression",
    /* NB: these hooks must NOT return anything. `middlewares.use()` returns
       the connect app, and vite treats a returned value as a post-hook and
       calls it — which crashed the server with
       "Cannot read properties of undefined (reading 'url')". */
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}

export default defineConfig({
  /* the deployment lives at the repo root; there is no public/ directory
     and nothing here should be copied or rewritten */
  publicDir: false,
  /* mpa, not spa: Pages serves a real 404 for an unknown path, while the
     default single-page fallback would quietly answer 200 with index.html
     and hide a broken link until it reached production */
  appType: "mpa",
  plugins: [pagesLikeCompression()],
  server: {
    port: 3000,
    host: process.env.HOST === undefined ? true : process.env.HOST,
    /* the overlay is a dev affordance; production never shows it */
    hmr: { overlay: false },
  },
});
