"""Build the Learn Farsi website from content/ and data/.

usage: python3 tools/build_site.py

Writes static HTML pages next to the sources (GitHub Pages serves the repository root):
  index.html, course/, alphabet/, stories/, culture/, poetry/, news/, phrasebook/, idioms/, grammar/,
  verbs/, dictionary/, numbers/, flashcards/, search/, about/, 404.html, sitemap.xml
and the generated data files assets/search.json, assets/decks.json, assets/concordance.json.
assets/style.css and assets/app.js are hand-written and only referenced here.
Every page works without JavaScript for reading; audio, exercises, flashcards and tools need it.
"""
import glob
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
SITE_URL = "https://zhangbing9708-maker.github.io/Learn-Farsi/"
REPO_URL = "https://github.com/zhangbing9708-maker/Learn-Farsi"
_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_config.json")
SITE_CONFIG = json.load(open(_CFG_PATH, encoding="utf-8")) if os.path.exists(_CFG_PATH) else {}
GOOGLE_CLIENT_ID = (os.environ.get("LF_GOOGLE_CLIENT_ID") or SITE_CONFIG.get("google_client_id") or "").strip()
PERSIAN = re.compile("[؀-ۿ]")
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load(path, default=None):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_dir(folder):
    out = {}
    for p in sorted(glob.glob(os.path.join(CONTENT, folder, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print("skipping invalid", p, e)
            continue
        out[d.get("id") or os.path.basename(p)[:-5]] = d
    return out


COURSE = load("content/course.json", {})
LESSONS = load_dir("lessons")
STORIES = load_dir("stories")
ARTICLES = load_dir("culture")
POEMS = load_dir("poems")
NEWS = load("content/news.json", {"stories": []})
PHRASEBOOK = load("content/phrasebook.json")
IDIOMS = load("content/idioms.json")
VERBS = load("content/verbs.json")
IMAGES = load("data/images.json", {})
ALPHABET = load("data/alphabets.json", {}).get("fa", {})
GRAMMAR = load("data/grammar.json")
NUMBERS = load("data/numbers.json")
DICT = load("data/dict.json", {"entries": []})

LEVEL_NAMES = {"script": "The script", "A1": "Beginner (A1)", "A2": "Elementary (A2)", "B1": "Intermediate (B1)",
               "B2": "Upper intermediate (B2)", "C1": "Advanced (C1)"}
TOPICS = [
    ("history", "History", "تاریخ", "tārikh", "persepolis", "Five thousand years, from Elam and Cyrus to the present day."),
    ("places", "Places", "جاهای دیدنی", "jāhā-ye didani", "naqsh-e-jahan", "Cities, villages, deserts, forests and islands – and what to say when you get there."),
    ("food", "Food", "غذا", "ghazā", "ghormeh-sabzi", "Stews, rice, bread, tea and sweets, with recipes and the words of the Iranian table."),
    ("festivals", "Festivals", "جشن‌ها", "jashn-hā", "nowruz", "Nowruz, Yalda, Chaharshanbe Suri and the rest of the year's celebrations."),
    ("arts", "Arts", "هنر", "honar", "persian-miniature", "Carpets, miniatures, calligraphy, architecture, music and cinema."),
    ("people", "People", "چهره‌ها", "chehre-hā", "saadi", "Poets, scientists, rulers and artists who shaped Iran and the world."),
    ("language", "Language", "زبان", "zabān", "persian-calligraphy", "Where Persian comes from, who speaks it, and how it works."),
    ("life", "Everyday life", "زندگی روزمره", "zendegi-ye ruzmarre", "tajrish-bazaar", "Family, school, the bazaar, transport, sport and tea houses."),
]
TOPIC = {t[0]: t for t in TOPICS}
NAV = [("course", "Course"), ("alphabet", "Alphabet"), ("stories", "Stories"), ("culture", "Culture"),
       ("poetry", "Poetry"), ("news", "News")]
TOOLS = [("dictionary", "Dictionary", "5,000 most common words with audio"),
         ("phrasebook", "Phrasebook", "Everyday phrases, formal and spoken"),
         ("verbs", "Verbs", "Conjugate any verb in every tense"),
         ("grammar", "Grammar", "Sentence patterns and every grammar point"),
         ("idioms", "Proverbs and idioms", "The sayings Iranians really use"),
         ("numbers", "Numbers and dates", "Write any number; today's Persian date"),
         ("flashcards", "My flashcards", "Review your saved words"),
         ("voice", "Friend's voice", "Record a Persian speaker; hear them on every page"),
         ("journey", "My journey", "Your carpet, caravan route, badges and streak")]

ASSET_VER = ""
SEARCH = []      # search index entries
DECKS = {}       # deck id -> {t, u, w: [[fa, r, en, a]]}
SENTS = []       # every sentence with its page, for the dictionary concordance
PAGES = []       # every page url for the sitemap


# ---------------------------------------------------------------------------------------------- text
def esc(s):
    return html.escape(str(s or ""), quote=True)


def fa_num(n):
    return str(n).translate(FA_DIGITS)


INLINE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]|]*))?(?:\|([^\]]*))?\]\]")


def ifa(fa, r="", g=""):
    out = f'<span class="ifa"><bdi class="ifa-f" lang="fa" dir="rtl">{esc(fa)}</bdi>'
    if r:
        out += f' <span class="ifa-r">{esc(r)}</span>'
    if g:
        out += f' <span class="ifa-g">{esc(g)}</span>'
    return out + "</span>"


def inl(text):
    """Inline markdown: [[fa|r|gloss]], **bold**, *italic*, [link](url), `code`."""
    text = str(text or "")
    holders = []

    def hold(m):
        holders.append(ifa(m.group(1).strip(), (m.group(2) or "").strip(), (m.group(3) or "").strip()))
        return f"\x00{len(holders) - 1}\x00"
    text = INLINE.sub(hold, text)
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    # bare Persian runs in English prose get the right direction
    def wrap_fa(m):
        return f'<bdi lang="fa" dir="rtl">{m.group(0)}</bdi>'
    parts = re.split(r"(\x00\d+\x00|<[^>]+>)", text)
    for i, p in enumerate(parts):
        if p and not p.startswith("<") and not p.startswith("\x00"):
            parts[i] = re.sub(r"[؀-ۿ][؀-ۿ‌\s،؟]*[؀-ۿ]|[؀-ۿ]", wrap_fa, p)
    text = "".join(parts)
    return re.sub(r"\x00(\d+)\x00", lambda m: holders[int(m.group(1))], text)


def md(text, h="h4"):
    """Block markdown: paragraphs, - lists, 1. lists, ## headings, > quotes."""
    out, para, items, kind = [], [], [], None

    def flush_para():
        if para:
            out.append("<p>" + inl(" ".join(para)) + "</p>")
            para.clear()

    def flush_list():
        nonlocal kind
        if items:
            tag = "ol" if kind == "ol" else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inl(i)}</li>" for i in items) + f"</{tag}>")
            items.clear()
        kind = None
    for line in str(text or "").split("\n"):
        s = line.strip()
        if not s:
            flush_para()
            flush_list()
            continue
        m_ul = re.match(r"^[-•]\s+(.*)", s)
        m_ol = re.match(r"^\d+[.)]\s+(.*)", s)
        if m_ul or m_ol:
            flush_para()
            k = "ul" if m_ul else "ol"
            if kind and kind != k:
                flush_list()
            kind = k
            items.append((m_ul or m_ol).group(1))
            continue
        if s.startswith("#"):
            flush_para()
            flush_list()
            level = len(s) - len(s.lstrip("#"))
            tag = h if level <= 2 else "h5"
            out.append(f"<{tag}>{inl(s.lstrip('#').strip())}</{tag}>")
            continue
        if s.startswith(">"):
            flush_para()
            flush_list()
            out.append(f"<blockquote>{inl(s.lstrip('>').strip())}</blockquote>")
            continue
        if items:
            items[-1] += " " + s
        else:
            para.append(s)
    flush_para()
    flush_list()
    return "\n".join(out)


def cell(c):
    c = "" if c is None else str(c)
    if "[[" in c:
        return inl(c)
    if PERSIAN.search(c) and not re.search("[A-Za-z]", c):
        return f'<bdi lang="fa" dir="rtl">{esc(c)}</bdi>'
    return inl(c)


def slug_title(lid):
    words = lid.split("-")[2:] if re.match(r"^(script|a1|a2|b1|b2|c1)-\d\d-", lid) else lid.split("-")
    t = " ".join(words)
    return t[:1].upper() + t[1:]


def clip(s, n):
    s = plain(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:–-")
    return cut + "…"


def plain(s):
    return re.sub(r"\s+", " ", INLINE.sub(lambda m: m.group(1), str(s or "")).replace("**", "").replace("*", "")).strip()


# ---------------------------------------------------------------------------------------------- pieces
ICON_SAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path class="w" d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12"/></svg>'


def say(a, label="Listen"):
    if not a:
        return ""
    return f'<button class="say" type="button" data-a="{esc(a)}" aria-label="{esc(label)}">{ICON_SAY}</button>'


def card_json(fa, r, en, a, src):
    return esc(json.dumps({"fa": fa, "r": r, "en": en, "a": a or "", "src": src}, ensure_ascii=False))


def save_btn(fa, r, en, a, src):
    return (f'<button class="save" type="button" data-card="{card_json(fa, r, en, a, src)}" '
            f'aria-label="Save {esc(en)} to flashcards" title="Save to flashcards">+</button>')


def line(s, ctx, cls="ln", who=None):
    """A Persian sentence with transliteration, English and audio."""
    fa = s.get("fa", "")
    if not fa:
        return ""
    SENTS.append((fa, s.get("en", ""), s.get("a", ""), ctx["url"], ctx["title"]))
    parts = [f'<div class="{cls}"' + (f' data-a="{esc(s["a"])}"' if s.get("a") else "") + ">"]
    if who:
        parts.append(f'<span class="who">{esc(who)}</span>')
    parts.append(say(s.get("a")))
    parts.append('<div class="ln-b">')
    parts.append(f'<p class="fa" lang="fa" dir="rtl">{esc(fa)}</p>')
    if s.get("r"):
        parts.append(f'<p class="tr">{esc(s["r"])}</p>')
    if s.get("en"):
        parts.append(f'<p class="en">{inl(s["en"])}</p>')
    if s.get("lit"):
        parts.append(f'<p class="lit">Literally: {inl(s["lit"])}</p>')
    if s.get("col"):
        parts.append(f'<p class="col"><span class="col-tag">Spoken</span> <bdi lang="fa" dir="rtl">{esc(s["col"])}</bdi> '
                     f'<span class="tr">{esc(s.get("colR", ""))}</span> {say(s.get("colA"), "Listen to the spoken form")}</p>')
    if s.get("note"):
        parts.append(f'<p class="note">{inl(s["note"])}</p>')
    parts.append("</div></div>")
    return "".join(parts)


def vocab_list(items, ctx, deck_id=None):
    out = ['<ul class="vocab">']
    words = []
    for it in items:
        fa, r, en = it.get("fa", ""), it.get("r", ""), it.get("en", "")
        if not fa:
            continue
        words.append([fa, r, en, it.get("a", "")])
        SEARCH.append({"t": "word", "ti": en, "fa": fa, "r": r, "u": ctx["url"], "s": ctx["title"]})
        out.append('<li class="vw">')
        out.append(say(it.get("a"), f"Listen: {fa}"))
        out.append('<div class="vw-b"><p class="vw-top">'
                   f'<span class="vw-fa" lang="fa" dir="rtl">{esc(fa)}</span> '
                   f'<span class="vw-r tr">{esc(r)}</span></p>'
                   f'<p class="vw-en">{inl(en)}' + (f' <span class="pos">{esc(it["pos"])}</span>' if it.get("pos") else "") + "</p>")
        if it.get("note"):
            out.append(f'<p class="note">{inl(it["note"])}</p>')
        if it.get("lit"):
            out.append(f'<p class="note">Literally: {inl(it["lit"])}</p>')
        if it.get("col"):
            out.append(f'<p class="col"><span class="col-tag">Spoken</span> <bdi lang="fa" dir="rtl">{esc(it["col"])}</bdi> <span class="tr">{esc(it.get("colR", ""))}</span></p>')
        if isinstance(it.get("ex"), dict) and it["ex"].get("fa"):
            out.append(line(it["ex"], ctx, cls="ln ln-ex"))
        out.append("</div>")
        out.append(save_btn(fa, r, en, it.get("a", ""), ctx["title"]))
        out.append("</li>")
    out.append("</ul>")
    if deck_id and words:
        d = DECKS.setdefault(deck_id, {"t": ctx["title"], "u": ctx["url"], "w": []})
        seen = {w[0] for w in d["w"]}
        d["w"].extend(w for w in words if w[0] not in seen)
    if words:
        out.append(f'<p class="save-all"><button class="btn-quiet" type="button" data-save-all>Save all {len(words)} words to flashcards</button></p>')
    return "".join(out)


def figure(key, cls="ph", caption=None, eager=False):
    im = IMAGES.get(key or "")
    if not im:
        return ""
    cap = caption or im.get("caption") or ""
    w, h = im.get("w") or 800, im.get("h") or 600
    dw = min(960, w)
    dh = round(h * dw / w)
    load_attr = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<figure class="{cls}"><img src="{esc(im["url"])}" alt="{esc(cap)}" width="{dw}" height="{dh}" {load_attr} decoding="async">'
            f'<figcaption><span class="cap">{esc(cap)}</span> <span class="credit">Photo: <a href="{esc(im["page"])}">{esc(im["artist"])}</a>, '
            f'<a href="{esc(im["licenseUrl"])}">{esc(im["license"])}</a></span></figcaption></figure>')


def img_url(key):
    im = IMAGES.get(key or "")
    return im["url"] if im else ""


def thumb(key, alt=""):
    im = IMAGES.get(key or "")
    if not im:
        return '<span class="thumb thumb-none" aria-hidden="true"></span>'
    return f'<img class="thumb" src="{esc(im.get("thumb") or im["url"])}" alt="{esc(alt)}" loading="lazy" decoding="async">'


def study_bar(has_col=False, has_lines=True):
    if not has_lines:
        return ""
    b = ['<div class="study-bar" role="toolbar" aria-label="Show or hide">',
         '<span class="sb-label">Show</span>',
         '<button type="button" data-toggle="tr" aria-pressed="true">Transliteration</button>',
         '<button type="button" data-toggle="en" aria-pressed="true">English</button>']
    if has_col:
        b.append('<button type="button" data-toggle="col" aria-pressed="true">Spoken forms</button>')
    b.append('<button type="button" class="play-all" data-playall>Play all</button>'
             '<button type="button" class="save-off" data-offline hidden title="Keep this page and its recordings on this device">Save offline</button>'
             '<button type="button" class="voice-btn" data-voice-toggle aria-pressed="false" title="Record a Persian-speaking friend reading these lines, and hear their voice">Friend\'s voice</button>'
             '<button type="button" class="print-btn" data-print title="Print on A4 paper, with the exercises as a worksheet and an answer key">Print</button></div>')
    return "".join(b)


def has_key(x, key):
    if isinstance(x, dict):
        return key in x or any(has_key(v, key) for v in x.values())
    if isinstance(x, list):
        return any(has_key(v, key) for v in x)
    return False


# ---------------------------------------------------------------------------------------------- exercises
def answer_r(answer, vocab):
    for it in vocab:
        if it.get("fa") == answer:
            return it.get("r", "")
    return ""


def exercise(b, ctx, vocab):
    kind = b.get("kind")
    items = []
    for it in b.get("items", []):
        if kind == "mcq":
            items.append({"q": inl(it.get("q", "")), "o": it.get("options", []), "ans": it.get("answer", 0),
                          "x": inl(it.get("explain", "")) if it.get("explain") else ""})
        elif kind == "fill":
            items.append({"fa": it.get("fa", ""), "r": it.get("r", ""), "en": it.get("en", ""), "ans": it.get("answer", ""),
                          "ansR": answer_r(it.get("answer", ""), vocab), "hint": it.get("hint", "")})
        elif kind == "listen":
            items.append({"fa": it.get("fa", ""), "r": it.get("r", ""), "en": it.get("en", ""), "a": it.get("a", ""),
                          "o": it.get("options", []), "ans": it.get("answer", 0)})
        else:
            items.append({"fa": it.get("fa", ""), "r": it.get("r", ""), "en": it.get("en", ""), "a": it.get("a", "")})
            if kind in ("translate", "order"):
                SENTS.append((it.get("fa", ""), it.get("en", ""), it.get("a", ""), ctx["url"], ctx["title"]))
    data = json.dumps({"kind": kind, "items": items}, ensure_ascii=False).replace("</", "<\\/")
    hints = {"mcq": "Choose the right answer.", "fill": "Type the missing word in Persian – use the keyboard button if you need Persian letters.",
             "translate": "Say or write it in Persian, then check.", "match": "Tap a Persian word, then its meaning.",
             "order": "Tap the words in the right order.", "listen": "Listen, then choose."}
    return (f'<div class="ex" data-kind="{esc(kind)}"><p class="ex-hint">{hints.get(kind, "")}</p>'
            f'<div class="ex-body"><noscript>This exercise needs JavaScript.</noscript></div>'
            f'<script type="application/json" class="ex-data">{data}</script></div>')


def questions(qs, ctx):
    if not qs:
        return ""
    return exercise({"kind": "mcq", "items": qs}, ctx, [])


# ---------------------------------------------------------------------------------------------- page shell
def rel(depth):
    return "../" * depth


def page(path, title, body, desc="", image=None, section="", depth=None, lang_note=False, extra_head=""):
    if depth is None:
        depth = path.count("/")
    R = rel(depth)
    nav = []
    for key, label in NAV:
        cur = ' aria-current="page"' if section == key else ""
        nav.append(f'<li><a href="{R}{key}/index.html"{cur}>{label}</a></li>')
    tools_cur = section in [t[0] for t in TOOLS]
    tools = "".join(f'<li><a href="{R}{k}/index.html"' + (' aria-current="page"' if section == k else "") + f'>{lbl}</a></li>'
                    for k, lbl, _ in TOOLS)
    og = f'<meta property="og:image" content="{esc(img_url(image))}">' if image and img_url(image) else ""
    full_title = f"{title} – Learn Farsi" if title != "Learn Farsi" else "Learn Farsi – Persian from the alphabet to Hafez"
    PAGES.append(path)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc or 'A free course in Persian (Farsi) from the alphabet to advanced, with audio, stories, culture and tools.')}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
{og}
<meta name="theme-color" content="#1f3a8a">
<link rel="icon" href="{R}assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{R}assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{R}assets/apple-touch-icon.png">
<link rel="manifest" href="{R}manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lalezar&amp;family=Literata:ital,opsz,wght@0,7..72,400..700;1,7..72,400..600&amp;family=Vazirmatn:wght@400;500;700&amp;display=swap">
<link rel="stylesheet" href="{R}assets/style.css?v={ASSET_VER}">
{extra_head}
</head>
<body data-root="{R}" data-section="{esc(section)}"{(' data-gcid="' + esc(GOOGLE_CLIENT_ID) + '"') if GOOGLE_CLIENT_ID else ''}>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
<div class="band" aria-hidden="true"></div>
<nav class="top" aria-label="Main">
<a class="brand" href="{R}index.html"><svg class="star" viewBox="0 0 40 40" aria-hidden="true"><path d="M20 2l5 8.5 9.5-2.5-2.5 9.5L40 20l-8 2.5 2.5 9.5-9.5-2.5L20 38l-5-8.5-9.5 2.5 2.5-9.5L0 20l8-2.5L5.5 8l9.5 2.5z"/><circle cx="20" cy="20" r="6"/></svg><span class="brand-en">Learn Farsi</span><span class="brand-fa" lang="fa" dir="rtl">فارسی</span></a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="menu">Menu</button>
<div class="menu" id="menu">
<ul class="nav">{"".join(nav)}
<li class="tools"><details{" open" if False else ""}><summary{' aria-current="page"' if tools_cur else ""}>Tools</summary><ul>{tools}</ul></details></li>
</ul>
<form class="search" action="{R}search/index.html" role="search"><input type="search" name="q" placeholder="Search" aria-label="Search lessons, words and stories"></form>
</div>
</nav>
</header>
<main id="main">
{body}
</main>
<footer class="site">
<div class="foot">
<p class="foot-fa" lang="fa" dir="rtl">«توانا بود هر که دانا بود»</p><p class="foot-fa-en">“Whoever has knowledge has power.” – Ferdowsi</p>
<p>Learn Farsi is a free, open course in Persian. <a href="{R}about/index.html">About, sources and credits</a> · <a href="{REPO_URL}">Source on GitHub</a> · <a href="{R}about/photos.html">Photo credits</a></p>
<p class="small">Text CC BY-SA 4.0, code MIT. Photos from Wikimedia Commons under their own licences, credited under each picture. Audio made with an open-source Persian voice.</p>
</div>
</footer>
<script src="{R}assets/app.js?v={ASSET_VER}" defer></script>
<script src="{R}assets/voice.js?v={ASSET_VER}" defer></script>
<script src="{R}assets/journey.js?v={ASSET_VER}" defer></script>
</body>
</html>
"""
    out = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)


def crumbs(R, items):
    out = []
    for label, href in items:
        out.append(f'<a href="{href}">{esc(label)}</a>' if href else f"<span>{esc(label)}</span>")
    return '<p class="crumbs">' + ' <span aria-hidden="true">/</span> '.join(out) + "</p>"


def head_block(title, fa, r, a=None, intro="", kicker=""):
    return (f'<header class="page-head">{kicker}'
            f'<h1><span class="h-fa" lang="fa" dir="rtl">{esc(fa)}</span><span class="h-en">{esc(title)}</span></h1>'
            + (f'<p class="h-r">{esc(r)} {say(a, "Listen to the title")}</p>' if r else "")
            + (f'<div class="lede">{md(intro)}</div>' if intro else "") + "</header>")


# ---------------------------------------------------------------------------------------------- lessons
def course_order():
    order = []
    for lv in COURSE.get("levels", []):
        for lid in lv.get("lessons", []):
            order.append((lv, lid))
    return order


def level_of(lid):
    for lv in COURSE.get("levels", []):
        if lid in lv.get("lessons", []):
            return lv
    return None


def render_letters(b):
    cells = {c["g"]: c for s in ALPHABET.get("sections", []) for c in s.get("cells", []) if c}
    out = ['<div class="letters">']
    for g in b.get("letters", []):
        c = cells.get(g)
        if not c:
            out.append(f'<div class="letter"><p class="lt-g" lang="fa">{esc(g)}</p></div>')
            continue
        ex = c.get("ex") or {}
        forms = c.get("forms") or []
        out.append('<div class="letter">'
                   f'<p class="lt-g" lang="fa" dir="rtl">{esc(c["g"])}</p>'
                   f'<p class="lt-name">{esc(c.get("name", ""))} <span class="lt-sound">{esc(c.get("r", ""))}</span></p>')
        if forms:
            labels = ["alone", "start", "middle", "end"]
            out.append('<ol class="lt-forms">' + "".join(
                f'<li><span lang="fa" dir="rtl">{esc(f)}</span><small>{labels[i]}</small></li>' for i, f in enumerate(forms[:4])) + "</ol>")
        if ex.get("w"):
            out.append(f'<p class="lt-ex">{say(ex.get("a"), "Listen: " + ex.get("w", ""))}<bdi lang="fa" dir="rtl">{esc(ex["w"])}</bdi> '
                       f'<span class="tr">{esc(ex.get("r", ""))}</span> <span class="en">{esc(ex.get("m", ""))}</span></p>')
        if c.get("joins") is False:
            out.append('<p class="lt-note">does not join the next letter</p>')
        out.append("</div>")
    out.append("</div>")
    return "".join(out)


def render_block(b, i, ctx, vocab, deck_id):
    t = b.get("type")
    title = b.get("title") or {"vocab": "Words", "tips": "Tips", "culture": "Culture", "reading": "Reading",
                               "dialogue": "Dialogue", "exercise": "Practice", "grammar": "Grammar", "letters": "Letters"}.get(t, "")
    sid = f"s{i + 1}"
    h = f'<h2 id="{sid}">{inl(title)}</h2>' if title else ""
    cls = f"blk blk-{t}"
    if t == "text":
        return f'<section class="{cls}">{h}{md(b.get("md"))}{figure(b.get("image"))}</section>'
    if t == "image":
        return f'<section class="{cls}">{figure(b.get("image"), caption=b.get("caption"))}</section>'
    if t == "vocab":
        return f'<section class="{cls}">{h}{vocab_list(b.get("items", []), ctx, deck_id)}</section>'
    if t == "dialogue":
        whos = []
        for ln in b.get("lines", []):
            if ln.get("who") not in whos:
                whos.append(ln.get("who"))
        lines = "".join(line(ln, ctx, cls="ln dl dl-" + ("a" if whos.index(ln.get("who")) % 2 == 0 else "b"), who=ln.get("who"))
                        for ln in b.get("lines", []))
        ctxp = f'<p class="context">{inl(b["context"])}</p>' if b.get("context") else ""
        return f'<section class="{cls}">{h}{ctxp}<div class="lines">{lines}</div></section>'
    if t == "grammar":
        tb = ""
        if isinstance(b.get("table"), dict) and b["table"].get("rows"):
            head = b["table"].get("head") or []
            tb = ('<div class="tbl-wrap"><table>' + (("<thead><tr>" + "".join(f"<th>{cell(x)}</th>" for x in head) + "</tr></thead>") if head else "")
                  + "<tbody>" + "".join("<tr>" + "".join(f"<td>{cell(x)}</td>" for x in row) + "</tr>" for row in b["table"]["rows"])
                  + "</tbody></table></div>")
        exs = "".join(line(e, ctx) for e in b.get("examples") or [])
        return f'<section class="{cls}">{h}{md(b.get("md"))}{tb}' + (f'<div class="lines">{exs}</div>' if exs else "") + "</section>"
    if t == "reading":
        intro = f'<p class="context">{inl(b["intro"])}</p>' if b.get("intro") else ""
        sents = "".join(line(s, ctx) for s in b.get("sentences", []))
        return f'<section class="{cls}">{h}{intro}<div class="lines reading">{sents}</div>{questions(b.get("questions"), ctx)}</section>'
    if t == "culture":
        return f'<section class="{cls}">{h}<div class="culture-box">{figure(b.get("image"))}{md(b.get("md"))}</div></section>'
    if t == "tips":
        return f'<section class="{cls}">{h}<ul class="tips">' + "".join(f"<li>{inl(x)}</li>" for x in b.get("items", [])) + "</ul></section>"
    if t == "letters":
        return f'<section class="{cls}">{h}{md(b.get("md"))}{render_letters(b)}</section>'
    if t == "exercise":
        return f'<section class="{cls}">{h}{exercise(b, ctx, vocab)}</section>'
    return ""


def build_lessons():
    order = [(lv, lid) for lv, lid in course_order() if lid in LESSONS]
    for idx, (lv, lid) in enumerate(order):
        L = LESSONS[lid]
        url = f"course/{lid}.html"
        ctx = {"url": url, "title": f'{L.get("title")}'}
        vocab = [it for b in L.get("sections", []) if b.get("type") == "vocab" for it in b.get("items", [])]
        R = "../"
        blocks = [render_block(b, i, ctx, vocab, lid) for i, b in enumerate(L.get("sections", []))]
        toc = "".join(f'<li><a href="#s{i + 1}">{esc(plain(b.get("title") or b.get("type", "").title()))}</a></li>'
                      for i, b in enumerate(L.get("sections", [])) if b.get("type") != "image")
        lvname = lv.get("name") or LEVEL_NAMES.get(L.get("level"), "")
        kicker = crumbs(R, [("Course", "index.html"), (lvname, f'index.html#{lv["id"]}'), (f'Lesson {L.get("n", "")}', None)])
        goals = ""
        if L.get("goals"):
            goals = '<div class="goals"><p>In this lesson you will learn to</p><ul>' + "".join(f"<li>{inl(g)}</li>" for g in L["goals"]) + "</ul></div>"
        prev_l = order[idx - 1][1] if idx > 0 else None
        next_l = order[idx + 1][1] if idx + 1 < len(order) else None
        pn = '<nav class="prevnext" aria-label="Lessons">'
        if prev_l:
            pn += f'<a class="prev" href="{prev_l}.html"><small>Previous</small>{esc(LESSONS[prev_l]["title"])}</a>'
        if next_l:
            pn += f'<a class="next" href="{next_l}.html"><small>Next</small>{esc(LESSONS[next_l]["title"])}</a>'
        pn += "</nav>"
        body = (f'<div class="with-toc"><aside class="toc-side" aria-label="In this lesson"><p>In this lesson</p><ol>{toc}</ol></aside>'
                f'<article class="lesson" data-lesson="{esc(lid)}">'
                + head_block(L.get("title", ""), L.get("titleFa", ""), L.get("titleR", ""), L.get("titleA"), L.get("intro", ""), kicker)
                + goals + figure(L.get("image"), "ph ph-hero", eager=True)
                + study_bar(has_key(L, "col")) + "".join(blocks)
                + f'<div class="lesson-end"><button class="done-btn" type="button" data-done="{esc(lid)}">Mark this lesson as done</button></div>'
                + pn + "</article></div>")
        page(url, L.get("title", lid), body, desc=clip(L.get("intro", ""), 200), image=L.get("image"), section="course")
        SEARCH.append({"t": "lesson", "ti": L.get("title"), "fa": L.get("titleFa", ""), "r": L.get("titleR", ""), "u": url,
                       "s": f'{lvname}, lesson {L.get("n", "")}', "k": " ".join(plain(g) for g in L.get("goals", []))})


def build_course_index():
    secs = []
    total = 0
    for lv in COURSE.get("levels", []):
        rows = []
        n_written = 0
        for i, lid in enumerate(lv.get("lessons", [])):
            L = LESSONS.get(lid)
            n = L.get("n", i + 1) if L else i + 1
            if L:
                n_written += 1
                rows.append(f'<li class="toc-row"><a href="{lid}.html"><span class="toc-n">{n}</span><span class="toc-t">{esc(L["title"])}</span>'
                            f'<span class="toc-dots" aria-hidden="true"></span><span class="toc-fa" lang="fa" dir="rtl">{esc(L.get("titleFa", ""))}</span></a>'
                            f'<span class="toc-done" data-done-mark="{esc(lid)}" aria-hidden="true"></span></li>')
            else:
                rows.append(f'<li class="toc-row toc-soon"><span class="toc-a"><span class="toc-n">{n}</span><span class="toc-t">{esc(slug_title(lid))}</span>'
                            f'<span class="toc-dots" aria-hidden="true"></span><span class="toc-soon-tag">being written</span></span></li>')
        total += n_written
        secs.append(f'<section class="level" id="{lv["id"]}"><header class="level-head"><p class="lv-code">{esc(lv["id"].upper() if lv["id"] != "script" else "Start")}</p>'
                    f'<h2>{esc(lv["name"])} <span class="lv-fa" lang="fa" dir="rtl">{esc(lv.get("fa", ""))}</span></h2>'
                    f'<p>{esc(lv.get("blurb", ""))}</p><p class="lv-prog" data-level-lessons="{esc(",".join(l for l in lv["lessons"] if l in LESSONS))}"></p></header>'
                    f'<ol class="toc">{"".join(rows)}</ol></section>')
    body = ('<div class="narrow">' + head_block("The course", "دوره‌ی آموزشی", "dowre-ye āmuzeshi", None,
            f"Six stages, from your first letter to reading Hafez. Each lesson has a dialogue or reading with recorded audio, the words to learn, "
            f"clear grammar, a note on culture and exercises that check themselves. {total} lessons are ready; the rest are being written. "
            "Tick a lesson off when you finish it and your progress is kept in this browser.")
            + '<p class="resume" data-resume></p>' + "".join(secs) + "</div>")
    page("course/index.html", "The course", body, desc="Persian lessons from the alphabet to advanced.", section="course")


# ---------------------------------------------------------------------------------------------- stories
def build_stories():
    levels = ["A1", "A2", "B1", "B2", "C1"]
    order = [sid for sid in COURSE.get("stories", []) if sid in STORIES] + sorted(s for s in STORIES if s not in COURSE.get("stories", []))
    by_level = {lv: [s for s in order if STORIES[s].get("level") == lv] for lv in levels}
    for sid in order:
        S = STORIES[sid]
        url = f"stories/{sid}.html"
        ctx = {"url": url, "title": S.get("title", sid)}
        paras = "".join('<div class="para">' + "".join(line(s, ctx) for s in p.get("sentences", [])) + "</div>"
                        for p in S.get("paragraphs", []))
        words = sum(len(s.get("fa", "").split()) for p in S.get("paragraphs", []) for s in p.get("sentences", []))
        same = by_level.get(S.get("level"), [])
        i = same.index(sid) if sid in same else -1
        pn = '<nav class="prevnext" aria-label="Stories">'
        if i > 0:
            pn += f'<a class="prev" href="{same[i - 1]}.html"><small>Previous story</small>{esc(STORIES[same[i - 1]]["title"])}</a>'
        if 0 <= i < len(same) - 1:
            pn += f'<a class="next" href="{same[i + 1]}.html"><small>Next story</small>{esc(STORIES[same[i + 1]]["title"])}</a>'
        pn += "</nav>"
        kicker = crumbs("../", [("Stories", "index.html"), (LEVEL_NAMES.get(S.get("level"), ""), f'index.html#{S.get("level", "").lower()}'), (S.get("kind", "").capitalize(), None)])
        body = ('<article class="story narrow">'
                + head_block(S.get("title", ""), S.get("titleFa", ""), S.get("titleR", ""), S.get("titleA"), S.get("intro", ""), kicker)
                + f'<p class="meta">{esc(LEVEL_NAMES.get(S.get("level"), ""))}, {fa_num(words)} <span lang="fa">کلمه</span> ({words} words)</p>'
                + figure(S.get("image"), "ph ph-hero", eager=True)
                + study_bar(has_key(S, "col")) + '<div class="story-tools"><button class="btn-quiet" type="button" data-astext>Read as continuous text</button></div>'
                + f'<div class="story-text">{paras}</div>'
                + (f'<section class="blk"><h2>Words</h2>{vocab_list(S.get("vocab", []), ctx, "story-" + sid)}</section>' if S.get("vocab") else "")
                + (f'<section class="blk"><h2>Did you follow?</h2>{questions(S.get("questions"), ctx)}</section>' if S.get("questions") else "")
                + (f'<section class="blk after"><h2>About this story</h2>{md(S.get("after"))}</section>' if S.get("after") else "")
                + (f'<p class="source">{inl(S.get("source"))}</p>' if S.get("source") else "")
                + '<div class="read-end"><button class="done-btn" type="button" data-read="story:' + esc(sid) + '">I\'ve read this</button></div>'
                + pn + "</article>")
        page(url, S.get("title", sid), body, desc=clip(S.get("intro", ""), 200), image=S.get("image"), section="stories")
        SEARCH.append({"t": "story", "ti": S.get("title"), "fa": S.get("titleFa", ""), "r": S.get("titleR", ""), "u": url,
                       "s": f'{LEVEL_NAMES.get(S.get("level"), "")}, {S.get("kind", "")}'})
    secs = []
    blurbs = {"A1": "Very short and in the present tense. You can read these after the first lessons.",
              "A2": "Folk tales and everyday stories in the past tense.",
              "B1": "Legends from the Shahnameh, history and modern life, 250–450 words.",
              "B2": "Longer retellings of the great epics and romances, and modern stories.",
              "C1": "Literary prose: historical fiction and the epic in full colour."}
    for lv in levels:
        if not by_level[lv]:
            continue
        tiles = "".join(
            f'<li class="tile"><a href="{sid}.html">{thumb(STORIES[sid].get("image"), STORIES[sid].get("title"))}'
            f'<span class="tile-fa" lang="fa" dir="rtl">{esc(STORIES[sid].get("titleFa", ""))}</span>'
            f'<span class="tile-t">{esc(STORIES[sid].get("title", ""))}</span><span class="tile-m">{esc(STORIES[sid].get("kind", "").capitalize())}</span></a></li>'
            for sid in by_level[lv])
        secs.append(f'<section class="shelf" id="{lv.lower()}"><h2>{esc(LEVEL_NAMES[lv])}</h2><p>{blurbs[lv]}</p><ul class="tiles">{tiles}</ul></section>')
    body = ('<div class="wide">' + head_block("Stories", "داستان‌ها", "dāstān-hā", None,
            f"{len(order)} graded readers: folk tales, Mulla Nasreddin, the Shahnameh, history and everyday life in Iran. "
            "Every sentence has recorded audio, a transliteration and a translation you can hide. Start at your level and read a little every day.")
            + "".join(secs) + "</div>")
    page("stories/index.html", "Stories", body, desc="Graded Persian stories with audio and translation.", section="stories")


# ---------------------------------------------------------------------------------------------- culture
def build_culture():
    plan = COURSE.get("culture", {})
    order = {t: [a for a in plan.get(t, []) if a in ARTICLES] for t, *_ in TOPICS}
    for aid, A in ARTICLES.items():
        if A.get("topic") in order and aid not in order[A["topic"]]:
            order[A["topic"]].append(aid)
    for topic, ids in order.items():
        for aid in ids:
            A = ARTICLES[aid]
            url = f"culture/{aid}.html"
            ctx = {"url": url, "title": A.get("title", aid)}
            body_secs = "".join(f'<section class="art-sec">' + (f'<h2>{inl(s.get("h"))}</h2>' if s.get("h") else "")
                                + figure(s.get("image")) + md(s.get("md")) + "</section>" for s in A.get("body", []))
            facts = ""
            if A.get("facts"):
                facts = '<aside class="facts"><h2>Facts</h2><ul>' + "".join(f"<li>{inl(x)}</li>" for x in A["facts"]) + "</ul></aside>"
            sents = "".join(line(s, ctx) for s in A.get("sentences", []))
            related = [x for x in ids if x != aid][:4]
            rel_html = ""
            if related:
                rel_html = ('<section class="related"><h2>More on ' + esc(TOPIC[topic][1].lower()) + '</h2><ul class="tiles small">' + "".join(
                    f'<li class="tile"><a href="{x}.html">{thumb(ARTICLES[x].get("image"), ARTICLES[x].get("title"))}<span class="tile-t">{esc(ARTICLES[x].get("title"))}</span></a></li>'
                    for x in related) + "</ul></section>")
            kicker = crumbs("../", [("Culture", "index.html"), (TOPIC[topic][1], f"index.html#{topic}")])
            body = ('<article class="article narrow">'
                    + head_block(A.get("title", ""), A.get("titleFa", ""), A.get("titleR", ""), A.get("titleA"), A.get("summary", ""), kicker)
                    + figure(A.get("image"), "ph ph-hero", eager=True) + facts + body_secs
                    + (f'<section class="blk"><h2>Say it in Persian</h2>{study_bar(has_key(A.get("sentences"), "col"))}<div class="lines">{sents}</div></section>' if sents else "")
                    + (f'<section class="blk"><h2>Words</h2>{vocab_list(A.get("vocab", []), ctx, "article-" + aid)}</section>' if A.get("vocab") else "")
                    + '<div class="read-end"><button class="done-btn" type="button" data-read="article:' + esc(aid) + '">I\'ve read this</button></div>' + rel_html + "</article>")
            page(url, A.get("title", aid), body, desc=clip(A.get("summary", ""), 200), image=A.get("image"), section="culture")
            SEARCH.append({"t": topic, "ti": A.get("title"), "fa": A.get("titleFa", ""), "r": A.get("titleR", ""), "u": url,
                           "s": TOPIC[topic][1], "k": plain(A.get("summary", ""))})
    secs = []
    for key, name, fa, r, img, blurb in TOPICS:
        ids = order.get(key, [])
        if not ids:
            continue
        tiles = "".join(
            f'<li class="tile"><a href="{aid}.html">{thumb(ARTICLES[aid].get("image"), ARTICLES[aid].get("title"))}'
            f'<span class="tile-fa" lang="fa" dir="rtl">{esc(ARTICLES[aid].get("titleFa", ""))}</span>'
            f'<span class="tile-t">{esc(ARTICLES[aid].get("title", ""))}</span><span class="tile-m">{esc(clip(ARTICLES[aid].get("summary", ""), 120))}</span></a></li>'
            for aid in ids)
        secs.append(f'<section class="shelf" id="{key}"><h2>{esc(name)} <span class="lv-fa" lang="fa" dir="rtl">{esc(fa)}</span></h2><p>{esc(blurb)}</p><ul class="tiles">{tiles}</ul></section>')
    n = sum(len(v) for v in order.values())
    jump = "".join(f'<li><a href="#{k}">{esc(nm)}</a></li>' for k, nm, *_ in TOPICS if order.get(k))
    body = ('<div class="wide">' + head_block("Iran in pictures and stories", "فرهنگ ایران", "farhang-e Irān", None,
            f"{n} illustrated articles on the history, places, food, festivals, arts and people of the Persian-speaking world. "
            "Each one ends with useful sentences, recorded, and the words to go with them.")
            + f'<nav class="jump" aria-label="Topics"><ul>{jump}</ul></nav>' + "".join(secs) + "</div>")
    page("culture/index.html", "Culture", body, desc="History, places, food, festivals, arts and people of Iran, for Persian learners.", section="culture", image="naqsh-e-jahan")
    return order


# ---------------------------------------------------------------------------------------------- poetry
def build_poetry():
    order = [p for p in COURSE.get("poems", []) if p in POEMS] + sorted(p for p in POEMS if p not in COURSE.get("poems", []))
    for pid in order:
        P = POEMS[pid]
        url = f"poetry/{pid}.html"
        ctx = {"url": url, "title": P.get("title", pid)}
        verses = []
        for ln in P.get("lines", []):
            SENTS.append((ln.get("fa", ""), ln.get("en", ""), ln.get("a", ""), url, ctx["title"]))
            halves = [x.strip() for x in ln.get("fa", "").split(" / ")]
            fa_html = "".join(f'<span class="mesra">{esc(hv)}</span>' for hv in halves)
            words = ""
            if ln.get("words"):
                words = ('<details class="wbw"><summary>Word by word</summary><table><tbody>' + "".join(
                    f'<tr><td lang="fa" dir="rtl">{esc(w[0])}</td><td class="tr">{esc(w[1])}</td><td>{esc(w[2])}</td></tr>'
                    for w in ln["words"] if isinstance(w, list) and len(w) >= 3) + "</tbody></table></details>")
            verses.append(f'<div class="verse ln"' + (f' data-a="{esc(ln["a"])}"' if ln.get("a") else "") + ">"
                          + say(ln.get("a")) + f'<div class="ln-b"><p class="fa" lang="fa" dir="rtl">{fa_html}</p>'
                          + f'<p class="tr">{esc(ln.get("r", ""))}</p><p class="en">{inl(ln.get("en", ""))}</p>'
                          + (f'<p class="note">{inl(ln["note"])}</p>' if ln.get("note") else "") + words + "</div></div>")
        kicker = crumbs("../", [("Poetry", "index.html"), (P.get("poet", ""), None)])
        meta = ", ".join(x for x in [P.get("poet"), P.get("work"), (P.get("century") + " century") if P.get("century") else "", P.get("form")] if x)
        body = ('<article class="poem narrow">' + head_block(P.get("title", ""), P.get("titleFa", ""), P.get("titleR", ""), P.get("titleA"), P.get("intro", ""), kicker)
                + f'<p class="meta">{esc(meta)} <bdi lang="fa" dir="rtl">{esc(P.get("poetFa", ""))}</bdi></p>'
                + figure(P.get("image"), "ph ph-portrait") + study_bar(False) + f'<div class="verses">{"".join(verses)}</div>'
                + f'<section class="blk"><h2>Reading the poem</h2>{md(P.get("commentary"))}</section>' + '<div class="read-end"><button class="done-btn" type="button" data-read="poem:' + esc(pid) + '">I\'ve read this</button></div>' + '</article>')
        page(url, P.get("title", pid), body, desc=f'{P.get("title")} by {P.get("poet")}, with translation and word-by-word notes.', image=P.get("image"), section="poetry")
        SEARCH.append({"t": "poem", "ti": P.get("title"), "fa": P.get("titleFa", ""), "r": P.get("titleR", ""), "u": url, "s": P.get("poet", "")})
    items = "".join(
        f'<li class="poem-row"><a href="{pid}.html"><span class="pr-fa" lang="fa" dir="rtl">{esc(POEMS[pid].get("titleFa", ""))}</span>'
        f'<span class="pr-t">{esc(POEMS[pid].get("title", ""))}</span><span class="pr-p">{esc(POEMS[pid].get("poet", ""))}, {esc(POEMS[pid].get("century", ""))} century</span>'
        + (f'<span class="pr-l" lang="fa" dir="rtl">{esc(POEMS[pid]["lines"][0]["fa"].split(" / ")[0])}</span>' if POEMS[pid].get("lines") else "")
        + "</a></li>" for pid in order)
    body = ('<div class="narrow">' + head_block("Poetry", "شعر", "she'r", None,
            "Iranians quote poetry the way others quote proverbs. Here are the poems everyone knows – Saadi, Rumi, Hafez, Ferdowsi, Khayyam – "
            "line by line, with audio, a translation, a word-by-word gloss and notes on how to read them.")
            + (f'<ul class="poems">{items}</ul>' if items else '<p class="empty">The poems are being annotated. Come back soon.</p>') + "</div>")
    page("poetry/index.html", "Poetry", body, desc="Classical Persian poems with translation, transliteration and audio.", section="poetry", image="tomb-of-hafez")


# ---------------------------------------------------------------------------------------------- news
def build_news():
    stories = sorted(NEWS.get("stories", []), key=lambda s: s.get("date", ""), reverse=True)
    for S in stories:
        url = f'news/{S["id"]}.html'
        ctx = {"url": url, "title": S.get("title", "")}
        sents = "".join(line(s, ctx) for s in S.get("sentences", []))
        kicker = crumbs("../", [("News", "index.html"), (S.get("date", ""), None)])
        body = ('<article class="news narrow">' + head_block(S.get("title", ""), S.get("titleFa", ""), S.get("titleR", ""), S.get("titleA"), "", kicker)
                + f'<p class="meta">{esc(S.get("tag", ""))}, level {esc(S.get("level", ""))}. Source: <a href="{esc(S.get("url", ""))}">{esc(S.get("source", ""))}</a></p>'
                + figure(S.get("image"), "ph ph-hero", eager=True) + study_bar(False) + f'<div class="lines">{sents}</div>'
                + (f'<section class="blk"><h2>Background</h2>{md(S.get("why"))}</section>' if S.get("why") else "")
                + (f'<section class="blk"><h2>Words</h2>{vocab_list(S.get("vocab", []), ctx, "news-" + S["id"])}</section>' if S.get("vocab") else "")
                + (f'<section class="blk"><h2>Did you follow?</h2>{questions(S.get("questions"), ctx)}</section>' if S.get("questions") else "")
                + "</article>")
        page(url, S.get("title", ""), body, desc=f'{S.get("title")} – a news story in simple Persian.', image=S.get("image"), section="news")
        SEARCH.append({"t": "news", "ti": S.get("title"), "fa": S.get("titleFa", ""), "r": S.get("titleR", ""), "u": url, "s": S.get("date", "")})
    rows = "".join(
        f'<li class="news-row"><a href="{S["id"]}.html">{thumb(S.get("image"), S.get("title"))}<span class="nr-b"><span class="nr-d">{esc(S.get("date", ""))}, {esc(S.get("tag", ""))}, level {esc(S.get("level", ""))}</span>'
        f'<span class="nr-fa" lang="fa" dir="rtl">{esc(S.get("titleFa", ""))}</span><span class="nr-t">{esc(S.get("title", ""))}</span></span></a></li>'
        for S in stories)
    body = ('<div class="narrow">' + head_block("The news in simple Persian", "اخبار به فارسی ساده", "akhbār be fārsi-ye sāde", None,
            NEWS.get("intro", "")) + f'<p class="meta">Updated {esc(NEWS.get("updated", ""))}.</p><ul class="news-list">{rows}</ul></div>')
    page("news/index.html", "News", body, desc="This week's news written in simple Persian with audio.", section="news")
    return stories


# ---------------------------------------------------------------------------------------------- reference pages
def build_phrasebook():
    if not PHRASEBOOK:
        body = '<div class="narrow">' + head_block("Phrasebook", "کتاب عبارات", "ketāb-e ebārāt", None, "") + '<p class="empty">The phrasebook is being written.</p></div>'
        page("phrasebook/index.html", "Phrasebook", body, section="phrasebook")
        return
    ctx = {"url": "phrasebook/index.html", "title": "Phrasebook"}
    secs, jump = [], []
    for s in PHRASEBOOK.get("sections", []):
        sid = s.get("id", "")
        jump.append(f'<li><a href="#{esc(sid)}">{esc(s.get("title", ""))}</a></li>')
        items = []
        for it in s.get("items", []):
            reg = '<span class="reg reg-f">formal</span>' if it.get("formal") is True else ('<span class="reg reg-i">friendly</span>' if it.get("formal") is False else "")
            items.append(line(it, ctx).replace('<div class="ln-b">', '<div class="ln-b">' + reg, 1)
                         + "")
            SEARCH.append({"t": "phrase", "ti": it.get("en", ""), "fa": it.get("fa", ""), "r": it.get("r", ""), "u": f"phrasebook/index.html#{sid}", "s": s.get("title", "")})
        deck = DECKS.setdefault("phrasebook-" + sid, {"t": "Phrasebook: " + s.get("title", ""), "u": f"phrasebook/index.html#{sid}", "w": []})
        deck["w"] = [[it.get("fa", ""), it.get("r", ""), it.get("en", ""), it.get("a", "")] for it in s.get("items", [])]
        secs.append(f'<section class="blk pb-sec" id="{esc(sid)}"><h2>{esc(s.get("title", ""))} <span class="lv-fa" lang="fa" dir="rtl">{esc(s.get("titleFa", ""))}</span></h2>'
                    + (f'<p class="context">{inl(s.get("intro", ""))}</p>' if s.get("intro") else "") + f'<div class="lines">{"".join(items)}</div></section>')
    n = sum(len(s.get("items", [])) for s in PHRASEBOOK.get("sections", []))
    body = ('<div class="with-toc"><aside class="toc-side" aria-label="Sections"><p>Sections</p><ol>' + "".join(jump) + '</ol></aside><div class="narrow-in">'
            + head_block("Phrasebook", "کتاب عبارات", "ketāb-e ebārāt", None, PHRASEBOOK.get("intro", "") + f"\n\n{n} phrases in {len(secs)} sections.")
            + study_bar(True) + "".join(secs) + "</div></div>")
    page("phrasebook/index.html", "Phrasebook", body, desc=f"{n} everyday Persian phrases with audio, formal and spoken.", section="phrasebook")


def build_idioms():
    if not IDIOMS:
        body = '<div class="narrow">' + head_block("Proverbs and idioms", "ضرب‌المثل‌ها و اصطلاحات", "zarb-ol-masal-hā va estelāhāt", None, "") + '<p class="empty">Being written.</p></div>'
        page("idioms/index.html", "Proverbs and idioms", body, section="idioms")
        return
    ctx = {"url": "idioms/index.html", "title": "Proverbs and idioms"}
    items = []
    cats = sorted({it.get("cat", "") for it in IDIOMS.get("items", []) if it.get("cat")})
    for i, it in enumerate(IDIOMS.get("items", [])):
        ex = line(it["ex"], ctx, cls="ln ln-ex") if isinstance(it.get("ex"), dict) and it["ex"].get("fa") else ""
        items.append(f'<li class="idiom" data-kind="{esc(it.get("kind", ""))}" data-cat="{esc(it.get("cat", ""))}" id="i{i + 1}">'
                     + line({k: v for k, v in it.items() if k not in ("ex", "note", "lit")}, ctx)
                     + (f'<p class="lit">Literally: {inl(it["lit"])}</p>' if it.get("lit") else "")
                     + (f'<p class="note">{inl(it["note"])}</p>' if it.get("note") else "") + ex
                     + save_btn(it.get("fa", ""), it.get("r", ""), it.get("en", ""), it.get("a", ""), "Proverbs and idioms") + "</li>")
        SEARCH.append({"t": "idiom", "ti": it.get("en", ""), "fa": it.get("fa", ""), "r": it.get("r", ""), "u": f"idioms/index.html#i{i + 1}", "s": it.get("kind", "")})
    filt = ('<div class="filters" data-idiom-filter><label>Show <select data-f="kind"><option value="">proverbs and idioms</option><option value="proverb">proverbs</option><option value="idiom">idioms</option></select></label>'
            '<label>Topic <select data-f="cat"><option value="">all</option>' + "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats) + "</select></label></div>")
    body = ('<div class="narrow">' + head_block("Proverbs and idioms", "ضرب‌المثل‌ها و اصطلاحات", "zarb-ol-masal-hā va estelāhāt", None,
            IDIOMS.get("intro", "") + f"\n\n{len(items)} sayings, each with its literal meaning, when to use it and an example.")
            + filt + study_bar(False) + f'<ul class="idioms">{"".join(items)}</ul></div>')
    page("idioms/index.html", "Proverbs and idioms", body, desc="Persian proverbs and idioms with literal meanings, usage and audio.", section="idioms")


ROLE_NAMES = {}


def grammar_sentence(s, ctx):
    if not s:
        return ""
    SENTS.append((s.get("fa", ""), s.get("en", ""), s.get("a", ""), ctx["url"], ctx["title"]))
    parts = s.get("p") or []
    fa_html = " ".join(f'<span class="gp gp-{esc(p[0])}" title="{esc(ROLE_NAMES.get(p[0], p[0]))}: {esc(p[3] if len(p) > 3 else "")}">{esc(p[1])}</span>' for p in parts) or esc(s.get("fa"))
    if parts and s.get("fa", "").rstrip()[-1:] in ".؟!":
        fa_html += esc(s["fa"].rstrip()[-1])
    en_parts = s.get("e") or []
    en_html = " ".join(f'<span class="gp gp-{esc(p[0])}">{esc(p[1])}</span>' for p in en_parts) or esc(s.get("en"))
    gloss = ""
    if parts:
        gloss = '<table class="gloss"><tbody><tr>' + "".join(f'<td><span class="gp gp-{esc(p[0])}" lang="fa" dir="rtl">{esc(p[1])}</span><br><span class="tr">{esc(p[2])}</span><br><small>{esc(p[3] if len(p) > 3 else "")}</small></td>' for p in reversed(parts)) + "</tr></tbody></table>"
    return (f'<div class="ln gs"' + (f' data-a="{esc(s["a"])}"' if s.get("a") else "") + ">" + say(s.get("a"))
            + f'<div class="ln-b"><p class="fa" lang="fa" dir="rtl">{fa_html}</p><p class="tr">{esc(s.get("r", ""))}</p>'
            + f'<p class="en">{en_html}</p>{gloss}</div></div>')


def build_grammar():
    ctx = {"url": "grammar/index.html", "title": "Grammar"}
    out = []
    if GRAMMAR:
        for r in GRAMMAR.get("roles", []):
            ROLE_NAMES[r["k"]] = r["en"]
        legend = "".join(f'<li><span class="gp gp-{esc(r["k"])}">{esc(r["en"])}</span> <bdi lang="fa" dir="rtl">{esc(r["fa"])}</bdi> <span class="tr">{esc(r["r"])}</span> – {esc(r["about"])}</li>'
                         for r in GRAMMAR.get("roles", []))
        out.append(f'<section class="blk" id="patterns"><h2>{esc(GRAMMAR.get("title", "Sentence patterns"))}</h2>{md(GRAMMAR.get("intro", ""))}<ul class="roles">{legend}</ul>')
        cmp_ = GRAMMAR.get("compare") or {}
        if cmp_.get("s"):
            out.append('<div class="lines">' + grammar_sentence(cmp_["s"], ctx) + "</div>" + (f'<p class="note">{inl(cmp_.get("note", ""))}</p>' if cmp_.get("note") else ""))
        for p in GRAMMAR.get("patterns", []):
            order = " + ".join(f'<span class="gp gp-{esc(k)}">{esc(ROLE_NAMES.get(k, k))}</span>' for k in p.get("order", []))
            out.append(f'<div class="pattern"><h3>{p.get("n")}. {esc(p.get("name", ""))} <bdi lang="fa" dir="rtl">{esc(p.get("fa", ""))}</bdi></h3>'
                       f'<p class="meta">{esc(p.get("kind", ""))}</p><p class="order">Persian order: {order}</p><p>{inl(p.get("note", ""))}</p>'
                       f'<div class="lines">' + "".join(grammar_sentence(e, ctx) for e in p.get("ex", [])) + "</div></div>")
        out.append("</section>")
        d = GRAMMAR.get("detail") or {}
        if d:
            out.append(f'<section class="blk"><h2>{esc(d.get("title", ""))}</h2><p>{inl(d.get("text", ""))}</p><div class="lines">'
                       + "".join(grammar_sentence(s, ctx) for s in d.get("steps", [])) + f'</div><p class="note">{inl(d.get("note", ""))}</p></section>')
        for f in GRAMMAR.get("features", []):
            tb = ""
            if isinstance(f.get("table"), dict):
                tb = (f'<div class="tbl-wrap"><table><caption>{esc(f["table"].get("title", ""))}</caption><tbody>' + "".join(
                    "<tr>" + "".join(f"<td>{cell(c) if not isinstance(c, dict) else cell(c.get('fa', ''))}</td>" for c in (row if isinstance(row, list) else [row.get('fa', ''), row.get('r', ''), row.get('en', '')])) + "</tr>"
                    for row in f["table"].get("rows", [])) + "</tbody></table></div>")
            out.append(f'<section class="blk"><h2>{esc(f.get("title", ""))}</h2><p>{inl(f.get("text", ""))}</p><div class="lines">'
                       + "".join(grammar_sentence(s, ctx) for s in f.get("ex", [])) + f"</div>{tb}</section>")
    # every grammar block of the course
    idx = []
    for lv in COURSE.get("levels", []):
        rows = []
        for lid in lv.get("lessons", []):
            L = LESSONS.get(lid)
            if not L:
                continue
            for i, b in enumerate(L.get("sections", [])):
                if b.get("type") in ("grammar", "letters") and b.get("title"):
                    rows.append(f'<li><a href="../course/{lid}.html#s{i + 1}">{inl(b["title"])}</a> <span class="meta">lesson {L.get("n")}</span></li>')
        if rows:
            idx.append(f'<h3>{esc(lv["name"])}</h3><ul class="gindex">{"".join(rows)}</ul>')
    body = ('<div class="narrow">' + head_block("Grammar", "دستور زبان", "dastur-e zabān", None,
            "How Persian sentences are built, and an index of every grammar point in the course. Persian grammar is famously regular: "
            "no gender, no articles to agree, verbs with one set of endings. The colours show each part's role.")
            + '<nav class="jump"><ul><li><a href="#patterns">Sentence patterns</a></li><li><a href="#index">Grammar in the course</a></li></ul></nav>'
            + "".join(out) + f'<section class="blk" id="index"><h2>Grammar in the course</h2>{"".join(idx) or "<p>The lessons are being written.</p>"}</section></div>')
    page("grammar/index.html", "Grammar", body, desc="Persian sentence patterns and an index of grammar points.", section="grammar")


def build_verbs():
    verbs = (VERBS or {}).get("verbs", [])
    ctx = {"url": "verbs/index.html", "title": "Verbs"}
    rows = []
    for i, v in enumerate(verbs):
        ex = v.get("ex") or {}
        if ex.get("fa"):
            SENTS.append((ex["fa"], ex.get("en", ""), ex.get("a", ""), ctx["url"], ctx["title"]))
        rows.append(f'<li class="verb" data-i="{i}" data-level="{esc(v.get("level", ""))}" data-cat="{esc(v.get("cat", ""))}">'
                    f'<button type="button" class="verb-open" aria-expanded="false"><span class="vb-fa" lang="fa" dir="rtl">{esc(v.get("inf", ""))}</span>'
                    f'<span class="vb-r tr">{esc(v.get("r", ""))}</span><span class="vb-en">{esc(v.get("en", ""))}</span>'
                    f'<span class="vb-stem">stem <bdi lang="fa" dir="rtl">{esc(v.get("stem", ""))}</bdi> <span class="tr">{esc(v.get("stemR", ""))}</span></span></button>'
                    f'{say(v.get("a"), "Listen: " + v.get("inf", ""))}</li>')
        SEARCH.append({"t": "verb", "ti": v.get("en", ""), "fa": v.get("inf", ""), "r": v.get("r", ""), "u": f"verbs/index.html#v{i}", "s": "Verb"})
    data = json.dumps(verbs, ensure_ascii=False).replace("</", "<\\/")
    body = ('<div class="narrow">' + head_block("Verbs", "فعل‌ها", "fe'l-hā", None,
            "Every Persian verb has two stems – the past stem, which is the infinitive without its final ن, and the present stem, which you have to learn. "
            "From those two the whole verb follows. Pick a verb to see it in every tense, or type any infinitive and present stem below.")
            + '<div class="verb-tools"><label>Find a verb <input type="search" data-verb-q placeholder="go, رفتن, raftan"></label>'
            + '<details class="custom-verb"><summary>Conjugate another verb</summary><p>Infinitive and present stem in Persian letters, with their transliteration.</p>'
            + '<div class="cv-grid"><label>Infinitive <input data-cv="inf" lang="fa" dir="rtl" placeholder="نوشتن"></label><label>Transliteration <input data-cv="r" placeholder="neveshtan"></label>'
            + '<label>Present stem <input data-cv="stem" lang="fa" dir="rtl" placeholder="نویس"></label><label>Transliteration <input data-cv="stemR" placeholder="nevis"></label></div>'
            + '<button type="button" class="btn" data-cv-go>Conjugate</button></details></div>'
            + '<div class="conj" data-conj hidden></div>'
            + (f'<ul class="verbs">{"".join(rows)}</ul>' if rows else '<p class="empty">The verb list is being written – you can already conjugate any verb above.</p>')
            + f'<script type="application/json" id="verb-data">{data}</script></div>')
    page("verbs/index.html", "Verbs", body, desc="Persian verbs with present stems and full conjugation tables.", section="verbs")


def build_alphabet():
    secs = []
    for s in ALPHABET.get("sections", []):
        cells = []
        for c in s.get("cells", []):
            if not c:
                continue
            ex = c.get("ex") or {}
            forms = "".join(f'<span lang="fa" dir="rtl">{esc(f)}</span>' for f in (c.get("forms") or [])[:4])
            cells.append(f'<li class="ab-cell"><button type="button" class="ab-btn" data-a="{esc(ex.get("a", ""))}" aria-label="{esc(c.get("name", ""))}">'
                         f'<span class="ab-g" lang="fa" dir="rtl">{esc(c["g"])}</span><span class="ab-n">{esc(c.get("name", ""))}</span>'
                         f'<span class="ab-s">{esc(c.get("r", ""))}</span></button>'
                         + (f'<span class="ab-forms">{forms}</span>' if forms else "")
                         + (f'<span class="ab-ex"><bdi lang="fa" dir="rtl">{esc(ex.get("w", ""))}</bdi> <span class="tr">{esc(ex.get("r", ""))}</span> <span class="en">{esc(ex.get("m", ""))}</span></span>' if ex else "")
                         + "</li>")
        secs.append(f'<section class="blk"><h2>{esc(s.get("title", ""))}</h2><p>{inl(s.get("note", ""))}</p><ol class="alphabet">{"".join(cells)}</ol></section>')
    lessons = [lid for lid in (COURSE.get("levels", [{}])[0].get("lessons", [])) if lid in LESSONS]
    links = "".join(f'<li><a href="../course/{lid}.html">{esc(LESSONS[lid]["title"])}</a></li>' for lid in lessons)
    tips = "".join(f"<li>{inl(t)}</li>" for t in ALPHABET.get("tips", []))
    body = ('<div class="wide">' + head_block("The Persian alphabet", "الفبای فارسی", "alefbā-ye fārsi", None,
            ALPHABET.get("intro", "") + " Tap a letter to hear its example word.")
            + (f'<section class="blk"><h2>Learn the letters step by step</h2><ol class="link-list">{links}</ol></section>' if links else "")
            + "".join(secs) + f'<section class="blk"><h2>Remember</h2><ul class="tips">{tips}</ul></section></div>')
    page("alphabet/index.html", "The Persian alphabet", body, desc="All 32 Persian letters with their forms, sounds and example words with audio.", section="alphabet", image="persian-calligraphy")


def build_numbers():
    ctx = {"url": "numbers/index.html", "title": "Numbers"}
    tables = ""
    if NUMBERS:
        for grp in NUMBERS.get("groups", []):
            rows = "".join(f'<tr><td class="num">{esc(it["n"])}</td><td class="num" lang="fa">{esc(fa_num(it["n"]))}</td>'
                           f'<td><bdi lang="fa" dir="rtl">{esc(it["fa"])}</bdi></td><td class="tr">{esc(it["r"])}</td><td>{say(it.get("a"), "Listen")}</td></tr>'
                           for it in grp.get("items", []))
            tables += f'<section class="blk"><h2>{esc(grp["title"])}</h2><div class="tbl-wrap"><table class="numtab"><tbody>{rows}</tbody></table></div></section>'
    body = ('<div class="narrow">' + head_block("Numbers and dates", "عددها و تاریخ", "adad-hā va tārikh", None,
            "Persian numbers are regular once you know 1–20 and the tens. Type any number to see it written in Persian words and digits, "
            "and convert dates between the Iranian (Solar Hijri) calendar and the Western one.")
            + '<section class="blk"><h2>Write a number</h2><div class="numconv"><label>Number <input type="text" inputmode="numeric" data-num-in value="1405"></label>'
            + '<div class="num-out" data-num-out aria-live="polite"></div></div></section>'
            + '<section class="blk"><h2>Today in Iran</h2><div class="today-big" data-today></div>'
            + '<div class="dateconv"><label>Western date <input type="date" data-g2j></label><p data-g2j-out aria-live="polite"></p>'
            + '<label>Iranian date <input type="text" data-j2g placeholder="1405/07/25"></label><p data-j2g-out aria-live="polite"></p></div>'
            + '<h3>The months</h3><ol class="months" data-months></ol></section>'
            + tables + "</div>")
    page("numbers/index.html", "Numbers and dates", body, desc="Persian numbers in words and digits, and the Iranian calendar.", section="numbers")


def build_dictionary():
    n = len([e for e in DICT.get("entries", []) if not e.get("x")])
    extra = len(DICT.get("entries", [])) - n
    body = ('<div class="narrow">' + head_block("Dictionary", "واژه‌نامه", "vāzhe-nāme", None,
            f"The {n:,} most common words of Persian, ranked by how often they appear, plus {extra} more from its topic lists – each with a recorded pronunciation. "
            "Search in Persian, in rough transliteration or in English. Where a word appears in this site's lessons and stories, you can read it in context.")
            + '<div class="dict-tools"><input type="search" data-dict-q placeholder="water, آب, ab" aria-label="Search the dictionary">'
            + '<label>Level <select data-dict-level><option value="">all</option><option value="1">Beginner (1–1,000)</option><option value="2">Intermediate (1,001–3,000)</option><option value="3">Advanced (3,001–5,000)</option><option value="4">5,000+</option></select></label>'
            + '<label>Topic <select data-dict-list><option value="">all</option></select></label>'
            + '<label>Part of speech <select data-dict-pos><option value="">all</option><option value="n">noun</option><option value="v">verb</option><option value="adj">adjective</option><option value="adv">adverb</option><option value="prep">preposition</option><option value="conj">conjunction</option><option value="pron">pronoun</option><option value="q">number/quantity</option><option value="pn">name</option></select></label></div>'
            + '<p class="dict-count" data-dict-count aria-live="polite">Loading the dictionary…</p><ol class="dict" data-dict></ol>'
            + '<p><button type="button" class="btn-quiet" data-dict-more hidden>Show more</button></p>'
            + '<p class="small">Word list, ranks, glosses and topics from Corey Miller and Karineh Aghajanian-Stewart, <em>A Frequency Dictionary of Persian</em> (Routledge, 2018). Example sentences come from this site.</p></div>')
    page("dictionary/index.html", "Dictionary", body, desc="The 5,000 most common Persian words with audio, searchable in Persian and English.", section="dictionary")


def build_flashcards():
    body = ('<div class="narrow">' + head_block("My flashcards", "کارت‌های من", "kārt-hā-ye man", None,
            "Every word you save with + on any page comes here. Review a few minutes a day: the cards you find hard come back sooner, the easy ones later. "
            "Your cards are kept in this browser; use Save backup to move them to another device.")
            + '<div class="fc" data-fc><p class="fc-stats" data-fc-stats></p><div class="fc-card" data-fc-card hidden></div>'
            + '<div class="fc-actions"><button class="btn" type="button" data-fc-start>Start review</button>'
            + '<label>Front <select data-fc-front><option value="fa">Persian</option><option value="en">English</option></select></label></div>'
            + '<section class="blk"><h2>Add a set of words</h2><p>Add all the words of a lesson, story or article at once.</p><div class="fc-add"><select data-fc-deck aria-label="Choose a set of words"></select><button class="btn-quiet" type="button" data-fc-add>Add these words</button></div></section>'
            + '<section class="blk"><h2>Saved words</h2><div class="fc-list" data-fc-list></div>'
            + '<p class="fc-io"><button class="btn-quiet" type="button" data-fc-export>Save backup</button> <label class="btn-quiet file">Load backup <input type="file" accept=".json" data-fc-import hidden></label> '
            + '<button class="btn-quiet" type="button" data-fc-csv>Export for Anki (CSV)</button></p></section></div></div>')
    page("flashcards/index.html", "My flashcards", body, desc="Review your saved Persian words with spaced repetition.", section="flashcards")


def build_search():
    body = ('<div class="narrow">' + head_block("Search", "جست‌وجو", "jost-o-ju", None, "")
            + '<form class="search-big" action="index.html"><input type="search" name="q" data-search-q aria-label="Search" placeholder="Search lessons, stories, words, phrases"></form>'
            + '<div data-search-out aria-live="polite"></div></div>')
    page("search/index.html", "Search", body, section="search")


def build_about():
    n_l, n_s, n_a, n_p = len(LESSONS), len(STORIES), len(ARTICLES), len(POEMS)
    body = ('<div class="narrow prose">' + head_block("About Learn Farsi", "درباره‌ی ما", "dar-bāre-ye mā", None, "") + md(f"""
Learn Farsi is a free course in Persian for English speakers, written as an open book: every lesson, story and article lives as a plain JSON file in [the GitHub repository]({REPO_URL}), and the website is built from it. Right now it has {n_l} lessons, {n_s} graded stories, {n_a} illustrated articles and {n_p} annotated poems, a phrasebook, proverbs, a verb conjugator and a 5,000-word dictionary.

## How to use it

1. If you can't read Persian yet, start with **the alphabet**: eight short lessons, about an hour each.
2. Then work through the course in order. Each lesson takes 45–90 minutes. Listen to every line, say it aloud, then hide the English and the transliteration and read again.
3. Save the words you want to keep with **+**; review them on the flashcards page for ten minutes a day.
4. From the end of A1, read one story a week at your level, and from A2 the weekly news in simple Persian.
5. Dip into culture and poetry whenever you like – they are written for learners at every level.

## Which Persian?

The course teaches the standard Persian of Iran, as written in books and newspapers and spoken in Tehran. Wherever everyday speech differs, the spoken form is shown too, marked *Spoken*. Persian is also spoken as Dari in Afghanistan and Tajik in Tajikistan; the advanced lessons explain the differences.

## Transliteration

ā as in *father*, a as in *cat*, e as in *bed*, o as in *pole* (short), u as in *rule*, i as in *machine*; kh as in Scottish *loch*; gh a throaty r-like sound for both غ and ق; zh as in *measure*; ' a catch in the throat for ع and ء. Hyphens join the parts of one Persian word: *mi-ravam*, *ketāb-hā*, *khāne-ye man*.

## Sources and credits

- **Audio** is made with the open-source Piper "gyro" Persian voice, run with sherpa-onnx. It is a synthetic voice: listen to real speakers too.
- **Photos** come from Wikimedia Commons; the photographer and licence are under every picture, and all are listed on the [photo credits page](photos.html).
- **The dictionary**'s word list, frequency ranks, glosses and topic lists come from Corey Miller and Karineh Aghajanian-Stewart, *A Frequency Dictionary of Persian* (Routledge, 2018).
- **News stories** are original summaries in simple Persian of reports from the sources linked on each story.
- **Poems** are by classical poets whose work is in the public domain; translations and notes are new.
- **Fonts**: Vazirmatn by Saber Rastikerdar, Lalezar by Borna Izadpanah, Literata by TypeTogether – all under the SIL Open Font License.

## Licence and contributing

The text of the course is free to use and share under CC BY-SA 4.0; the code is MIT. Spotted a mistake in the Persian? Open an issue or pull request on [GitHub]({REPO_URL}) – every file is plain text, described in `CONTENT_GUIDE.md`.
""") + "</div>")
    page("about/index.html", "About", body, desc="About Learn Farsi: how to use it, sources and credits.", section="about")
    rows = "".join(f'<tr><td><a href="{esc(im["page"])}">{esc(im.get("caption", k))}</a></td><td>{esc(im.get("artist", ""))}</td>'
                   f'<td><a href="{esc(im.get("licenseUrl", ""))}">{esc(im.get("license", ""))}</a></td></tr>'
                   for k, im in sorted(IMAGES.items(), key=lambda kv: kv[1].get("caption", kv[0])))
    body = ('<div class="narrow">' + head_block("Photo credits", "عکس‌ها", "aks-hā", None,
            "Every photo on this site comes from Wikimedia Commons and is used under the licence shown. Thank you to all the photographers and institutions who share their work.")
            + f'<div class="tbl-wrap"><table class="credits"><thead><tr><th>Photo</th><th>Author</th><th>Licence</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    page("about/photos.html", "Photo credits", body, desc="Credits for the photos used on Learn Farsi.", section="about")


CITIES = {"script": ("Tabriz", "تبریز"), "a1": ("Qazvin", "قزوین"), "a2": ("Tehran", "تهران"), "b1": ("Kashan", "کاشان"),
          "b2": ("Isfahan", "اصفهان"), "c1": ("Shiraz", "شیراز")}


def build_journey():
    """assets/journey.json (what each lesson teaches, for the progress page) and journey/index.html."""
    ranks = {}
    p = os.path.join(ROOT, "data", "dict.json")
    total = 0
    if os.path.exists(p):
        for e in json.load(open(p, encoding="utf-8")).get("entries", []):
            if e.get("w") and e["w"] not in ranks:
                ranks[e["w"]] = (e.get("n", 99999), e.get("c", 0))
                total += e.get("c", 0)
    levels, lessons = [], {}
    for lv in COURSE.get("levels", []):
        ids = [l for l in lv.get("lessons", []) if l in LESSONS]
        city = CITIES.get(lv["id"], ("", ""))
        levels.append({"id": lv["id"], "name": lv.get("name", ""), "fa": lv.get("fa", ""), "city": city[0], "cityFa": city[1], "lessons": ids})
        for lid in ids:
            L = LESSONS[lid]
            words = []
            for b in L.get("sections", []):
                if b.get("type") == "vocab":
                    for it in b.get("items", []):
                        if it.get("fa") and it["fa"] not in words:
                            words.append(it["fa"])
            lessons[lid] = {"t": L.get("title", ""), "u": f"course/{lid}.html", "lv": lv["id"], "n": L.get("n", 0),
                            "w": words, "g": [plain(g) for g in L.get("goals", [])]}
    freq = {w: [r[0], r[1]] for w, r in ranks.items()}
    fal = []
    for pid in COURSE.get("poems", []):
        P = POEMS.get(pid)
        if not P:
            continue
        for ln in P.get("lines", [])[:6]:
            if ln.get("a") and ln.get("en"):
                fal.append([ln["fa"], ln["en"], ln["a"], f"poetry/{pid}.html", P.get("poet", "")])
    praise = []
    pp = os.path.join(ROOT, "data", "praise.json")
    if os.path.exists(pp):
        praise = [[x["fa"], x["r"], x["en"], x.get("a", "")] for x in json.load(open(pp, encoding="utf-8")).get("items", [])]
    data = {"levels": levels, "lessons": lessons, "freq": freq, "total": total, "fal": fal, "praise": praise,
            "stories": {k: [v.get("title", ""), v.get("level", "")] for k, v in STORIES.items()},
            "poems": {k: v.get("title", "") for k, v in POEMS.items()}, "articles": len(ARTICLES)}
    json.dump(data, open(os.path.join(ASSETS, "journey.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    body = ('<div class="narrow wide-journey" data-journey>' + head_block("My journey", "سفر من", "safar-e man", None,
            "From the first letter in Tabriz to Hafez's garden in Shiraz: every lesson you finish moves your caravan on and weaves "
            "one more medallion into your carpet. Your journey is kept in this browser – nothing is sent anywhere.")
            + '<section class="blk j-route"><h2>The caravan route</h2><div data-j-route></div></section>'
            + '<section class="blk j-stats" data-j-stats></section>'
            + '<section class="blk"><h2>Your carpet</h2><p class="meta">One medallion for every lesson. Finish a lesson to weave it in.</p><div data-j-carpet></div></section>'
            + '<section class="blk"><h2>Badges</h2><div data-j-badges></div></section>'
            + '<section class="blk"><h2>What you can do now</h2><div data-j-cando></div></section>'
            + '<section class="blk j-cert" data-j-cert></section></div>')
    page("journey/index.html", "My journey", body, desc="Your progress in Persian: the caravan route, your carpet, badges and streak.", section="journey")


def build_voice():
    body = ('<div class="narrow" data-voice-page>' + head_block("Friend's voice", "صدای دوست", "sedā-ye dust", None,
            "Do you know someone who speaks Persian? Ask them to read the lines of a lesson aloud. Next to every speaker icon on the site "
            "you get two more buttons: a **microphone** to record your friend reading that line, and a **person** button to hear the recording. "
            "You can also choose to hear your friend's voice instead of the computer voice everywhere – in dialogues, *Play all* and the listening exercises.")
            + '<section class="blk"><h2>Where your recordings are kept</h2><p class="vstatus" data-voice-status>…</p>'
            + '<p class="vbtns"><button type="button" class="btn gbtn" data-voice-signin>Sign in with Google</button> '
            + '<button type="button" class="btn-quiet" data-voice-device>Keep them on this device only</button> '
            + '<button type="button" class="btn-quiet" data-voice-signout hidden>Sign out of Google</button></p>'
            + '<p class="note" data-voice-noclient hidden>Google sign-in has not been switched on for this copy of the site yet, so for now recordings can be kept on this device only.</p>'
            + '<div data-voice-settings hidden><p><label><input type="checkbox" data-voice-show> Show the record and play buttons next to every speaker icon</label></p>'
            + '<p><label><input type="checkbox" data-voice-prefer> Use my friend\'s voice instead of the computer voice when there is a recording</label></p></div></section>'
            + '<section class="blk"><h2>My recordings</h2><div data-voice-list></div></section>'
            + '<section class="blk"><h2>Privacy</h2>' + md(
                "- With Google, each recording is saved as a small audio file in the **hidden app-data folder of your own Google Drive**. "
                "This site asks only for access to that folder (`drive.appdata`): it cannot see, open or change anything else in your Drive, and the files don't appear among your documents.\n"
                "- The site has no server. Your recordings go straight from your browser to your Google Drive and back – they are never sent to the site's authors, never added to the site's code on GitHub and never shared with other learners.\n"
                "- *On this device only* keeps the recordings in this browser's storage instead; clearing the browser's site data deletes them.\n"
                "- Delete any recording above. To remove everything, open Google Drive → Settings → Manage apps → Learn Farsi → *Delete hidden app data*.\n"
                "- Always ask your friend before you record them.") + "</section></div>")
    page("voice/index.html", "Friend's voice", body, desc="Record a Persian-speaking friend and hear their voice on every page – saved privately in your own Google Drive.", section="voice")


def build_offline():
    """offline.html, the web app manifest and the service worker that keeps visited pages and recordings."""
    body = ('<div class="narrow">' + head_block("You're offline", "آفلاین هستید", "āflāyn hastid", None,
            "This page hasn't been saved on this device yet. Every page you open – and every recording you play – is kept, "
            "so the lessons you've already studied still work without a connection. To keep a whole page with all its audio, "
            "press **Save offline** at the top of any lesson, story or article.")
            + '<section class="blk"><h2>Saved on this device</h2><ul class="saved-pages" data-offline-list><li>…</li></ul></section></div>')
    page("offline.html", "Offline", body, section="", depth=0)
    absolute_links("offline.html")
    manifest = {
        "name": "Learn Farsi – Persian from the alphabet to Hafez", "short_name": "Learn Farsi",
        "description": "A free course in Persian (Farsi) from the alphabet to advanced, with audio, stories, culture and tools.",
        "lang": "en", "dir": "ltr", "start_url": "./index.html", "scope": "./", "display": "standalone",
        "background_color": "#f6f8fc", "theme_color": "#1f3a8a",
        "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
                  {"src": "assets/favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
    json.dump(manifest, open(os.path.join(ROOT, "manifest.webmanifest"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8").write(SW_JS.replace("__VER__", ASSET_VER))


SW_JS = r"""/* Learn Farsi service worker – generated by tools/build_site.py.
   Pages: network first, the saved copy when offline. Recordings and fonts: kept once fetched (file names never change).
   Script, stylesheet and data: the saved copy at once, refreshed in the background. */
var VER = "__VER__";
var STATIC = "lf-static-" + VER, PAGES = "lf-pages", AUDIO = "lf-audio", FONTS = "lf-fonts";

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(STATIC).then(function (c) {
    return c.addAll(["offline.html", "assets/style.css?v=" + VER, "assets/app.js?v=" + VER, "assets/voice.js?v=" + VER, "assets/journey.js?v=" + VER, "assets/favicon.svg"]);
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("lf-static-") === 0 && k !== STATIC; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function clean(u) { return u.split("#")[0]; }

function partial(req, res) {
  var range = req.headers.get("range");
  if (!range) return res;
  return res.arrayBuffer().then(function (buf) {
    var size = buf.byteLength, m = /bytes=(\d*)-(\d*)/.exec(range) || [], start = 0, end = size - 1;
    if (m[1]) { start = parseInt(m[1], 10); if (m[2]) end = Math.min(parseInt(m[2], 10), size - 1); }
    else if (m[2]) { start = Math.max(0, size - parseInt(m[2], 10)); }
    return new Response(buf.slice(start, end + 1), { status: 206, statusText: "Partial Content", headers: {
      "Content-Type": res.headers.get("Content-Type") || "audio/mpeg", "Accept-Ranges": "bytes",
      "Content-Range": "bytes " + start + "-" + end + "/" + size, "Content-Length": String(end - start + 1) } });
  });
}

function keep(cacheName, req) {
  var url = clean(req.url);
  return caches.open(cacheName).then(function (c) {
    return c.match(url).then(function (hit) {
      if (hit) return partial(req, hit);
      return fetch(url, { mode: req.mode === "navigate" ? "same-origin" : req.mode, credentials: "omit" }).then(function (res) {
        if (res && (res.status === 200 || res.type === "opaque")) { c.put(url, res.clone()); return partial(req, res); }
        return res;
      });
    });
  });
}

function networkFirst(req) {
  return fetch(req).then(function (res) {
    if (res && res.ok && res.type === "basic") {
      var copy = res.clone();
      caches.open(PAGES).then(function (c) { c.put(clean(req.url), copy); });
    }
    return res;
  }).catch(function () {
    return caches.open(PAGES).then(function (c) { return c.match(clean(req.url), { ignoreSearch: true }); })
      .then(function (hit) { return hit || caches.match("offline.html"); });
  });
}

function fresh(req) {
  return caches.open(STATIC).then(function (c) {
    return c.match(req).then(function (hit) {
      var net = fetch(req).then(function (res) { if (res && res.ok) c.put(req, res.clone()); return res; });
      if (hit) { net.catch(function () {}); return hit; }
      return net;
    });
  });
}

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin === self.location.origin) {
    if (req.mode === "navigate") { e.respondWith(networkFirst(req)); return; }
    if (url.pathname.indexOf("/data/audio/") >= 0) { e.respondWith(keep(AUDIO, req)); return; }
    if (url.pathname.indexOf("/assets/") >= 0 || /\.json$/.test(url.pathname)) { e.respondWith(fresh(req)); return; }
    return;
  }
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") e.respondWith(keep(FONTS, req));
});
"""


def build_404():
    body = ('<div class="narrow">' + head_block("Page not found", "پیدا نشد", "peydā na-shod", None,
            "This page doesn't exist – perhaps it moved when the course grew. Try the [course](course/index.html), the [stories](stories/index.html) or search.") + "</div>")
    page("404.html", "Page not found", body, section="", depth=0)
    absolute_links("404.html")


def absolute_links(path):
    """GitHub Pages serves 404.html (and the service worker serves offline.html) in place of a page at any depth,
    so their links must be absolute."""
    p = os.path.join(ROOT, path)
    s = open(p, encoding="utf-8").read().replace('data-root=""', 'data-root="/Learn-Farsi/"')
    s = s.replace('href="assets/', 'href="/Learn-Farsi/assets/').replace('src="assets/', 'src="/Learn-Farsi/assets/')
    s = re.sub(r'href="(?!https?:|/|#|mailto:)([^"]+)"', r'href="/Learn-Farsi/\1"', s)
    s = s.replace('action="search/', 'action="/Learn-Farsi/search/')
    open(p, "w", encoding="utf-8").write(s)


# ---------------------------------------------------------------------------------------------- home
def build_home(culture_order, news):
    hello = next((e for e in DICT.get("entries", []) if e.get("w") == "سلام"), {})
    levels = []
    for i, lv in enumerate(COURSE.get("levels", [])):
        ready = [l for l in lv.get("lessons", []) if l in LESSONS]
        first = ready[0] if ready else None
        href = f"course/{first}.html" if first else f"course/index.html#{lv['id']}"
        levels.append(f'<li class="step"><a href="{href}"><span class="step-n">{fa_num(i + 1)}</span><span class="step-fa" lang="fa" dir="rtl">{esc(lv.get("fa", ""))}</span>'
                      f'<span class="step-t">{esc(lv.get("name", ""))}</span><span class="step-m">{len(ready)} of {len(lv.get("lessons", []))} lessons ready</span>'
                      f'<span class="step-prog" data-level-lessons="{esc(",".join(ready))}"></span></a></li>')
    feat_stories = [s for s in COURSE.get("stories", []) if s in STORIES]
    pick = []
    for lv in ["A1", "A2", "B1", "B2"]:
        for s in feat_stories:
            if STORIES[s].get("level") == lv and s not in pick:
                pick.append(s)
                break
    pick = (pick + [s for s in feat_stories if s not in pick])[:4]
    story_tiles = "".join(f'<li class="tile"><a href="stories/{s}.html">{thumb(STORIES[s].get("image"), STORIES[s].get("title"))}'
                          f'<span class="tile-fa" lang="fa" dir="rtl">{esc(STORIES[s].get("titleFa", ""))}</span><span class="tile-t">{esc(STORIES[s].get("title", ""))}</span>'
                          f'<span class="tile-m">{esc(LEVEL_NAMES.get(STORIES[s].get("level"), ""))}</span></a></li>' for s in pick)
    topics = "".join(f'<li class="topic"><a href="culture/index.html#{k}">{thumb(img, name)}<span class="topic-fa" lang="fa" dir="rtl">{esc(fa)}</span>'
                     f'<span class="topic-t">{esc(name)}</span><span class="topic-m">{len(culture_order.get(k, []))} articles</span></a></li>'
                     for k, name, fa, r, img, blurb in TOPICS if culture_order.get(k))
    news_rows = "".join(f'<li><a href="news/{S["id"]}.html"><span class="nr-fa" lang="fa" dir="rtl">{esc(S.get("titleFa", ""))}</span>'
                        f'<span class="nr-t">{esc(S.get("title", ""))}</span><span class="nr-d">{esc(S.get("date", ""))}</span></a></li>' for S in news[:4])
    tools = "".join(f'<li><a href="{k}/index.html"><span class="tool-t">{esc(lbl)}</span><span class="tool-m">{esc(m)}</span></a></li>' for k, lbl, m in TOOLS)
    poem = POEMS.get("saadi-bani-adam")
    poem_html = ""
    if poem and poem.get("lines"):
        ln = poem["lines"][0]
        poem_html = (f'<section class="home-poem"><a href="poetry/saadi-bani-adam.html"><p class="hp-fa" lang="fa" dir="rtl">' + "".join(f'<span class="mesra">{esc(h.strip())}</span>' for h in ln["fa"].split(" / "))
                     + f'</p><p class="hp-en">{esc(ln.get("en", ""))}</p><p class="hp-by">Saadi, Golestan, 1258 – read the whole poem</p></a></section>')
    n_words = len(DICT.get("entries", []))
    body = f"""
<section class="hero">
<div class="hero-text">
<h1>Persian, from the first letter to Hafez.</h1>
<p class="hero-sub">A free, open course in Farsi: {len(LESSONS)} lessons with recorded audio, {len(STORIES)} graded {"story" if len(STORIES) == 1 else "stories"}, {len(ARTICLES)} illustrated {"article" if len(ARTICLES) == 1 else "articles"} on Iran's history, places and food, and a 5,000-word dictionary.</p>
<p class="hero-cta"><a class="btn" href="course/{next((l for l in COURSE.get("levels", [{}])[0].get("lessons", []) if l in LESSONS), "index")}.html">Start with the alphabet</a> <a class="btn-quiet" href="course/a1-01-hello.html">I can read – start A1</a></p>
<p class="resume" data-resume></p>
</div>
<div class="hero-word">
<p class="hw-fa" lang="fa" dir="rtl">سلام</p>
<p class="hw-r">salām {say(hello.get("a"), "Listen: salām")}</p>
<p class="hw-en">Hello. Literally <em>peace</em> – the word you'll say most in Iran.</p>
<p class="hw-date" data-today-short></p>
</div>
</section>
<section class="journey-home" data-journey-home hidden></section>
<section class="path"><h2>The path</h2><ol class="steps">{"".join(levels)}</ol></section>
<section class="home-sec"><div class="hs-head"><h2>Read in Persian</h2><a href="stories/index.html">All {len(STORIES)} stories</a></div><ul class="tiles">{story_tiles}</ul></section>
<section class="home-sec"><div class="hs-head"><h2>Iran in pictures and stories</h2><a href="culture/index.html">All {len(ARTICLES)} articles</a></div><ul class="topics">{topics}</ul></section>
<div class="home-two">
<section class="home-news"><div class="hs-head"><h2>This week in simple Persian</h2><a href="news/index.html">All news</a></div><ul class="news-mini">{news_rows}</ul></section>
<section class="home-tools"><div class="wotd" data-wotd hidden></div><h2>Tools</h2><ul class="tools-list">{tools}</ul></section>
</div>
{poem_html}
"""
    page("index.html", "Learn Farsi", body, desc="Learn Persian (Farsi) free: alphabet, 70+ lessons with audio, graded stories, Iranian culture, poetry, news and a 5,000-word dictionary.", image="nasir-al-mulk", section="home", depth=0)


# ---------------------------------------------------------------------------------------------- data files
ZW = "‌"
MARKS = re.compile("[ً-ْٰ]")


def norm(w):
    w = MARKS.sub("", w).replace("ي", "ی").replace("ك", "ک").replace("أ", "ا").replace("إ", "ا")
    return re.sub(r"[.,،؛:؟?!«»\"'()\[\]{}…\-–—]", "", w).strip()


SUFFIXES = sorted(["ها", "های", "هایی", "هایم", "هایت", "هایش", "هایمان", "هایتان", "هایشان", "ی", "یی", "ای", "ام", "ات", "اش", "مان", "تان", "شان",
                   "م", "ت", "ش", "تر", "ترین", "ان", "یان", "گان", "را"], key=len, reverse=True)
ENDINGS = ["م", "ی", "د", "یم", "ید", "ند", ""]


def build_concordance():
    """Persian headword -> up to 3 sentences of this site that use it."""
    heads = {}
    for e in DICT.get("entries", []):
        heads.setdefault(norm(e["w"]), e["n"])
    stems = {}
    for v in (VERBS or {}).get("verbs", []):
        inf = norm(v.get("inf", ""))
        if " " in inf or not inf.endswith("ن"):
            continue
        stems.setdefault(inf[:-1], inf)            # past stem
        st = norm(v.get("stem", ""))
        if st:
            stems.setdefault("P" + st, inf)        # present stem
    for e in DICT.get("entries", []):
        w = norm(e["w"])
        if w.endswith("ن") and "v" in (e.get("p") or "").split(",") and " " not in w:
            stems.setdefault(w[:-1], w)

    def candidates(tok):
        out = {tok}
        t = tok.replace(ZW, "")
        out.add(t)
        parts = tok.split(ZW)
        if len(parts) > 1:
            out.add(parts[0])
        for base in list(out):
            for s in SUFFIXES:
                if base.endswith(s) and len(base) - len(s) >= 2:
                    out.add(base[: -len(s)])
        # verbs
        v = tok
        for pre in ("نمی" + ZW, "می" + ZW, "نمی", "می"):
            if v.startswith(pre):
                core = v[len(pre):]
                for en in sorted(ENDINGS, key=len, reverse=True):
                    if en and core.endswith(en) and len(core) > len(en):
                        c = core[: -len(en)]
                        if "P" + c in stems:
                            out.add(stems["P" + c])
                        if c in stems:
                            out.add(stems[c])
                        if c.endswith("ی") and "P" + c[:-1] in stems:
                            out.add(stems["P" + c[:-1]])
                break
        for neg in ("ن", ""):
            c0 = v[len(neg):] if neg and v.startswith(neg) else v
            for en in sorted(ENDINGS, key=len, reverse=True):
                c = c0[: -len(en)] if en and c0.endswith(en) else (c0 if not en else None)
                if c and c in stems:
                    out.add(stems[c])
            c1 = c0.split(ZW)[0]
            if c1.endswith("ه") and c1[:-1] in stems:
                out.add(stems[c1[:-1]])
        for pre in ("ب", "بی", "نی"):
            if v.startswith(pre):
                core = v[len(pre):]
                for en in sorted(ENDINGS, key=len, reverse=True):
                    if en and core.endswith(en):
                        c = core[: -len(en)]
                        if "P" + c in stems:
                            out.add(stems["P" + c])
        return out
    found = {}
    sent_index = {}
    sents = []
    urls = {}
    for fa, en, a, url, title in SENTS:
        if not fa or not en:
            continue
        toks = [norm(t) for t in fa.split()]
        hits = set()
        for t in toks:
            if not t:
                continue
            for c in candidates(t):
                if c in heads:
                    hits.add(c)
        for h in hits:
            lst = found.setdefault(h, [])
            if len(lst) >= 3:
                continue
            key = (fa, url)
            if key not in sent_index:
                if url not in urls:
                    urls[url] = len(urls)
                sent_index[key] = len(sents)
                sents.append([fa, en, a, urls[url]])
            if sent_index[key] not in lst:
                lst.append(sent_index[key])
    titles = {}
    for fa, en, a, url, title in SENTS:
        titles.setdefault(url, title)
    out = {"u": [[u, titles.get(u, "")] for u, _ in sorted(urls.items(), key=lambda kv: kv[1])], "s": sents,
           "w": {h: v for h, v in found.items()}}
    json.dump(out, open(os.path.join(ASSETS, "concordance.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    # word of the day: common content words that have audio and an example sentence from the course
    wotd = []
    for e in DICT.get("entries", []):
        if e.get("x") or e["n"] < 60 or e["n"] > 2500 or not e.get("a"):
            continue
        if not set((e.get("p") or "").split(",")) & {"n", "v", "adj", "adv"}:
            continue
        refs = found.get(norm(e["w"]))
        if not refs:
            continue
        fa, en, a, ui = sents[refs[0]]
        if len(fa) > 70:
            continue
        wotd.append([e["w"], e["r"], e["g"], e["a"], fa, en, a, out["u"][ui][0], out["u"][ui][1]])
    import random
    random.Random(1405).shuffle(wotd)
    json.dump(wotd[:400], open(os.path.join(ASSETS, "wotd.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return len(found)


def write_data():
    os.makedirs(ASSETS, exist_ok=True)
    # deduplicate search entries
    seen, idx = set(), []
    for e in SEARCH:
        k = (e.get("t"), e.get("fa"), e.get("ti"), e.get("u"))
        if k in seen:
            continue
        seen.add(k)
        idx.append({k2: v for k2, v in e.items() if v})
    json.dump(idx, open(os.path.join(ASSETS, "search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(DECKS, open(os.path.join(ASSETS, "decks.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    n = build_concordance()
    urls = "".join(f"<url><loc>{SITE_URL}{p.replace('index.html', '')}</loc></url>" for p in sorted(set(PAGES)) if p != "404.html")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    return len(idx), n


def main():
    global ASSET_VER
    h = hashlib.sha1()
    for f in ("style.css", "app.js", "voice.js", "journey.js"):
        p = os.path.join(ASSETS, f)
        if os.path.exists(p):
            h.update(open(p, "rb").read())
    ASSET_VER = h.hexdigest()[:8]
    build_lessons()
    build_course_index()
    build_stories()
    culture_order = build_culture()
    build_poetry()
    news = build_news()
    build_phrasebook()
    build_idioms()
    build_grammar()
    build_verbs()
    build_alphabet()
    build_numbers()
    build_dictionary()
    build_flashcards()
    build_search()
    build_about()
    build_home(culture_order, news)
    build_404()
    build_voice()
    build_journey()
    build_offline()
    n_search, n_conc = write_data()
    print(f"Built {len(PAGES)} pages: {len(LESSONS)} lessons, {len(STORIES)} stories, {len(ARTICLES)} articles, {len(POEMS)} poems, "
          f"{len(NEWS.get('stories', []))} news; search {n_search} entries; {len(DECKS)} decks; concordance {n_conc} words.")


if __name__ == "__main__":
    main()
