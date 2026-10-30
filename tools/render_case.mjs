// Renders stills of the 3D case, with its components, for the main page: assembled (site/img/case-still.webp, hero) and exploded
// (site/img/case-exploded.webp, get-started step 1).
//
// Serves site/ locally, opens case.html with reduced motion (no spin), waits for the 3D view and saves it
// with a transparent background, then presses "Explode" and saves it again. Needs Node with Playwright and Python with Pillow (for the WebP file).
//
//   node tools/render_case.mjs

import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// require() so that a globally installed Playwright (NODE_PATH) is found too.
const { chromium } = createRequire(import.meta.url)("playwright");

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SITE = join(ROOT, "site");
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".woff2": "font/woff2", ".stl": "model/stl" };

const server = createServer((request, response) => {
  const path = normalize(decodeURIComponent(new URL(request.url, "http://x").pathname)).replace(/^(\.\.[/\\])+/, "");
  try {
    const body = readFileSync(join(SITE, path.endsWith("/") ? `${path}index.html` : path));
    response.writeHead(200, { "Content-Type": TYPES[extname(path)] ?? "application/octet-stream" }).end(body);
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((ready) => server.listen(0, "127.0.0.1", ready));
const { port } = server.address();

const browser = await chromium.launch({ args: ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"] });
const tmp = mkdtempSync(join(tmpdir(), "brewberrypi-case-"));
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 }, reducedMotion: "reduce" });
  await page.goto(`http://127.0.0.1:${port}/case.html`);
  // Only the model: no page, no buttons, a fixed size.
  await page.addStyleTag({ content: `
    html, body, .band-dark, .page-head, .case, .case-view { background: transparent !important; }
    .page-head::before, .case-ui, .case-tag, .nav, .page-head > .wrap > :not(.case) { display: none !important; }
    .case { display: block !important; border: 0 !important; }
    .case__body { display: none !important; }
    #case-viewer { width: 900px !important; height: 675px !important; min-height: 0 !important; border: 0 !important; }` });
  await page.locator("#case-viewer canvas").waitFor({ timeout: 30_000 });
  await page.waitForTimeout(1500);
  const save = async (name) => {
    const png = join(tmp, `${name}.png`);
    await page.locator("#case-viewer").screenshot({ path: png, omitBackground: true });
    execFileSync("python3", ["-I", "-c", `
import sys
from PIL import Image
Image.open(sys.argv[1]).save(sys.argv[2], "WEBP", quality=88, method=6)
`, png, join(SITE, "img", `${name}.webp`)]);
    console.log(`wrote site/img/${name}.webp`);
  };
  await save("case-still");
  // The button is hidden by the style above; with reduced motion the parts move apart at once.
  await page.evaluate(() => document.querySelector("#case-explode").click());
  await page.waitForTimeout(800);
  await save("case-exploded");
} finally {
  await browser.close();
  server.close();
  rmSync(tmp, { recursive: true, force: true });
}
