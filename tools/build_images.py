"""Build data/images.json from tools/images.tsv (Wikimedia Commons photos).

Each line of the TSV: key, file name on Commons, mime type, width, height, licence, author.
The site hotlinks Commons thumbnails (800px wide) and shows the author and licence under every photo.
Thumbnail URLs follow Commons' scheme: /thumb/<a>/<ab>/<File>/800px-<File> where <a><b> are the first
hex digits of the MD5 of the file name; SVGs get a ".png" suffix; files narrower than 800px are linked directly.
"""
import hashlib
import json
import os
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTH = 960      # Wikimedia only serves standard thumbnail widths (…, 330, 500, 960, 1280, …)
THUMB = 500
LICENSE_URLS = {
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY 2.5": "https://creativecommons.org/licenses/by/2.5/",
    "CC BY-SA 2.5": "https://creativecommons.org/licenses/by-sa/2.5/",
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY-SA 2.0": "https://creativecommons.org/licenses/by-sa/2.0/",
    "CC0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "GFDL": "https://www.gnu.org/licenses/fdl-1.3.html",
    "Public domain": "https://commons.wikimedia.org/wiki/Help:Public_domain",
    "No restrictions": "https://commons.wikimedia.org/wiki/Commons:Flickr_files#No_known_copyright_restrictions",
}


def urls(file, mime, w, width=WIDTH):
    name = file.replace(" ", "_")
    md5 = hashlib.md5(name.encode("utf-8")).hexdigest()
    q = urllib.parse.quote(name, safe="()',!*-._~")
    base = f"https://upload.wikimedia.org/wikipedia/commons/{md5[0]}/{md5[:2]}/{q}"
    page = "https://commons.wikimedia.org/wiki/File:" + q
    if mime == "image/svg+xml":
        return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{md5[0]}/{md5[:2]}/{q}/{width}px-{q}.png", page
    if w > width:
        return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{md5[0]}/{md5[:2]}/{q}/{width}px-{q}", page
    return base, page


def main():
    out = {}
    captions = {}
    cap_path = os.path.join(ROOT, "tools", "image_captions.json")
    if os.path.exists(cap_path):
        captions = json.load(open(cap_path, encoding="utf-8"))
    for line in open(os.path.join(ROOT, "tools", "images.tsv"), encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        key, file, mime, w, h, lic, artist = (line.split("\t") + [""] * 7)[:7]
        url, page = urls(file, mime, int(w))
        th, _ = urls(file, mime, int(w), THUMB)
        out[key] = {
            "url": url, "thumb": th, "page": page, "w": int(w), "h": int(h),
            "artist": artist.strip() or "Wikimedia Commons", "license": lic,
            "licenseUrl": LICENSE_URLS.get(lic, "https://commons.wikimedia.org/wiki/Commons:Licensing"),
            "caption": captions.get(key, key.replace("-", " ").title()),
        }
    path = os.path.join(ROOT, "data", "images.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out)} images -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
