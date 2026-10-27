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
| `site/` | The published site: plain HTML, CSS and images, no build step. Logos, icons and the font are copied in by the brand build |
| `brand/` | Logo, favicons, social preview and the brand guide (`brand/README.md`); `brand/tools/build_brand.py` regenerates them |
| `.github/workflows/pages.yml` | Deploys `site/` to GitHub Pages on every push to `main` |

## Preview locally

```sh
python3 -m http.server -d site 8000
```

Then open http://localhost:8000/.

## Publishing

Repository settings: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
A push (or merge) to `main` runs *Deploy to GitHub Pages*; the workflow can also be started by hand
from the Actions tab.
