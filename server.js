/**
 * Biobuzz26-27 — Node.js dev server (zero dependencies)
 *
 * Serves the self-contained FTC 22972 Excalibur prototype (index.html).
 * Run: npm start   (http://localhost:3000)
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { fileURLToPath } from "node:url";

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || "127.0.0.1";
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_PAGE = "index.html";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".mp4": "video/mp4",
  ".mp3": "audio/mpeg",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".pdf": "application/pdf",
};

function notFound(res) {
  res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
  res.end("<h1>404 — Not Found</h1><p><a href='/'>Back to home</a></p>");
}

const server = http.createServer((req, res) => {
  try {
    // Decode the URL and strip the query string
    const urlPath = decodeURIComponent(new URL(req.url, `http://${HOST}:${PORT}`).pathname);

    // "/" -> home page
    let filePath = urlPath === "/" ? `/${DEFAULT_PAGE}` : urlPath;

    // Resolve safely: prevent path traversal outside ROOT
    const resolved = path.normalize(path.join(ROOT, filePath));
    if (!resolved.startsWith(ROOT + path.sep) && resolved !== ROOT) {
      return notFound(res);
    }

    fs.stat(resolved, (err, stat) => {
      // Serve directories' default page (e.g. / -> home.html already handled)
      if (!err && stat.isDirectory()) {
        return fs.stat(path.join(resolved, DEFAULT_PAGE), (e2, s2) => {
          if (e2 || !s2.isFile()) return notFound(res);
          streamFile(path.join(resolved, DEFAULT_PAGE), req, res);
        });
      }
      if (err || !stat.isFile()) return notFound(res);
      streamFile(resolved, req, res);
    });
  } catch {
    notFound(res);
  }
});

/* Types GitHub Pages compresses. Compressing here too means a local load
   costs what the deployed load costs — which matters most on a phone,
   where an uncompressed 715 KB page looks far worse than the real thing. */
const COMPRESSIBLE = /^(?:text\/|application\/(?:javascript|json|xml|manifest\+json)|image\/svg\+xml)/i;
const MIN_BYTES = 1024;

function streamFile(file, req, res) {
  const ext = path.extname(file).toLowerCase();
  const type = MIME[ext] || "application/octet-stream";
  fs.readFile(file, (err, data) => {
    if (err) return notFound(res);

    const wantsGzip = /\bgzip\b/i.test(String(req.headers["accept-encoding"] || ""));
    const headers = {
      "Content-Type": type,
      "Cache-Control": "no-cache", // local preview: always fresh
      Vary: "Accept-Encoding",
    };

    if (wantsGzip && data.length >= MIN_BYTES && COMPRESSIBLE.test(type)) {
      data = gzipSync(data, { level: 6 });
      headers["Content-Encoding"] = "gzip";
    }

    headers["Content-Length"] = data.length;
    res.writeHead(200, headers);
    res.end(req.method === "HEAD" ? undefined : data);
  });
}

server.listen(PORT, HOST, () => {
  console.log("");
  console.log("  Biobuzz26-27 — Excalibur Robotics (FTC 22972) dev server");
  console.log("  ───────────────────────────────────────────────────────");
  console.log(`  Serving:  ${ROOT}`);
  console.log(`  URL:      http://${HOST === "0.0.0.0" ? "localhost" : HOST}:${PORT}/`);
  console.log("  Press Ctrl+C to stop.");
  console.log("");
});