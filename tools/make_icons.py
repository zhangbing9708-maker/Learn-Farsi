"""Draw the site icons: assets/favicon.svg and the PNG app icons used by the web manifest.

The mark is the eight-pointed star of the site's header (a girih star from Persian tilework) in tile-white with a
saffron centre, on lapis blue. The PNGs keep the star inside the central 60% so they also work as maskable icons.
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAPIS, WHITE, SAFFRON = "#1f3a8a", "#f6f8fc", "#d9971a"
# the header star, in a 40 x 40 box
STAR = [(20, 2), (25, 10.5), (34.5, 8), (32, 17.5), (40, 20), (32, 22.5), (34.5, 32), (25, 29.5), (20, 38),
        (15, 29.5), (5.5, 32), (8, 22.5), (0, 20), (8, 17.5), (5.5, 8), (15, 10.5)]

SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<rect width="48" height="48" rx="11" fill="{LAPIS}"/>
<g transform="translate(6 6) scale(.9)"><path fill="{WHITE}" d="M20 2l5 8.5 9.5-2.5-2.5 9.5L40 20l-8 2.5 2.5 9.5-9.5-2.5L20 38l-5-8.5-9.5 2.5 2.5-9.5L0 20l8-2.5L5.5 8l9.5 2.5z"/><circle cx="20" cy="20" r="6" fill="{SAFFRON}"/></g>
</svg>
"""


def png(size, path, share=0.6, rounded=False):
    big = size * 4                                   # draw large, then shrink for smooth edges
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if rounded:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=big * 0.22, fill=LAPIS)
    else:
        d.rectangle([0, 0, big, big], fill=LAPIS)
    s = big * share / 40
    off = (big - 40 * s) / 2
    d.polygon([(off + x * s, off + y * s) for x, y in STAR], fill=WHITE)
    r = 6 * s
    c = off + 20 * s
    d.ellipse([c - r, c - r, c + r, c + r], fill=SAFFRON)
    im.resize((size, size), Image.LANCZOS).save(path)


def main():
    a = os.path.join(ROOT, "assets")
    open(os.path.join(a, "favicon.svg"), "w", encoding="utf-8").write(SVG)
    png(192, os.path.join(a, "icon-192.png"))
    png(512, os.path.join(a, "icon-512.png"))
    png(180, os.path.join(a, "apple-touch-icon.png"), share=0.66)
    png(32, os.path.join(a, "favicon-32.png"), share=0.84, rounded=True)
    print("icons -> assets/favicon.svg, icon-192.png, icon-512.png, apple-touch-icon.png, favicon-32.png")


if __name__ == "__main__":
    main()
