// BrewberryPi website: scroll effects and the 3D case.

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

startReveal();
startCase();

