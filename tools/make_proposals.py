"""Writes the design proposals site/b.html and site/c.html from site/index.html (proposal A).

Temporary: only for comparing the proposals. Edit index.html, then run this script.
"""

import pathlib
import re

SITE = pathlib.Path(__file__).resolve().parent.parent / "site"

STAMP = '''<span class="stamp" aria-hidden="true">
            <svg viewBox="0 0 120 120"><defs><path id="stamp-ring" d="M60 60m-47 0a47 47 0 1 1 94 0a47 47 0 1 1-94 0"/></defs>
              <text><textPath href="#stamp-ring">BREWBERRYPI · MASH CONTROL · BREW BY RECIPE ·</textPath></text></svg>
            <img src="mark-reversed.svg" alt="" width="58" height="58">
          </span>
          '''

PROPOSALS = {
    "b": {"label": "B · Paper", "theme_color": "#f6efe6",
          "extra": lambda s: s.replace('<div class="live__bar">', STAMP + '<div class="live__bar">', 1)},
    "c": {"label": "C · Instrument", "theme_color": "#f5f5f3", "extra": lambda s: s},
}


def main():
    source = (SITE / "index.html").read_text()
    for key, p in PROPOSALS.items():
        s = source.replace('<html lang="en" class="no-js">', f'<html lang="en" class="no-js theme-{key}" data-theme="light">')
        s = re.sub(r'\n    // The theme chosen.*?\n    try \{.*?\n', "\n", s, flags=re.S)
        s = s.replace('<meta name="theme-color" content="#0f0b0d">', f'<meta name="theme-color" content="{p["theme_color"]}">')
        s = s.replace('<link rel="stylesheet" href="styles.css">',
                      f'<link rel="stylesheet" href="styles.css">\n  <link rel="stylesheet" href="theme-{key}.css">')
        s = re.sub(r'\n        <button class="icon-btn" id="theme-toggle".*?</button>', "", s, flags=re.S)
        s = s.replace(' aria-current="page"', "")
        s = s.replace(f'href="{key}.html">', f'href="{key}.html" aria-current="page">')
        s = p["extra"](s)
        (SITE / f"{key}.html").write_text(s)
        print(f"wrote site/{key}.html")


if __name__ == "__main__":
    main()
