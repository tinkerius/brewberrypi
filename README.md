# BrewberryPi website

Source of the BrewberryPi website: **https://tinkerius.github.io/brewberrypi/**

BrewberryPi is a Raspberry Pi controller for a home-brewing mash kettle. The project lives in three repositories:

| Repository | Content |
|---|---|
| [brewberrypi-app](https://github.com/tinkerius/brewberrypi-app) | The application (brewing engine, web UI), shipped as a container image |
| [brewberrypi-os](https://github.com/tinkerius/brewberrypi-os) | The operating-system image for Raspberry Pi 3/4/5 |
| [brewberrypi-case](https://github.com/tinkerius/brewberrypi-case) | The 3D-printable case |

## Layout

| Path | Content |
|---|---|
| `site/` | The published site: plain HTML, CSS and JavaScript, no build step (see below) |
| `brand/` | Logo, favicons, social preview and the brand guide (`brand/README.md`); `brand/tools/build_brand.py` regenerates them |
| `tools/` | Scripts that refresh the site's assets from the other repositories |
| `.github/workflows/pages.yml` | Deploys `site/` to GitHub Pages on every push to `main` |

### The site

Three pages (main, software, case), "Instrument": light pages with dark display bands (nav, hero, case, footer), Zilla Slab headlines, mono
labels and the brand pink `#e0789a` as the signature colour. On light backgrounds pink is only a fill under ink text
(highlighter, buttons, markers), never text itself; inside a dark band (`.band-dark`, which redefines the colour
tokens) it may be text too.

| Path | Content | Comes from |
|---|---|---|
| `site/index.html` | Main page: the overview, the three parts (components, software, case) as linked panels, get started | written by hand |
| `site/components.html` | Components: how the Pi, relay board, probe, kettle and pump connect (diagram and legend) | written by hand |
| `site/software.html` | Software details: screenshots, mash controlling, recipe definition, operating system | written by hand |
| `site/case.html` | Case details: the 3D view, front/back/inside, the parts it holds, printing | written by hand |
| `site/styles.css` | Colour tokens (from `brand/README.md`, light and `.band-dark`), layout | written by hand |
| `site/main.js` | Scroll effects, the feature cards (`FEATURES`: add an entry to add a feature) | written by hand |
| `site/case3d.js` | Interactive 3D view of the case (three.js), loaded when the section scrolls into view; part colours from the section's CSS | written by hand |
| `site/components3d.js` | The bought components (Pi, relay board, adapter, switches, sockets, inlet, jack) for the 3D view, modelled from the dimensions and positions in the case spec; shown from the start, hidden with the viewer's "Hide components" button | written by hand; keep in step with `brewberrypi-case/02-specification/spec.md` |
| `site/img/app-*.webp` | Screenshots of the app | `tools/capture_screens.mjs` |
| `site/img/case-still.webp`, `site/img/case-exploded.webp` | Stills of the 3D case for the main page (assembled, exploded) | `tools/render_case.mjs` |
| `site/models/case-*.stl`, `site/img/case-assembly.png` | Case parts and the fallback render | `tools/sync_assets.sh` from `brewberrypi-case/04-stl` |
| `site/vendor/three/` | three.js 0.170.0 (`three.module.min.js`, `STLLoader.js`, `OrbitControls.js`, MIT licence) | npm package `three@0.170.0` |
| logos, favicons, `site/fonts/` | Brand files and Zilla Slab subsets | `brand/tools/build_brand.py` |

### Refreshing the assets

The tools expect the other repositories next to this one (`../brewberrypi-app`, `../brewberrypi-case`).

```sh
tools/sync_assets.sh               # case STLs, case render
node tools/capture_screens.mjs     # app screenshots
node tools/render_case.mjs         # stills of the 3D case (after sync_assets.sh)
```

`capture_screens.mjs` starts the app in simulation (`--dummymode`, 40× faster), runs the example recipe, answers
its questions and takes the screenshots in light mode, desktop and phone. It needs `make setup` and `make build`
done in `brewberrypi-app`, Node with Playwright and Python with Pillow. It takes about two minutes.

## Preview locally

```sh
python3 -m http.server -d site 8000
```

Then open http://localhost:8000/.

## Publishing

Repository settings: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
A push (or merge) to `main` runs *Deploy to GitHub Pages*; the workflow can also be started by hand
from the Actions tab.

## Visitor statistics

Page views are counted by [GoatCounter](https://www.goatcounter.com/) (no cookies, no consent banner needed);
the dashboard is at https://brewberrypi.goatcounter.com. Each page loads its script at the end of `<head>`,
so a new page needs the same two lines. Visits from `localhost` are not counted.
