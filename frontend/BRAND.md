# Brand files

The logos, favicons and the font in `public/` are copied unchanged from the BrewberryPi brand in
[tinkerius/brewberrypi](https://github.com/tinkerius/brewberrypi) (`brand/`, `site/fonts/`; commit `0446c5e`).
They are generated there by `brand/tools/build_brand.py`: don't edit them here; rebuild them there and copy them again.

| File | From |
|---|---|
| `public/logo.svg`, `public/logo-dark.svg` | `brand/logo.svg`, `brand/logo-dark.svg` |
| `public/favicon.svg`, `public/favicon.ico`, `public/apple-touch-icon.png` | `brand/` |
| `public/fonts/zilla-slab-medium.woff2`, `public/fonts/OFL.txt` | `site/fonts/` (Zilla Slab Medium, Latin subset, SIL Open Font License) |

The brand colours are the theme tokens in `src/styles.css` (`brand/README.md`, "Colours").
