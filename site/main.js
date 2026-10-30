// BrewberryPi website: scroll effects, feature cards and the 3D case.

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (selector, root = document) => root.querySelector(selector);

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

// ---------- Features ----------
// To add a feature, add an entry. group: the section it appears in ("mash" or "recipe"). size: "wide" spans two columns on large screens. art: an optional
// illustration (see ART). size "full" spans the whole row. soon: the muted "more to come" card.

const ICONS = {
  list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
  thermo: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0Z"/><path d="M12 10v7"/>',
  bell: '<path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2h-15Z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
  shield: '<path d="M12 3 20 6v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6Z"/><path d="m8.8 12 2.2 2.2 4.2-4.4"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
};

const ART = {
  process: '<div class="mini-shot"><img src="img/app-process-light.webp" width="1464" height="1850" loading="lazy" decoding="async" alt="The app working through the step mash BENIWEISS: the done steps, the active rest with its time left, and the steps still to come"></div>',
  json: '<figure class="mini-file"><figcaption>recipes/BENIWEISS.json</figcaption><pre>{\n  <b>"name"</b>: <i>"München 12.6 - SUD2:BENIWEISS"</i>,\n  <b>"goals"</b>: [\n    { <b>"type"</b>: <i>"PourInBrewingWater"</i> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>40</u> },\n    { <b>"type"</b>: <i>"MashIn"</i> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>52</u> },\n    { <b>"type"</b>: <i>"Rest"</i>, <b>"temperature"</b>: <u>52</u>, <b>"minutes"</b>: <u>30</u>,\n      <b>"name"</b>: <i>"Eiweißrast"</i> },\n    <s>…</s>\n    { <b>"type"</b>: <i>"IodineTest"</i>, <b>"temperature"</b>: <u>73</u>, <b>"minutes"</b>: <u>10</u> },\n    { <b>"type"</b>: <i>"HeatUp"</i>, <b>"temperature"</b>: <u>78</u> }\n  ]\n}</pre></figure>',
  curve: '<svg class="mini-curve" viewBox="0 0 300 90" preserveAspectRatio="none" aria-hidden="true"><path class="target" d="M0 22H300"/><path d="M0 84C50 80 80 50 110 30S150 22 170 22H300"/></svg>',
  ask: '<div class="mini-ask">Iodine test successfull?<div><span>Yes</span><span>No</span></div></div>',
};

const FEATURES = [
  { group: "mash", icon: "thermo", title: "Temperature control", size: "wide", art: "curve",
    text: "Full power to heat up, half power close to the target, then it holds each rest while the pump keeps the mash moving. A chart shows the kettle temperature since the start, so you see each ramp and rest as it happens." },
  { group: "mash", icon: "bell", title: "It guides you through the brew", size: "wide", art: "ask",
    text: "BrewberryPi heats, holds the rests and runs the pump on its own, and tells you when it's your turn: pour in the water, mash in, do the iodine test. Confirm on any device, and it carries on. A buzzer reminds you until you do." },
  { group: "mash", icon: "shield", title: "Safe by design", size: "wide",
    text: "The heater is off whenever it isn't actively controlling temperature. All outputs go off at start-up and on every stop, crash or hang, backed by the systemd and hardware watchdogs." },
  { group: "mash", icon: "spark", title: "More to come", size: "wide", soon: true,
    text: "The feature list grows with the project. Have an idea? Open an issue on GitHub." },
  { group: "recipe", icon: "list", title: "Mashing process as step lists", size: "wide", art: "process",
    text: "Write your mash schedule once as a list of steps: the target temperature of each heat-up, the temperature and minutes of each rest, the extra minutes after an iodine test that isn't done yet, and the boil time. Give your rests their own names. BrewberryPi works through it step by step, like this step mash for a wheat beer." },
  { group: "recipe", icon: "file", title: "Easy mash process creation", size: "wide", art: "json",
    text: "A recipe is a small JSON file: list the steps with their temperatures and minutes. Drop it into the recipes folder on the Pi's network share, and it shows up in the app within seconds." },
];

function renderFeatures() {
  for (const group of ["mash", "recipe"]) {
    const grid = $(`#features-${group}`);
    if (!grid) continue;
    grid.replaceChildren();
    FEATURES.filter((f) => f.group === group).forEach((f, i) => {
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

