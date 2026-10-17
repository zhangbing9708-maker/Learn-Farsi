"""Persian number words, and data/numbers.json for the Numbers page.

usage: python3 tools/numbers.py            writes data/numbers.json (then run make_audio.py)
       python3 tools/numbers.py 1405       prints the words for a number

The same rules are implemented in assets/app.js for the converter on the page.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONES = [("", ""), ("یک", "yek"), ("دو", "do"), ("سه", "se"), ("چهار", "chahār"), ("پنج", "panj"), ("شش", "shesh"),
        ("هفت", "haft"), ("هشت", "hasht"), ("نه", "noh")]
TEENS = [("ده", "dah"), ("یازده", "yāzdah"), ("دوازده", "davāzdah"), ("سیزده", "sizdah"), ("چهارده", "chahārdah"),
         ("پانزده", "pānzdah"), ("شانزده", "shānzdah"), ("هفده", "hefdah"), ("هجده", "hejdah"), ("نوزده", "nuzdah")]
TENS = [("", ""), ("", ""), ("بیست", "bist"), ("سی", "si"), ("چهل", "chehel"), ("پنجاه", "panjāh"), ("شصت", "shast"),
        ("هفتاد", "haftād"), ("هشتاد", "hashtād"), ("نود", "navad")]
HUNDREDS = [("", ""), ("صد", "sad"), ("دویست", "devist"), ("سیصد", "sisad"), ("چهارصد", "chahārsad"), ("پانصد", "pānsad"),
            ("ششصد", "sheshsad"), ("هفتصد", "haftsad"), ("هشتصد", "hashtsad"), ("نهصد", "nohsad")]
SCALES = [("", ""), ("هزار", "hezār"), ("میلیون", "milyun"), ("میلیارد", "milyārd"), ("تریلیون", "teriliyun")]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def below_1000(n):
    parts = []
    h, rest = divmod(n, 100)
    if h:
        parts.append(HUNDREDS[h])
    if 10 <= rest < 20:
        parts.append(TEENS[rest - 10])
    else:
        t, o = divmod(rest, 10)
        if t:
            parts.append(TENS[t])
        if o:
            parts.append(ONES[o])
    return parts


def words(n):
    """Return (Persian, transliteration) for an integer, e.g. 1405 -> ('هزار و چهارصد و پنج', 'hezār o chahārsad o panj')."""
    if n == 0:
        return "صفر", "sefr"
    neg = n < 0
    n = abs(n)
    groups = []
    i = 0
    while n:
        n, g = divmod(n, 1000)
        if g:
            ws = below_1000(g)
            if i:
                if i == 1 and g == 1:
                    ws = []          # 1000 is هزار, not یک هزار
                ws = [(" ".join(w[0] for w in ws), " ".join(w[1] for w in ws))] if ws else []
                ws = [(" ".join(x for x in [ws[0][0] if ws else "", SCALES[i][0]] if x),
                       " ".join(x for x in [ws[0][1] if ws else "", SCALES[i][1]] if x))]
            groups.append(ws)
        i += 1
    flat = [w for g in reversed(groups) for w in g]
    fa = " و ".join(w[0] for w in flat)
    r = " o ".join(w[1] for w in flat)
    if neg:
        fa, r = "منفی " + fa, "manfi " + r
    return fa, r


def ordinal(n):
    fa, r = words(n)
    if n == 1:
        return "اول", "avval"
    if fa.endswith("سه"):
        return fa[:-2] + "سوم", r[:-2] + "sevvom"
    if fa.endswith("دو") and not fa.endswith("ودو"):
        return fa[:-2] + "دوم", r[:-2] + "dovvom"
    if fa.endswith("سی"):
        return fa + "‌ام", r + "-om"
    return fa + "م", r + "om"


def build():
    def item(n, label=None):
        fa, r = words(n)
        return {"n": label or f"{n:,}", "fa": fa, "r": r}
    groups = [
        {"title": "0 to 20", "items": [item(n) for n in range(0, 21)]},
        {"title": "Tens, and how to join them with o ('and')", "items": [item(n) for n in (30, 40, 50, 60, 70, 80, 90, 21, 35, 47, 58, 99)]},
        {"title": "Hundreds", "items": [item(n) for n in range(100, 1000, 100)] + [item(n) for n in (101, 250, 365, 999)]},
        {"title": "Thousands and more", "items": [item(n) for n in (1000, 2000, 10000, 100000, 1000000, 1000000000, 1404, 1405, 2026, 1979, 12500, 2500000)]},
        {"title": "Ordinals: first, second, third…", "items": [
            {"n": f"{n}{'st' if n % 10 == 1 and n != 11 else 'nd' if n % 10 == 2 and n != 12 else 'rd' if n % 10 == 3 and n != 13 else 'th'}",
             "fa": ordinal(n)[0], "r": ordinal(n)[1]} for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 21, 30, 100)]
            + [{"n": "the first", "fa": "اولین", "r": "avvalin"}, {"n": "the second", "fa": "دومین", "r": "dovvomin"},
               {"n": "the last", "fa": "آخرین", "r": "ākharin"}]},
        {"title": "Parts and amounts", "items": [
            {"n": "½", "fa": "نصف", "r": "nesf"}, {"n": "half (with a unit)", "fa": "نیم", "r": "nim"},
            {"n": "1½ hours", "fa": "یک ساعت و نیم", "r": "yek sā'at o nim"}, {"n": "¼", "fa": "یک چهارم", "r": "yek chahārom"},
            {"n": "quarter past", "fa": "و ربع", "r": "o rob'"}, {"n": "⅓", "fa": "یک سوم", "r": "yek sevvom"},
            {"n": "10%", "fa": "ده درصد", "r": "dah darsad"}, {"n": "0.5", "fa": "صفر ممیز پنج", "r": "sefr momayyez panj"},
            {"n": "a dozen", "fa": "یک دوجین", "r": "yek dujin"}, {"n": "twice", "fa": "دو بار", "r": "do bār"},
            {"n": "double", "fa": "دو برابر", "r": "do barābar"}, {"n": "how many?", "fa": "چند تا؟", "r": "chand tā?"}]},
    ]
    for g in groups:
        for it in g["items"]:
            it["nFa"] = str(it["n"]).translate(FA_DIGITS)
    path = os.path.join(ROOT, "data", "numbers.json")
    old = {}
    if os.path.exists(path):
        for g in json.load(open(path, encoding="utf-8")).get("groups", []):
            for it in g["items"]:
                old[it["fa"]] = {k: it[k] for k in ("faV", "a") if k in it}
    for g in groups:
        for it in g["items"]:
            it.update(old.get(it["fa"], {}))
    json.dump({"groups": groups}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{sum(len(g['items']) for g in groups)} numbers -> data/numbers.json")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
        print(words(n), ordinal(n))
    else:
        build()
