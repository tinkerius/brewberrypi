// BrewberryPi website: scroll effects, features, recipe and the 3D case.

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (selector, root = document) => root.querySelector(selector);
const svgNS = "http://www.w3.org/2000/svg";

// ---------- Nav ----------

const navLinks = [...document.querySelectorAll(".nav__links a")];
const sectionObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    for (const link of navLinks) link.classList.toggle("is-active", link.hash === `#${entry.target.id}`);
  }
}, { rootMargin: "-45% 0px -50% 0px" });
// Links to sections of this page (index.html#start) light up while their section is in view.
const pagePath = (path) => path.replace(/index\.html$/, "");
for (const link of navLinks) {
  if (!link.hash || pagePath(link.pathname) !== pagePath(location.pathname)) continue;
  const section = $(link.hash);
  if (section) sectionObserver.observe(section);
}
const hero = $(".hero");
if (hero) sectionObserver.observe(hero); // no link: clears the highlight at the top

// ---------- Recipe model ----------
// A simplified kettle: enough to draw a believable curve for the recipe profile. The real
// controller and its physics live in brewberrypi-app.

const START_TEMPERATURE = 18;
const HEAT_RATE = 1.6; // °C per minute at full power
const NEAR_TARGET = 3; // °C: half power from here (control.nearTargetBand, nearTargetPower)

const fmt = (t) => `${Number(t).toFixed(1)}`;

function describe(goal) {
  switch (goal.type) {
    case "PourInBrewingWater": return { name: "Add Water", desc: "Pour in the brewing water.", kind: "you", detail: "your turn" };
    case "HeatUp": return { name: "Heat Up", desc: `Heat up mash to ${fmt(goal.temperature)} degrees (C).`, kind: "heat", detail: `to ${goal.temperature} °C` };
    case "MashIn": return { name: "Mash In", desc: "Now it's your job to mash in the malt.", kind: "you", detail: "your turn" };
    case "Rest": return {
      name: goal.name ?? "Rest", custom: Boolean(goal.name),
      desc: goal.description ?? `Rest at ${fmt(goal.temperature)} degrees (C) for ${goal.minutes}min.`,
      kind: "rest", detail: `${goal.temperature} °C · ${goal.minutes} min`,
    };
    case "IodineTest": return { name: "Iodine Test", desc: "Now it's your job to do the iodine test.", kind: "you", detail: `yes / no at ${goal.temperature} °C` };
    case "Lautering": return { name: "Lautering", desc: "Now it's your job to lauter.", kind: "you", detail: "your turn" };
    case "HeatUpForHopsCooking": return { name: "Heat Up", desc: "Heat up mash for cooking", kind: "heat", detail: "to 97 °C" };
    case "CookWater": return { name: goal.name ?? "Boil", desc: goal.description ?? "", kind: "rest", detail: `boil · ${goal.minutes} min` };
    default: return { name: goal.type, desc: "", kind: "rest", detail: "" };
  }
}

/** The temperature a goal controls to, or null for operator steps. */
function targetOf(goal) {
  switch (goal.type) {
    case "HeatUp": case "Rest": case "IodineTest": return goal.temperature;
    case "HeatUpForHopsCooking": return 97;
    case "CookWater": return 100;
    default: return null;
  }
}

/** Minute-by-minute samples {t, T, heat, pump, goal} and one segment per goal. */
function simulate(goals) {
  const samples = [];
  const segments = [];
  let t = 0;
  let T = START_TEMPERATURE;
  const step = 0.5;
  const push = (heat, pump, goal) => samples.push({ t, T, heat, pump, goal });

  goals.forEach((goal, index) => {
    const info = describe(goal);
    const t0 = t;
    const hold = (minutes, target, duty) => {
      for (let m = 0; m < minutes; m += step) {
        t += step;
        T = target + Math.sin(t * 1.7) * 0.12; // the hysteresis wobble
        push(duty + 0.12 * Math.sin(t * 2.3), true, index);
      }
    };
    const heatTo = (target) => {
      while (T < target - 0.05) {
        const power = target - T > NEAR_TARGET ? 1 : 0.5;
        t += step;
        T = Math.min(target, T + HEAT_RATE * power * step);
        push(power, true, index);
      }
      t += step;
      push(0.3, true, index);
    };
    const wait = (minutes, drop = 0, pump = false) => {
      const start = T;
      for (let m = 0; m < minutes; m += step) {
        t += step;
        T = start - drop * Math.min(1, (m + step) / 2);
        push(0, pump, index);
      }
    };

    switch (goal.type) {
      case "PourInBrewingWater": wait(6); break;
      case "HeatUp": heatTo(goal.temperature); break;
      case "MashIn": wait(6, 2.5); break; // the cold malt pulls the temperature down
      case "Rest": hold(goal.minutes, goal.temperature, 0.3); break;
      case "IodineTest": hold(6, goal.temperature, 0.3); break;
      case "Lautering": wait(8, 1.5); break;
      case "HeatUpForHopsCooking": heatTo(97); break;
      case "CookWater": hold(goal.minutes, 99.5, 0.9); break;
      default: wait(4);
    }
    segments.push({ ...info, index, t0, t1: t, target: targetOf(goal) });
  });
  return { samples, segments, total: t };
}

/** SVG path of the samples in a box of width w and height h, for temperatures lo..hi; from the start of
 *  the brew (fromStart) or from the first sample. */
function pathOf(samples, total, w, h, lo, hi, fromStart = true) {
  const x = (t) => (t / total) * w;
  const y = (T) => h - ((T - lo) / (hi - lo)) * h;
  const first = fromStart ? { t: 0, T: START_TEMPERATURE } : samples[0];
  let d = `M${x(first.t).toFixed(1)} ${y(first.T).toFixed(1)}`;
  for (const s of samples) d += `L${x(s.t).toFixed(1)} ${y(s.T).toFixed(1)}`;
  return d;
}

// ---------- Recipe section ----------

function renderRecipe(recipe, model) {
  if (!$("#recipe-steps")) return;
  $("#recipe-name").textContent = recipe.name.replace(" - ", " – ");
  const W = 1000, H = 160, LO = 10, HI = 85;
  const svg = $("#recipe-profile");
  const base = document.createElementNS(svgNS, "line");
  base.setAttribute("class", "base");
  base.setAttribute("x1", 0); base.setAttribute("x2", W); base.setAttribute("y1", H); base.setAttribute("y2", H);
  svg.append(base);
  const colour = { heat: "var(--brass)", rest: "var(--pink)", you: "var(--leaf)" };
  for (const seg of model.segments) {
    const samples = model.samples.filter((s) => s.goal === seg.index);
    if (!samples.length) continue;
    const prev = model.samples[model.samples.indexOf(samples[0]) - 1];
    const pts = prev ? [prev, ...samples] : samples;
    const d = pathOf(pts, model.total, W, H, LO, HI, false);
    const x0 = (pts[0].t / model.total) * W, x1 = (pts.at(-1).t / model.total) * W;
    const area = document.createElementNS(svgNS, "path");
    area.setAttribute("class", "area");
    area.setAttribute("d", `${d}L${x1} ${H}L${x0} ${H}Z`);
    area.setAttribute("fill", colour[seg.kind]);
    const line = document.createElementNS(svgNS, "path");
    line.setAttribute("class", "seg");
    line.setAttribute("d", d);
    line.setAttribute("stroke", colour[seg.kind]);
    svg.append(area, line);
  }

  const list = $("#recipe-steps");
  model.segments.forEach((seg, i) => {
    const li = document.createElement("li");
    li.className = `recipe__step recipe__step--${seg.kind}`;
    li.innerHTML = `<small>${String(i + 1).padStart(2, "0")}</small><b></b><span></span>`;
    li.querySelector("b").textContent = seg.name;
    // Custom step names come from the recipe file; the example's are German, which lets the browser hyphenate them.
    if (seg.custom) li.querySelector("b").lang = "de";
    li.querySelector("span").textContent = seg.detail;
    list.append(li);
  });
}

// ---------- Features ----------
// To add a feature, add an entry. size: "wide" spans two columns on large screens. art: an optional
// illustration (see ART). size "full" spans the whole row. soon: the muted "more to come" card.

const ICONS = {
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  thermo: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0Z"/><path d="M12 10v7"/>',
  bell: '<path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15Z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  devices: '<rect x="2.5" y="4.5" width="13" height="9" rx="1.5"/><path d="M6 17.5h6M9 13.5v4"/><rect x="17.5" y="8.5" width="4" height="11" rx="1"/>',
  shield: '<path d="M12 3 20 6v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6Z"/><path d="m8.8 12 2.2 2.2 4.2-4.4"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  curve: '<path d="M3 20h18"/><path d="M4 17l4-6 3 2 4-7h5"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
};

const ART = {
  process: '<div class="mini-shot"><img src="img/app-process-light.webp" width="1464" height="1850" loading="lazy" decoding="async" alt="The app working through the step mash BENIWEISS: the done steps, the active rest with its time left, and the steps still to come"></div>',
  json: '<figure class="mini-file"><figcaption>recipes/BENIWEISS.json</figcaption><pre>{\n  <b>"name"</b>: <i>"München 12.6 - SUD2:BENIWEISS"</i>,\n  <b>"goals"</b>: [\n    { <b>"type"</b>: <i>"PourInBrewingWater"</i> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>40</u> },\n    { <b>"type"</b>: <i>"MashIn"</i> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>52</u> },\n    { <b>"type"</b>: <i>"Rest"</i>, <b>"temperature"</b>: <u>52</u>, <b>"minutes"</b>: <u>30</u>,\n      <b>"name"</b>: <i>"Eiweißrast"</i> },\n    <s>…</s>\n    { <b>"type"</b>: <i>"IodineTest"</i>, <b>"temperature"</b>: <u>73</u>, <b>"minutes"</b>: <u>10</u> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>78</u> }\n  ]\n}</pre></figure>',
  curve: '<svg class="mini-curve" viewBox="0 0 300 90" preserveAspectRatio="none" aria-hidden="true"><path class="target" d="M0 22H300"/><path d="M0 84C50 80 80 50 110 30S150 22 170 22H300"/></svg>',
  ask: '<div class="mini-ask">Iodine test successfull?<div><span>Yes</span><span>No</span></div></div>',
  devices: '<div class="mini-devices" aria-hidden="true"><i></i><i></i><i></i></div>',
};

const FEATURES = [
  { icon: "list", title: "Recipes as step lists", size: "wide", art: "process",
    text: "Write your mash schedule once: heat up, rest, mash in, iodine test, lautering, boil. BrewberryPi works through it step by step, like this step mash for a wheat beer." },
  { icon: "file", title: "Easy mash process creation", size: "wide", art: "json",
    text: "A recipe is a small JSON file: list the steps with their temperatures and minutes. Drop it into the recipes folder on the Pi's network share, and it shows up in the app within seconds." },
  { icon: "bell", title: "It guides you through the brew", size: "wide", art: "ask",
    text: "BrewberryPi heats, holds the rests and runs the pump on its own, and tells you when it's your turn: pour in the water, mash in, do the iodine test. Confirm on any device, and it carries on. A buzzer reminds you until you do." },
  { icon: "thermo", title: "Temperature control", size: "wide", art: "curve",
    text: "Full power to heat up, half power close to the target, then it holds each rest while the pump keeps the mash moving." },
  { icon: "devices", title: "Live on every screen", art: "devices",
    text: "Temperature, heater power and pump at a glance, pushed to every browser in your network the moment they change. Any of them can control the brew." },
  { icon: "curve", title: "The whole curve",
    text: "A chart of the kettle temperature since the start, so you see each ramp and rest as it happens." },
  { icon: "shield", title: "Safe by design", size: "wide",
    text: "The heater is off whenever it isn't actively controlling temperature. All outputs go off at start-up and on every stop, crash or hang, backed by the systemd and hardware watchdogs." },
  { icon: "spark", title: "More to come", size: "full", soon: true,
    text: "The feature list grows with the project. Have an idea? Open an issue on GitHub." },
];

function renderFeatures() {
  const grid = $("#feature-grid");
  if (!grid) return;
  grid.replaceChildren();
  FEATURES.forEach((f, i) => {
    const card = document.createElement("article");
    card.className = `feature card reveal${f.size ? ` feature--${f.size}` : ""}${f.soon ? " feature--soon" : ""}`;
    card.style.setProperty("--d", `${(i % 4) * 0.06}s`);
    card.innerHTML = `<span class="feature__icon"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[f.icon]}</svg></span>
      <h3></h3><p></p>${f.art ? `<div class="feature__art">${ART[f.art]}</div>` : ""}`;
    card.querySelector("h3").textContent = f.title;
    card.querySelector("p").textContent = f.text;
    grid.append(card);
  });
}

// ---------- Reveal on scroll, browser tilt ----------

function startReveal() {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-in");
        observer.unobserve(entry.target);
      }
    }
  }, { rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".reveal").forEach((el, i) => {
    if (!el.style.getPropertyValue("--d") && el.closest(".hero")) el.style.setProperty("--d", `${i * 0.08}s`);
    observer.observe(el);
  });

  const browser = $(".browser");
  if (reducedMotion || !browser) return;
  const tilt = () => {
    const rect = browser.getBoundingClientRect();
    const p = Math.max(0, Math.min(1, (innerHeight - rect.top) / (innerHeight * 0.9)));
    browser.style.setProperty("--tilt", `${(1 - p) * 18}deg`);
  };
  addEventListener("scroll", tilt, { passive: true });
  tilt();
}

// ---------- 3D case (lazy) ----------

function startCase() {
  const host = $("#case-viewer");
  if (!host) return;
  const observer = new IntersectionObserver(async ([entry]) => {
    if (!entry.isIntersecting) return;
    observer.disconnect();
    try {
      const { mountCase } = await import("./case3d.js");
      await mountCase(host, { reducedMotion });
    } catch (error) {
      console.warn("3D case view unavailable; showing the render instead.", error);
    }
  }, { rootMargin: "300px 0px" });
  observer.observe(host);
}

// ---------- Start ----------

renderFeatures();
startReveal();
startCase();

if ($("#recipe-steps")) fetch("data/recipe.json")
  .then((response) => response.json())
  .then((recipe) => renderRecipe(recipe, simulate(recipe.goals)))
  .catch((error) => console.warn("Recipe not loaded.", error));
