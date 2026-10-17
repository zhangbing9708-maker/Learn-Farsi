"""Vowel marks for a Persian sentence from its transliteration.

The site's voice (Piper "gyro", via sherpa-onnx) reads Persian letters, and Persian does not write its
short vowels, so every sentence is given to the voice with vowel marks. Instead of asking authors to write
the marks, we derive them from the transliteration (`r`), which does spell every vowel:

    vowelize_sentence("من کتاب می‌خوانم.", "man ketāb mi-khānam.")
      -> ("مَن کِتاب می‌خوانَم.", [])        # (marked sentence, list of tokens that could not be aligned)

Each space-separated token of `fa` is aligned with the token of `r` in the same position (so `r` must have
exactly the same number of spaces as `fa`; use hyphens inside words). The alignment itself is the dynamic
programme in tools/vowelize.py, fed with an IPA-like rendering of the transliteration. Tokens that cannot
be aligned fall back to a lexicon (the dictionary's own vowel-marked headwords) and are otherwise left
unmarked and reported, so tools/check_content.py can list them.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vowelize as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZWNJ = "‌"
MARKS = re.compile("[\\u064e-\\u0652\\u0670]")   # the marks we add (tanvin U+064B is spelling and is kept)
PUNCT = "،؛؟!.,:;\"'«»()[]{}—–-…?/“”‘’"
DIGITS = set("0123456789۰۱۲۳۴۵۶۷۸۹")

# transliteration -> IPA-like sounds that tools/vowelize.py understands
_SUBS = [("cch", "ʧʧ"), ("ssh", "ʃʃ"), ("kkh", "xx"), ("ggh", "ɣɣ"), ("zzh", "ʒʒ"), ("kh", "x"), ("gh", "ɣ"), ("sh", "ʃ"), ("ch", "ʧ"), ("zh", "ʒ"), ("j", "ʤ"), ("y", "j"),
         ("ā", "ɑ"), ("â", "ɑ"), ("aa", "ɑ"), ("ī", "i"), ("ū", "u"), ("a", "æ"), ("q", "ɣ"), ("x", "x"),
         ("'", "ʔ"), ("ʼ", "ʔ"), ("ʻ", "ʔ"), ("’", "ʔ"), ("‘", "ʔ"), ("`", "ʔ")]


def r_to_ipa(r):
    """Site transliteration -> IPA-like string for tools/vowelize.py. Hyphens separate word parts, so a
    digraph never forms across one (ruz-hā is r-u-z-h-ā, not r-u-zh-ā)."""
    out = []
    for part in r.lower().replace("_", "-").split("-"):
        i = 0
        while i < len(part):
            for a, b in _SUBS:
                if part.startswith(a, i):
                    out.append(b)
                    i += len(a)
                    break
            else:
                out.append(part[i])
                i += 1
    return "".join(out)


_DIGRAPH = re.compile("(?<=[a-zāâīū'])(kh|gh|sh|ch|zh)")


def r_variants(r, limit=4):
    """kh gh sh ch zh after a letter can also be two sounds (mazhab = مذهب, as-hāb, eshāgh): the other readings,
    tried only when the usual one does not fit the Persian spelling."""
    spots = [m.start() for m in _DIGRAPH.finditer(r)][:limit]
    out = []
    for mask in range(1, 2 ** len(spots)):
        t = r
        for k in reversed(range(len(spots))):
            if mask >> k & 1:
                i = spots[k]
                t = t[:i + 1] + "-" + t[i + 1:]
        out.append(t)
    return out


_LEX = None


def lexicon():
    """Persian word -> vowel-marked word, from the dictionary, glossary, grammar and alphabet data."""
    global _LEX
    if _LEX is not None:
        return _LEX
    lex = {}

    def add(w, v):
        if w and v and MARKS.search(v) and MARKS.sub("", v) == w and w not in lex:
            lex[w] = v
    p = os.path.join(ROOT, "data", "dict.json")
    if os.path.exists(p):
        for e in json.load(open(p, encoding="utf-8")).get("entries", []):
            add(e.get("w"), e.get("v"))
    p = os.path.join(ROOT, "data", "glossary.json")
    if os.path.exists(p):
        for e in json.load(open(p, encoding="utf-8")).get("entries", {}).values():
            fa = e.get("fa") or {}
            add(fa.get("w"), fa.get("v"))
    p = os.path.join(ROOT, "data", "lexicon.json")   # hand-made additions: {"word": "wordَ"}
    if os.path.exists(p):
        for w, v in json.load(open(p, encoding="utf-8")).items():
            add(w, v)
    _LEX = lex
    return lex


def split_token(tok):
    """'«سلام!»' -> ('«', 'سلام', '!»')"""
    i, j = 0, len(tok)
    while i < j and tok[i] in PUNCT:
        i += 1
    while j > i and tok[j - 1] in PUNCT:
        j -= 1
    return tok[:i], tok[i:j], tok[j:]


APOS = "'ʼ’‘`"


def split_r(tok):
    """Like split_token, for a transliteration: an apostrophe touching a letter is ع/ء, not punctuation
    (tama' = طمع, 'ozv = عضو)."""
    i, j = 0, len(tok)
    while i < j and tok[i] in PUNCT and not (tok[i] in APOS and i + 1 < j and tok[i + 1].isalpha()):
        i += 1
    while j > i and tok[j - 1] in PUNCT and not (tok[j - 1] in APOS and j - 2 >= i and tok[j - 2].isalpha()):
        j -= 1
    return tok[:i], tok[i:j], tok[j:]


def apply_ops(word, ops):
    """Write the marks that an alignment asks for (same conventions as tools/vowelize.py)."""
    L = list(word)
    marks = [""] * len(L)
    for (i, kind, mark) in ops:
        if kind == "cons" and mark:
            marks[i] = mark
        elif kind == "diph":
            if mark and mark != V.FATHA:
                marks[i] = mark
            k = i - 1
            while k >= 0 and L[k] == ZWNJ:
                k -= 1
            if k >= 0 and L[k] != " ":
                marks[k] = (V.SHADDA + V.FATHA) if V.SHADDA in marks[k] else V.FATHA
    return "".join(L[i] + marks[i] for i in range(len(L)))


def vowelize_token(fa, r, threshold=2.6):
    """Return (marked token, ok). `r` may be None (lexicon only)."""
    core = MARKS.sub("", fa)
    if not core or all(c in DIGITS or c in PUNCT for c in core):
        return fa, True
    if len(core) == 1:            # a letter on its own: the voice says its name
        return fa, True
    if r:
        rc = split_r(r)[1]
        for cand in [rc] + r_variants(rc):
            ipa = r_to_ipa(cand)
            if ipa:
                res = V.align(core, ipa)
                if res is not None and res[0] <= threshold:
                    return apply_ops(core, res[1]), True
    lex = lexicon()
    if core in lex:
        return lex[core], True
    # compound joined with ZWNJ: mark each part that the lexicon knows
    if ZWNJ in core:
        parts = core.split(ZWNJ)
        marked = [lex.get(p, p) for p in parts]
        if any(m != p for m, p in zip(marked, parts)):
            return ZWNJ.join(marked), False
    return core, False


def vowelize_sentence(fa, r):
    """Return (marked sentence, problems). problems is a list of 'token' strings that stayed unmarked, or
    ['tokens: fa=N r=M'] when the two strings do not have the same number of words."""
    fa_toks = fa.split()
    r_toks = (r or "").split()
    problems = []
    out = []
    aligned = len(fa_toks) == len(r_toks) and r_toks
    if r and not aligned:
        problems.append(f"tokens: fa={len(fa_toks)} r={len(r_toks)}")
    for i, tok in enumerate(fa_toks):
        pre, core, post = split_token(tok)
        rt = r_toks[i] if aligned else None
        marked, ok = vowelize_token(core, rt)
        if not ok and core and not all(c in DIGITS for c in core):
            problems.append(core)
        out.append(pre + marked + post)
    return " ".join(out), problems


def main():
    if len(sys.argv) >= 3:
        m, p = vowelize_sentence(sys.argv[1], sys.argv[2])
        print(m)
        if p:
            print("problems:", p)
        return
    tests = [
        ("من کتاب می‌خوانم.", "man ketāb mi-khānam."),
        ("خانه‌ی من بزرگ است.", "khāne-ye man bozorg ast."),
        ("اسم شما چیست؟", "esm-e shomā chist?"),
        ("خواهرم در تهران زندگی می‌کند.", "khāhar-am dar Tehrān zendegi mi-konad."),
        ("نوروز مبارک!", "nowruz mobārak!"),
        ("خیلی ممنون، خوبم.", "kheyli mamnun, khub-am."),
        ("او دو برادر دارد.", "u do barādar dārad."),
        ("لطفاً یک چای بدهید.", "lotfan yek chāy bedahid."),
        ("بعد از ظهر به بازار می‌رویم.", "ba'd az zohr be bāzār mi-ravim."),
        ("این‌جا خیلی قشنگ است.", "in-jā kheyli ghashang ast."),
        ("آن‌ها دانش‌آموز هستند.", "ān-hā dānesh-āmuz hastand."),
        ("ساعت چند است؟", "sā'at chand ast?"),
        ("نمی‌دانم.", "nemi-dānam."),
        ("بچه‌ها در حیاط بازی می‌کنند.", "bacche-hā dar hayāt bāzi mi-konand."),
        ("مسئول مدرسه آمد.", "mas'ul-e madrese āmad."),
    ]
    for fa, r in tests:
        m, p = vowelize_sentence(fa, r)
        print(fa, "|", r, "->", m, p or "")


if __name__ == "__main__":
    main()
