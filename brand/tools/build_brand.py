#!/usr/bin/env python3
"""Generate the BrewberryPi logo files in brand/.

The mark is drawn here as SVG geometry on a 64-unit grid; the wordmark is
Zilla Slab Bold, converted to outlines so no font is needed to show it.
PNGs and the ICO are rasterised with headless Chromium (Playwright).

The files the website uses are copied into site/ as well.

Needs: Python packages fonttools, uharfbuzz, brotli and pillow; Node with playwright.
Run from the repository root:  python3 brand/tools/build_brand.py
"""

import base64
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

TOOLS = Path(__file__).resolve().parent
BRAND = TOOLS.parent
CACHE = TOOLS / ".cache"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/zillaslab/{}"

# Colour sets. b berry (body), l leaf (knob), m brass (dial, valve, flames),
# t ink (the "Brewberry" of the name), p the "Pi" of the name.
LIGHT = dict(b="#8a2a4a", l="#3d7a3c", m="#c4821a", t="#2a1d22", p="#8a2a4a")
DARK = dict(b="#e0789a", l="#8fc77f", m="#e9b04f", t="#f1e8eb", p="#e0789a")
MONO = dict(b="#2a1d22", l="#2a1d22", m="#2a1d22", t="#2a1d22", p="#2a1d22")
REVERSED = dict(b="#fbf8f6", l="#9fd18f", m="#f0bd5c", t="#fbf8f6", p="#f3c9d6")
BERRY = "#8a2a4a"
PAPER = "#fbf8f6"

# Files the website in site/ uses; copied there on every build so they stay in sync.
SITE_FILES = ("logo-stacked.svg", "logo-stacked-dark.svg", "mark-dark.svg", "favicon.svg", "favicon.ico",
              "apple-touch-icon.png", "social-preview.png")

TAGLINE = ("Raspberry Pi controller for a", "home-brewing mash kettle")

# Flame on a 16-unit grid, placed into the marks with a transform.
FLAME = ("M8.6 1C11.8 4.2 12.6 6.6 12.6 9.6A4.6 4.6 0 0 1 3.4 9.6C3.4 7.6 4.4 6 5.6 5"
         "C5.8 6.6 6.6 7.4 7.4 7.6C7 5.4 7.4 3 8.6 1Z")


def mask(mid, shapes):
    return (f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
            f'<rect width="64" height="64" fill="#fff"/><g fill="#000">{shapes}</g></mask>')


def flames(xs, y, scale):
    return "".join(f'<path class="m" transform="translate({x:g} {y:g}) scale({scale:g})" d="{FLAME}"/>'
                   for x in xs)


def mark_full(pre):
    """Full mark, for 32 px and up: kettle with berry dots, dial thermometer, ball valve, three flames."""
    return (
        mask(f"{pre}body",
             '<circle cx="32" cy="30" r="8.4"/>'
             '<circle cx="22" cy="41.5" r="2.2"/><circle cx="32" cy="41.5" r="2.2"/><circle cx="42" cy="41.5" r="2.2"/>'
             '<circle cx="27" cy="46.5" r="2"/><circle cx="37" cy="46.5" r="2"/>')
        + mask(f"{pre}dial", '<rect x="31" y="24.6" width="2" height="6.4" rx="1" transform="rotate(40 32 30)"/>')
        + '<rect class="b" x="12" y="12" width="40" height="4.5" rx="2.25"/>'
        + '<rect class="b" x="8" y="21" width="9.5" height="4.5" rx="2.25"/>'
        + '<rect class="b" x="46.5" y="21" width="9.5" height="4.5" rx="2.25"/>'
        + f'<path class="b" mask="url(#{pre}body)" d="M16 18H48V48C48 49.66 46.66 51 45 51H19C17.34 51 16 49.66 16 48Z"/>'
        + '<path class="l" d="M32 11C27.5 11 24 8 23 3.5C28 3.5 31.2 6.6 32 11ZM32 11C32.8 6.6 36 3.5 41 3.5C40 8 36.5 11 32 11Z"/>'
        + f'<circle class="m" mask="url(#{pre}dial)" cx="32" cy="30" r="6.6"/>'
        + '<rect class="m" x="47" y="40" width="7" height="4" rx="1"/><circle class="m" cx="54.2" cy="42" r="3.6"/>'
        + '<rect class="m" x="53.4" y="35.8" width="1.6" height="3.4"/>'
        + '<rect class="m" x="49" y="34" width="11" height="2.8" rx="1.4"/>'
        + flames((18.24, 26.24, 34.24), 51.88, 0.72)
    )


def mark_small(pre):
    """Small mark, for 24 px and below: no dots, bigger dial, plain valve, bolder flames."""
    return (
        mask(f"{pre}body", '<circle cx="32" cy="33.5" r="10.8"/>')
        + mask(f"{pre}dial", '<rect x="30.6" y="26" width="2.8" height="8.8" rx="1.4" transform="rotate(40 32 33.5)"/>')
        + '<rect class="b" x="10" y="11" width="44" height="5.5" rx="2.75"/>'
        + '<rect class="b" x="5.5" y="22" width="11" height="6" rx="3"/>'
        + '<rect class="b" x="47.5" y="22" width="11" height="6" rx="3"/>'
        + f'<path class="b" mask="url(#{pre}body)" d="M15 19H49V46C49 48.2 47.2 50 45 50H19C16.8 50 15 48.2 15 46Z"/>'
        + '<path class="l" d="M32 10.5C26.5 10.5 22.5 7.5 21.5 2.5C27 2.5 31 5.5 32 10.5ZM32 10.5C33 5.5 37 2.5 42.5 2.5C41.5 7.5 37.5 10.5 32 10.5Z"/>'
        + f'<circle class="m" mask="url(#{pre}dial)" cx="32" cy="33.5" r="8"/>'
        + '<rect class="m" x="47" y="38" width="11" height="6.5" rx="2"/>'
        + flames((14.8, 24.8, 34.8), 51.1, 0.9)
    )


def style(c, dark=None):
    rules = "".join(f".{k}{{fill:{v}}}" for k, v in c.items())
    if dark:
        rules += "@media (prefers-color-scheme: dark){" + "".join(f".{k}{{fill:{v}}}" for k, v in dark.items()) + "}"
    return f"<style>{rules}</style>"


def svg(view_box, body, title, c, dark=None, size=None):
    w, h = view_box[2], view_box[3]
    dims = f' width="{size[0]:g}" height="{size[1]:g}"' if size else ""
    vb = " ".join(f"{v:g}" for v in view_box)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}"{dims} role="img" aria-label="{title}">'
            f"<title>{title}</title>{style(c, dark)}{body}</svg>\n")


class Text:
    """Shapes a string with HarfBuzz (kerning) and turns it into SVG outlines."""

    def __init__(self, path):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.cap = self.tt["OS/2"].sCapHeight
        self.hbfont = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def run(self, text, size, x, y, split=None):
        """Outlines of text at font size `size`, baseline at (x, y).
        Returns (paths, width); with `split`, paths is (before, after) at that character index."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {"kern": True, "liga": True})
        s = size / self.upm
        parts, pen_x = ([], []), 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
            gx, gy = x + (pen_x + pos.x_offset) * s, y - pos.y_offset * s
            self.glyphs[self.order[info.codepoint]].draw(TransformPen(pen, (s, 0, 0, -s, gx, gy)))
            parts[1 if split is not None and info.cluster >= split else 0].append(pen.getCommands())
            pen_x += pos.x_advance
        width = pen_x * s
        if split is None:
            return " ".join(parts[0]), width
        return (" ".join(parts[0]), " ".join(parts[1])), width


def wordmark(font, size, x, y):
    (brew, pi), width = font.run("BrewberryPi", size, x, y, split=len("Brewberry"))
    return f'<path class="t" d="{brew}"/><path class="p" d="{pi}"/>', width


def fetch_font(name):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(FONT_URL.format(name), path)
    return path


def render(jobs):
    """Rasterise SVG files with headless Chromium: jobs are (svg path, png path, width, height)."""
    payload = [dict(svg=base64.b64encode(Path(s).read_bytes()).decode(), png=str(p), w=w, h=h) for s, p, w, h in jobs]
    script = """
const { chromium } = require('playwright');
(async () => {
  const jobs = JSON.parse(require('fs').readFileSync(0, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const j of jobs) {
    await page.setViewportSize({ width: j.w, height: j.h });
    await page.setContent(`<style>html,body{margin:0;background:transparent}</style>` +
      `<img src="data:image/svg+xml;base64,${j.svg}" width="${j.w}" height="${j.h}" style="display:block">`);
    await page.waitForFunction(() => document.images[0].complete);
    await page.screenshot({ path: j.png, omitBackground: true, clip: { x: 0, y: 0, width: j.w, height: j.h } });
  }
  await browser.close();
})();
"""
    subprocess.run(["node", "-e", script], input=json.dumps(payload).encode(), check=True)


def main():
    bold = Text(fetch_font("ZillaSlab-Bold.ttf"))
    medium = Text(fetch_font("ZillaSlab-Medium.ttf"))
    out = {}

    # Marks: 64 × 64 grid, transparent background.
    box = (0, 0, 64, 64)
    out["mark.svg"] = svg(box, mark_full("k"), "BrewberryPi", LIGHT)
    out["mark-dark.svg"] = svg(box, mark_full("k"), "BrewberryPi", DARK)
    out["mark-mono.svg"] = svg(box, mark_full("k"), "BrewberryPi", MONO)
    out["mark-small.svg"] = svg(box, mark_small("k"), "BrewberryPi", LIGHT)
    out["mark-small-dark.svg"] = svg(box, mark_small("k"), "BrewberryPi", DARK)
    out["favicon.svg"] = svg(box, mark_small("k"), "BrewberryPi", LIGHT, dark=DARK)

    # Square tiles: reversed (berry background) for avatars, paper background for app icons.
    # The mark's drawn area is centred at (34, 32.75); scale it into the tile.
    def tile(bg, scale):
        tx, ty = 32 - 34 * scale, 32 - 32.75 * scale
        return f'<rect width="64" height="64" fill="{bg}"/><g transform="translate({tx:.2f} {ty:.2f}) scale({scale})">{mark_full("k")}</g>'
    out["mark-reversed.svg"] = svg(box, tile(BERRY, 0.74), "BrewberryPi", REVERSED)
    out["app-icon.svg"] = svg(box, tile(PAPER, 0.78), "BrewberryPi", LIGHT)

    # Horizontal lockup: name at 0.61 × the mark's height, cap height centred on the mark.
    size = 39
    base = 32 + bold.cap * size / bold.upm / 2
    words, width = wordmark(bold, size, 76, base)
    view = (6, 0, 76 + width + 2 - 6, 64)
    for name, c in (("logo.svg", LIGHT), ("logo-dark.svg", DARK), ("logo-mono.svg", MONO)):
        out[name] = svg(view, mark_full("k") + words, "BrewberryPi", c)

    # Stacked lockup: mark above the name.
    size = 24
    _, width = bold.run("BrewberryPi", size, 0, 0)
    w = max(64, width) + 8
    words, _ = wordmark(bold, size, (w - width) / 2, 64 + 6 + bold.cap * size / bold.upm)
    mark = f'<g transform="translate({(w - 64) / 2:.2f} 0)">{mark_full("k")}</g>'
    for name, c in (("logo-stacked.svg", LIGHT), ("logo-stacked-dark.svg", DARK)):
        out[name] = svg((0, 0, w, 94), mark + words, "BrewberryPi", c)

    # GitHub social preview, 1280 × 640.
    scale = 300 / 64
    words, wname = wordmark(bold, 112, 470, 300)
    line1, w1 = medium.run(TAGLINE[0], 38, 474, 372)
    line2, w2 = medium.run(TAGLINE[1], 38, 474, 420)
    assert 470 + max(wname, w1, w2) < 1200, "social preview text too wide"
    out["social-preview.svg"] = svg(
        (0, 0, 1280, 640),
        f'<rect width="1280" height="640" fill="{PAPER}"/>'
        f'<g transform="translate(110 165) scale({scale:.4f})">{mark_full("k")}</g>{words}'
        f'<path fill="#6b5a61" d="{line1} {line2}"/>',
        "BrewberryPi: Raspberry Pi controller for a home-brewing mash kettle", LIGHT)

    for name, text in out.items():
        (BRAND / name).write_text(text)

    # Raster files.
    tmp = CACHE / "png"
    tmp.mkdir(exist_ok=True)
    render([
        (BRAND / "favicon.svg", tmp / "fav16.png", 16, 16),
        (BRAND / "favicon.svg", tmp / "fav32.png", 32, 32),
        (BRAND / "favicon.svg", tmp / "fav48.png", 48, 48),
        (BRAND / "app-icon.svg", BRAND / "apple-touch-icon.png", 180, 180),
        (BRAND / "app-icon.svg", BRAND / "icon-192.png", 192, 192),
        (BRAND / "app-icon.svg", BRAND / "icon-512.png", 512, 512),
        (BRAND / "mark-reversed.svg", BRAND / "avatar.png", 500, 500),
        (BRAND / "mark.svg", BRAND / "mark-512.png", 512, 512),
        (BRAND / "social-preview.svg", BRAND / "social-preview.png", 1280, 640),
    ])
    icons = [Image.open(tmp / f"fav{s}.png") for s in (16, 32, 48)]
    icons[2].save(BRAND / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=icons[:2])
    print(f"wrote {len(out)} SVG files and the PNG/ICO set to {BRAND}")

    write_site()


def write_site():
    """Copy the files the website uses into site/, plus self-hosted Latin subsets of Zilla Slab Medium and Bold."""
    site = BRAND.parent / "site"
    for name in SITE_FILES:
        shutil.copyfile(BRAND / name, site / name)
    fonts = site / "fonts"
    fonts.mkdir(exist_ok=True)
    for weight in ("Medium", "Bold"):
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga"]
        font = subset.load_font(str(fetch_font(f"ZillaSlab-{weight}.ttf")), options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=[*range(0x20, 0x7F), *range(0xA0, 0x100), 0x2013, 0x2014, 0x2018, 0x2019,
                                     0x201C, 0x201D, 0x2026, 0x2192, 0x2212])
        subsetter.subset(font)
        subset.save_font(font, str(fonts / f"zilla-slab-{weight.lower()}.woff2"), options)
    shutil.copyfile(fetch_font("OFL.txt"), fonts / "OFL.txt")
    print(f"copied {len(SITE_FILES)} files and the fonts to {site}")


if __name__ == "__main__":
    main()
