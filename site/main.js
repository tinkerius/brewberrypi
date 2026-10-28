// BrewberryPi website: theme, scroll effects, the live hero card, features, recipe and the 3D case.

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (selector, root = document) => root.querySelector(selector);
const svgNS = "http://www.w3.org/2000/svg";

// ---------- Theme ----------

function currentTheme() {
  return document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
}

$("#theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch { /* storage blocked: the choice lasts for this page only */ }
  document.dispatchEvent(new CustomEvent("themechange"));
});

// ---------- Nav ----------

const nav = $(".nav");
const onScroll = () => nav.classList.toggle("is-scrolled", scrollY > 8);
addEventListener("scroll", onScroll, { passive: true });
onScroll();

const navLinks = [...document.querySelectorAll(".nav__links a")];
const sectionObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    for (const link of navLinks) link.classList.toggle("is-active", link.hash === `#${entry.target.id}`);
  }
}, { rootMargin: "-45% 0px -50% 0px" });
for (const link of navLinks) {
  const section = $(link.hash);
  if (section) sectionObserver.observe(section);
}
sectionObserver.observe($(".hero")); // no link: clears the highlight at the top

// ---------- Pointer glow on cards ----------

addEventListener("pointermove", (event) => {
  const card = event.target.closest?.(".glow");
  if (!card) return;
  const rect = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${event.clientX - rect.left}px`);
  card.style.setProperty("--my", `${event.clientY - rect.top}px`);
}, { passive: true });

// ---------- Recipe model ----------
// A simplified kettle: enough to draw a believable curve for the hero and the recipe profile. The real
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
      name: goal.name ?? "Rest",
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
    segments.push({ ...info, index, t0, t1: t });
  });
  return { samples, segments, total: t };
}

function sampleAt(model, t) {
  const { samples } = model;
  if (t <= 0) return { t: 0, T: START_TEMPERATURE, heat: 0, pump: false, goal: 0 };
  const i = Math.min(samples.length - 1, Math.max(0, Math.round(t / 0.5) - 1));
  return samples[i];
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

// ---------- Live hero card ----------

function startHero(model) {
  const W = 600, H = 220, LO = 10, HI = 85;
  const chart = $("#live-chart");
  const grid = $(".live__grid", chart);
  for (const T of [20, 40, 60, 80]) {
    const y = H - ((T - LO) / (HI - LO)) * H;
    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", 0); line.setAttribute("x2", W);
    line.setAttribute("y1", y); line.setAttribute("y2", y);
    grid.append(line);
  }
  const d = pathOf(model.samples, model.total, W, H, LO, HI);
  $("#curve-line").setAttribute("d", d);
  $("#curve-ghost").setAttribute("d", d);
  $("#curve-area").setAttribute("d", `${d}L${W} ${H}L0 ${H}Z`);

  const clip = $("#curve-clip-rect");
  const dot = $("#live-dot");
  const live = $(".live");
  const el = {
    temp: $("#live-temp"), goal: $("#live-goal"), desc: $("#live-desc"), progress: $("#live-progress"),
    heat: $("#live-heat"), pump: $("#live-pump"), state: $("#live-state"),
  };
  let shownGoal = -1;

  function render(t) {
    const s = sampleAt(model, t);
    const seg = model.segments[s.goal];
    clip.setAttribute("width", (t / model.total) * W);
    el.temp.textContent = s.T.toFixed(1);
    if (shownGoal !== s.goal) {
      shownGoal = s.goal;
      el.goal.textContent = seg.name;
      el.desc.textContent = seg.desc;
    }
    const progress = seg.kind === "you" ? 0 : Math.min(1, (t - seg.t0) / (seg.t1 - seg.t0));
    el.progress.style.width = `${(progress * 100).toFixed(1)}%`;
    const heat = Math.max(0, Math.min(1, s.heat));
    el.heat.classList.toggle("is-on", heat > 0.02);
    el.heat.querySelector("b").textContent = `${Math.round(heat * 10) * 10}%`;
    el.pump.classList.toggle("is-on", s.pump);
    el.pump.querySelector("b").textContent = s.pump ? "on" : "off";
    el.state.textContent = t >= model.total ? "Finished" : seg.kind === "you" ? "Waiting for you" : "Running";

    // The dot sits on the end of the curve, in the card's coordinates.
    const box = chart.getBoundingClientRect();
    const card = live.getBoundingClientRect();
    const x = box.left - card.left + (t / model.total) * box.width;
    const y = box.top - card.top + (1 - (s.T - LO) / (HI - LO)) * box.height;
    dot.style.transform = `translate(${x}px, ${y}px)`;
    dot.style.opacity = t > 0 && t < model.total ? 1 : 0;
  }

  if (reducedMotion) {
    render(model.segments[Math.min(6, model.segments.length - 1)].t0 + 10);
    return;
  }

  const DURATION = 16000; // ms for the whole recipe
  const PAUSE = 2600;
  let start = performance.now() + 600;
  let running = true;
  new IntersectionObserver(([entry]) => {
    running = entry.isIntersecting;
    if (running) requestAnimationFrame(frame);
  }).observe(live);
  addEventListener("resize", () => render(Math.max(0, Math.min(model.total, ((performance.now() - start) / DURATION) * model.total))));

  function frame(now) {
    if (!running) return;
    const elapsed = now - start;
    if (elapsed > DURATION + PAUSE) start = now;
    const p = Math.max(0, Math.min(1, elapsed / DURATION));
    render(p * model.total);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

// ---------- Recipe section ----------

function renderRecipe(recipe, model) {
  $("#recipe-name").textContent = recipe.name.replace(" - ", " – ");
  const W = 1000, H = 160, LO = 10, HI = 85;
  const svg = $("#recipe-profile");
  const base = document.createElementNS(svgNS, "line");
  base.setAttribute("class", "base");
  base.setAttribute("x1", 0); base.setAttribute("x2", W); base.setAttribute("y1", H); base.setAttribute("y2", H);
  svg.append(base);
  const colour = { heat: "var(--brass)", rest: "var(--berry)", you: "var(--leaf)" };
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
    li.querySelector("span").textContent = seg.detail;
    list.append(li);
  });
}

// ---------- Features ----------
// To add a feature, add an entry. size: "wide" spans two columns on large screens. art: an optional
// illustration (see ART).

const ICONS = {
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  thermo: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0Z"/><path d="M12 10v7"/>',
  bell: '<path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15Z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  devices: '<rect x="2.5" y="4.5" width="13" height="9" rx="1.5"/><path d="M6 17.5h6M9 13.5v4"/><rect x="17.5" y="8.5" width="4" height="11" rx="1"/>',
  flask: '<path d="M9.5 3h5M10.5 3v6l-5.2 9.1A2 2 0 0 0 7 21h10a2 2 0 0 0 1.7-2.9L13.5 9V3"/><path d="M7.5 15h9"/>',
  chip: '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
  shield: '<path d="M12 3 20 6v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6Z"/><path d="m8.8 12 2.2 2.2 4.2-4.4"/>',
  update: '<path d="M20 11a8 8 0 0 0-14.6-4.5M4 13a8 8 0 0 0 14.6 4.5"/><path d="M5 3v4h4M19 21v-4h-4"/>',
  wifi: '<path d="M2.5 9a14 14 0 0 1 19 0M5.8 12.6a9 9 0 0 1 12.4 0M9.2 16.1a4 4 0 0 1 5.6 0"/><circle cx="12" cy="19.3" r=".9"/>',
  sliders: '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
};

const ART = {
  steps: '<div class="mini-steps"><span class="y">Add Water</span><span class="h">Heat Up 52°</span><span class="y">Mash In</span><span class="r">Rest 30 min</span><span class="h">Heat Up 65°</span><span class="r">Rest 30 min</span><span class="y">Iodine Test</span><span class="h">78°</span></div>',
  curve: '<svg class="mini-curve" viewBox="0 0 300 90" preserveAspectRatio="none" aria-hidden="true"><path class="target" d="M0 22H300"/><path d="M0 84C50 80 80 50 110 30S150 22 170 22H300" stroke="url(#mini-grad)"/><defs><linearGradient id="mini-grad"><stop offset="0" stop-color="var(--brass)"/><stop offset="1" stop-color="var(--berry)"/></linearGradient></defs></svg>',
  ask: '<div class="mini-ask">Iodine test successfull?<div><span>Yes</span><span>No</span></div></div>',
  devices: '<div class="mini-devices" aria-hidden="true"><i></i><i></i><i></i></div>',
};

const FEATURES = [
  { icon: "list", title: "Recipes as step lists", size: "wide", art: "steps",
    text: "Write your mash schedule once: heat up, rest, mash in, iodine test, lautering, boil. BrewberryPi works through it step by step." },
  { icon: "thermo", title: "Temperature control", size: "wide", art: "curve", accent: "var(--brass)",
    text: "Full power to heat up, half power close to the target, then it holds each rest while the pump keeps the mash moving." },
  { icon: "bell", title: "It asks when it needs you", size: "wide", art: "ask", accent: "var(--leaf)",
    text: "Water in? Malt in? Iodine test done? The question appears on screen, and a buzzer beeps until somebody answers." },
  { icon: "devices", title: "Live on every screen", art: "devices",
    text: "Every browser in your network sees the same live state, and any of them can control the brew." },
  { icon: "flask", title: "Simulation mode", accent: "var(--brass)",
    text: "No hardware yet? Run a whole recipe against a simulated kettle, sped up if you like." },
  { icon: "shield", title: "Safe by design", size: "wide", accent: "var(--leaf)",
    text: "The heater is off whenever it isn't actively controlling temperature. All outputs go off at start-up and on every stop, crash or hang, backed by the systemd and hardware watchdogs." },
  { icon: "update", title: "Signed updates, rollback",
    text: "Install a new app version from the browser. Images are signature-checked, and the previous version stays for rollback." },
  { icon: "wifi", title: "Wi-Fi without a keyboard", accent: "var(--brass)",
    text: "No home network found? The Pi opens its own hotspot, and your phone lands on the Wi-Fi setup page." },
  { icon: "chip", title: "Your wiring, your pins", accent: "var(--brass)",
    text: "Pins, relay polarity and the sensor are set in the config, so it fits the relay board you already have." },
  { icon: "sliders", title: "Settings in the browser",
    text: "Device settings on their own page, and the config folder as a network share you open from your computer." },
  { icon: "spark", title: "More to come", size: "wide", soon: true,
    text: "The feature list grows with the project. Have an idea? Open an issue on GitHub." },
];

function renderFeatures() {
  const grid = $("#feature-grid");
  grid.replaceChildren();
  FEATURES.forEach((f, i) => {
    const card = document.createElement("article");
    card.className = `feature card glow reveal${f.size ? ` feature--${f.size}` : ""}${f.soon ? " feature--soon" : ""}`;
    card.style.setProperty("--d", `${(i % 4) * 0.06}s`);
    if (f.accent) card.style.setProperty("--accent", f.accent);
    card.innerHTML = `<span class="feature__icon"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[f.icon]}</svg></span>
      <h3></h3><p></p>${f.art ? `<div class="feature__art">${ART[f.art]}</div>` : ""}`;
    card.querySelector("h3").textContent = f.title;
    card.querySelector("p").textContent = f.text;
    grid.append(card);
  });
}

// ---------- Terminal (OS card) ----------

const TERMINAL = [
  ["cmd", "brewberry-update list"],
  ["dim", "# versions on the Pi and in the registry"],
  ["cmd", "brewberry-update download 0.2.0"],
  ["dim", "# pulls the image, checks its signature"],
  ["cmd", "brewberry-update install 0.2.0 --yes"],
  ["ok", "# switched; the old version is kept"],
  ["cmd", "brewberry-update rollback --yes"],
];

function startTerminal() {
  const term = $("#term");
  const html = (lines) => lines.map(([kind, text]) => kind === "cmd"
    ? `<span class="p">$</span> ${text}` : `<span class="${kind}">${text}</span>`).join("\n");
  if (reducedMotion) { term.innerHTML = html(TERMINAL); return; }

  let timer;
  const run = () => {
    let line = 0, char = 0;
    const done = [];
    const tick = () => {
      if (line >= TERMINAL.length) { timer = setTimeout(run, 3500); return; }
      const [kind, text] = TERMINAL[line];
      if (kind === "cmd" && char < text.length) {
        char += 1;
        term.innerHTML = html([...done, [kind, text.slice(0, char)]]) + '<span class="cursor"></span>';
        timer = setTimeout(tick, 38 + Math.random() * 50);
        return;
      }
      done.push(TERMINAL[line]);
      line += 1; char = 0;
      term.innerHTML = html(done) + '\n<span class="cursor"></span>';
      timer = setTimeout(tick, kind === "cmd" ? 450 : 700);
    };
    tick();
  };
  new IntersectionObserver(([entry]) => {
    clearTimeout(timer);
    if (entry.isIntersecting) run();
  }).observe(term);
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
startTerminal();
startCase();

fetch("data/recipe.json")
  .then((response) => response.json())
  .then((recipe) => {
    const model = simulate(recipe.goals);
    startHero(model);
    renderRecipe(recipe, model);
  })
  .catch((error) => console.warn("Recipe not loaded.", error));
