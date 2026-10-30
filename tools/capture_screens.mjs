// Captures the app screenshots for the website from a simulated brew.
//
// Starts brewberrypi-app in simulation (--dummymode, accelerated clock), loads a recipe, starts it,
// confirms the operator requests and takes the screenshots at fixed points of the brew, in light mode,
// desktop and phone. Needs a sibling checkout of brewberrypi-app with `make setup` and
// `make build` done, Node with Playwright, and Python with Pillow (for the WebP files).
//
//   node tools/capture_screens.mjs [path/to/brewberrypi-app]

import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

// require() so that a globally installed Playwright (NODE_PATH) is found too.
const { chromium } = createRequire(import.meta.url)("playwright");

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const APP = resolve(process.argv[2] ?? join(ROOT, "..", "brewberrypi-app"));
const OUT = join(ROOT, "site", "img");
const PORT = 8093;
const API = `http://127.0.0.1:${PORT}`;
// The browser opens the app under the host name a brewer would type; it shows in the top bar.
const BASE = `http://brewberrypi.local:${PORT}`;
const RECIPE = "BENIWEISS";
// The main shots are taken while this goal (index in the recipe) is active: the 65 °C rest.
const MAIN_GOAL = 6;

const VIEWS = [
  { name: "desktop", viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.5 },
  { name: "phone", viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
];
// The website is light with dark bands; it shows the app in light mode.
const SCHEMES = ["light"];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(method, path, body) {
  const response = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return response.json();
}

async function waitFor(predicate, what, timeoutMs = 600_000) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    try {
      const value = await predicate();
      if (value) return value;
    } catch {
      // The server is not up yet.
    }
    await sleep(250);
  }
  throw new Error(`timed out waiting for ${what}`);
}

const runDir = mkdtempSync(join(tmpdir(), "brewberrypi-shots-"));
const pngDir = join(runDir, "png");
mkdirSync(pngDir);
// Simulation runs 40 times faster.
writeFileSync(
  join(runDir, "config.json"),
  JSON.stringify({
    server: { port: PORT },
    recipes: { directory: "recipes" },
    ui: { deviceLink: "http://{host}:8081/" },
    simulation: { timeScale: 40 },
  }),
);

const app = spawn(join(APP, ".venv", "bin", "python"), ["-m", "brewberrypi", "--dummymode", "--config", join(runDir, "config.json")], {
  cwd: APP,
  stdio: ["ignore", "ignore", "inherit"],
});

let browser;
try {
  await waitFor(async () => (await api("GET", "/healthz")).status === "ok", "the app to start", 30_000);

  browser = await chromium.launch({ args: ["--host-resolver-rules=MAP brewberrypi.local 127.0.0.1"] });
  const pages = [];
  for (const view of VIEWS) {
    for (const scheme of SCHEMES) {
      const { name, ...options } = view;
      const context = await browser.newContext({ ...options, colorScheme: scheme });
      const page = await context.newPage();
      await page.goto(BASE + "/");
      pages.push({ page, view: name, file: `app-${name}-${scheme}` });
    }
  }

  await api("PUT", "/api/process", { recipe: RECIPE });
  await api("POST", "/api/process/start");

  // top: scroll to the top first (the app scrolls the active goal into view); views: which views to shoot.
  const shoot = async (suffix, { top = false, views = ["desktop", "phone"] } = {}) => {
    await sleep(1500); // let the pushed state and the chart settle
    for (const { page, view, file } of pages) {
      if (!views.includes(view)) continue;
      if (top) await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: join(pngDir, `${file}${suffix}.png`) });
    }
  };

  // Confirm the operator requests (water, mash in) until the main goal is active.
  await waitFor(async () => {
    const process = await api("GET", "/api/process");
    const active = process.goals.findIndex((goal) => goal.status === "Active");
    const request = process.goals[active]?.activeRequest;
    if (request && request.options.length === 1) {
      await api("POST", `/api/process/requests/${request.id}`, { response: request.options[0] });
    }
    return active === MAIN_GOAL && process.goals[active].statuspercent >= 40;
  }, "the main goal");
  await shoot("", { top: true });
  // The recipe's goal list on its own, for the "Recipes as step lists" feature.
  const desktopLight = pages.find(({ file }) => file === "app-desktop-light").page;
  const card = (title) => desktopLight.locator("section").filter({ has: desktopLight.locator("h2", { hasText: title }) });
  await card("Brewing Process").screenshot({ path: join(pngDir, "app-process-light.png") });
  // The chart, for the "Temperature control" feature.
  await card("Chart").screenshot({ path: join(pngDir, "app-chart-light.png") });

  // The iodine test asks a yes/no question.
  await waitFor(async () => {
    const process = await api("GET", "/api/process");
    const request = process.goals.find((goal) => goal.activeRequest)?.activeRequest;
    if (request && request.options.length === 1) {
      await api("POST", `/api/process/requests/${request.id}`, { response: request.options[0] });
      return false;
    }
    return request && request.options.length > 1;
  }, "the iodine test");
  await shoot("-iodine", { views: ["phone"] });
  // The active goal with its question, for "It guides you through the brew".
  await desktopLight.locator('li[data-status="Active"]').screenshot({ path: join(pngDir, "app-question-light.png") });

  await api("POST", "/api/process/stop");
  // Everything off after the stop, for "Safe by design".
  await sleep(2500);
  await card("Hardware Status").screenshot({ path: join(pngDir, "app-stopped-light.png") });
} finally {
  await browser?.close();
  app.kill("SIGTERM");
}

mkdirSync(OUT, { recursive: true });
execFileSync("python3", ["-I", "-c", `
import pathlib, sys
from PIL import Image
src, out = map(pathlib.Path, sys.argv[1:3])
for png in sorted(src.glob("*.png")):
    target = out / (png.stem + ".webp")
    Image.open(png).save(target, "WEBP", quality=86, method=6)
    print(target.relative_to(out.parent.parent))
`, pngDir, OUT], { stdio: "inherit" });
rmSync(runDir, { recursive: true, force: true });
