"""Check the content of Learn Farsi.

usage:
  python3 tools/check_content.py              check everything; prints OK or the problems
  python3 tools/check_content.py --images     list the image keys of data/images.json
  python3 tools/check_content.py --stats      count lessons, stories, sentences, words
  python3 tools/check_content.py FILE...      check only these files (warnings in full)

Errors (block publishing): invalid JSON, missing fields, bad ids, Arabic ي/ك, exercises that cannot be
played, a different number of words in `fa` and `r`, unknown image keys, lessons missing from course.json.
Warnings: words whose vowel marks could not be derived from the transliteration (the audio may be
mispronounced; fix the `r` or add the word to data/lexicon.json), spaces after می, very short lessons.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vowelize_text import vowelize_sentence, split_token, DIGITS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
LEVELS = ["script", "A1", "A2", "B1", "B2", "C1"]
TOPICS = {"history", "places", "food", "festivals", "arts", "people", "language", "life"}
KINDS = {"folk tale", "fable", "legend", "everyday life", "history", "biography", "humour", "travel", "dialogue", "news"}
BLOCKS = {"text", "vocab", "dialogue", "grammar", "reading", "culture", "tips", "letters", "exercise", "image"}
EXERCISES = {"mcq", "fill", "translate", "match", "order", "listen"}
POS = {"n", "v", "adj", "adv", "pron", "prep", "conj", "num", "phrase", "name", "interj", "part", "det"}
ARABIC = re.compile("[يك٠-٩]")
PERSIAN = re.compile("[؀-ۿ]")
LATIN_IN_FA = re.compile("[A-Za-z]")
INLINE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]|]*))?(?:\|([^\]]*))?\]\]")

errors, warnings = [], []


def err(f, msg):
    errors.append(f"{os.path.relpath(f, ROOT)}: {msg}")


def warn(f, msg):
    warnings.append(f"{os.path.relpath(f, ROOT)}: {msg}")


def images():
    p = os.path.join(ROOT, "data", "images.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def check_fa_text(f, s, where):
    if ARABIC.search(s):
        err(f, f"{where}: Arabic letter/digit in Persian text: {s!r}")
    if re.search(r"(^|\s)ن?می\s+\S", s) and "می " not in ("می ",):
        warn(f, f"{where}: space after می – use ZWNJ: {s!r}")


def check_sentence(f, obj, where, need_r=True):
    fa = obj.get("fa")
    if not isinstance(fa, str) or not fa.strip():
        err(f, f"{where}: missing fa")
        return
    check_fa_text(f, fa, where)
    if LATIN_IN_FA.search(fa) and "___" not in fa:
        warn(f, f"{where}: Latin letters inside Persian text: {fa!r}")
    r = obj.get("r")
    if need_r and not (isinstance(r, str) and r.strip()):
        err(f, f"{where}: missing r for {fa!r}")
        return
    if isinstance(r, str):
        if PERSIAN.search(r):
            err(f, f"{where}: Persian letters in r: {r!r}")
        if "___" in fa:
            if fa.count("___") != 1 or r.count("___") != 1:
                err(f, f"{where}: fill-in needs exactly one ___ in fa and r: {fa!r} / {r!r}")
        else:
            v, probs = vowelize_sentence(fa, r)
            for p in probs:
                if p.startswith("tokens:"):
                    err(f, f"{where}: word count differs ({p}): {fa!r} / {r!r}")
                else:
                    warn(f, f"{where}: cannot vowel-mark {p!r} from r in {fa!r} / {r!r}")
    if "col" in obj:
        col, colR = obj.get("col"), obj.get("colR")
        if not isinstance(col, str) or not isinstance(colR, str):
            err(f, f"{where}: col needs colR")
        else:
            check_fa_text(f, col, where + " col")
            v, probs = vowelize_sentence(col, colR)
            for p in probs:
                if p.startswith("tokens:"):
                    err(f, f"{where} col: word count differs ({p}): {col!r} / {colR!r}")
                else:
                    warn(f, f"{where} col: cannot vowel-mark {p!r} in {col!r} / {colR!r}")
    en = obj.get("en")
    if need_r and not (isinstance(en, str) and en.strip()):
        err(f, f"{where}: missing en for {fa!r}")


def check_md(f, md, where):
    if not isinstance(md, str):
        err(f, f"{where}: md must be a string")
        return
    if md.count("[[") != md.count("]]"):
        err(f, f"{where}: unbalanced [[ ]] in md")
    for m in INLINE.finditer(md):
        check_fa_text(f, m.group(1), where + " inline")


def check_image(f, key, where, imgs):
    if key is None:
        return
    if not isinstance(key, str):
        err(f, f"{where}: image must be a string key")
    elif imgs and key not in imgs:
        err(f, f"{where}: unknown image key {key!r}")


def check_exercise(f, b, where):
    kind = b.get("kind")
    if kind not in EXERCISES:
        err(f, f"{where}: unknown exercise kind {kind!r}")
        return
    items = b.get("items")
    if not isinstance(items, list) or not items:
        err(f, f"{where}: exercise without items")
        return
    for i, it in enumerate(items):
        w = f"{where} item {i + 1}"
        if not isinstance(it, dict):
            err(f, f"{w}: must be an object")
            continue
        if kind == "mcq":
            if not isinstance(it.get("q"), str):
                err(f, f"{w}: mcq needs q")
            opts = it.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                err(f, f"{w}: mcq needs 2+ options")
            elif not isinstance(it.get("answer"), int) or not (0 <= it["answer"] < len(opts)):
                err(f, f"{w}: mcq answer out of range")
            for o in opts or []:
                if isinstance(o, str):
                    check_fa_text(f, o, w)
        elif kind == "fill":
            check_sentence(f, it, w)
            if not isinstance(it.get("answer"), str) or not it["answer"].strip():
                err(f, f"{w}: fill needs answer")
            else:
                check_fa_text(f, it["answer"], w)
        elif kind == "listen":
            check_sentence(f, it, w)
            opts = it.get("options")
            if not isinstance(opts, list) or len(opts) < 2 or not isinstance(it.get("answer"), int) or not (0 <= it["answer"] < len(opts)):
                err(f, f"{w}: listen needs options and a valid answer")
        else:  # translate, match, order
            check_sentence(f, it, w)
            if kind == "order" and len(it["fa"].split()) < 3:
                warn(f, f"{w}: order exercise with fewer than 3 words")


def check_lesson(f, d, imgs):
    for k in ("id", "level", "n", "title", "titleFa", "titleR", "intro", "goals", "sections"):
        if k not in d:
            err(f, f"lesson missing {k}")
    if errors and errors[-1].startswith(os.path.relpath(f, ROOT)) and "missing" in errors[-1]:
        return
    if d["level"] not in LEVELS:
        err(f, f"bad level {d['level']!r}")
    base = os.path.basename(f)[:-5]
    if d["id"] != base:
        err(f, f"id {d['id']!r} does not match file name")
    if not re.match(r"^(script|a1|a2|b1|b2|c1)-\d\d-[a-z0-9-]+$", d["id"]):
        err(f, f"id {d['id']!r} must look like a1-03-family")
    check_sentence(f, {"fa": d["titleFa"], "r": d["titleR"], "en": d["title"]}, "title")
    check_image(f, d.get("image"), "lesson image", imgs)
    if not isinstance(d["goals"], list) or not d["goals"]:
        err(f, "goals must be a non-empty list")
    secs = d["sections"]
    if not isinstance(secs, list) or len(secs) < 4:
        err(f, "a lesson needs at least 4 sections")
        return
    n_ex = n_vocab = 0
    for i, b in enumerate(secs):
        w = f"section {i + 1} ({b.get('type')})"
        t = b.get("type")
        if t not in BLOCKS:
            err(f, f"{w}: unknown block type {t!r}")
            continue
        if t in ("text", "culture"):
            check_md(f, b.get("md"), w)
            check_image(f, b.get("image"), w, imgs)
        elif t == "image":
            check_image(f, b.get("image"), w, imgs)
        elif t == "vocab":
            items = b.get("items")
            if not isinstance(items, list) or not items:
                err(f, f"{w}: vocab without items")
                continue
            n_vocab += len(items)
            for j, it in enumerate(items):
                check_sentence(f, it, f"{w} word {j + 1}")
                if it.get("pos") and it["pos"] not in POS:
                    warn(f, f"{w} word {j + 1}: unusual pos {it['pos']!r}")
                if isinstance(it.get("ex"), dict):
                    check_sentence(f, it["ex"], f"{w} word {j + 1} ex")
        elif t == "dialogue":
            lines = b.get("lines")
            if not isinstance(lines, list) or len(lines) < 2:
                err(f, f"{w}: dialogue needs lines")
                continue
            for j, ln in enumerate(lines):
                if not ln.get("who"):
                    err(f, f"{w} line {j + 1}: missing who")
                check_sentence(f, ln, f"{w} line {j + 1}")
        elif t == "grammar":
            check_md(f, b.get("md"), w)
            tb = b.get("table")
            if tb is not None:
                if not isinstance(tb, dict) or not isinstance(tb.get("rows"), list):
                    err(f, f"{w}: table needs rows")
                else:
                    for row in tb["rows"]:
                        for cell in row:
                            if isinstance(cell, str):
                                check_fa_text(f, cell, w + " table")
                                if cell.count("[[") != cell.count("]]"):
                                    err(f, f"{w}: unbalanced [[ ]] in table cell {cell!r}")
            for j, ex in enumerate(b.get("examples") or []):
                check_sentence(f, ex, f"{w} example {j + 1}")
        elif t == "reading":
            sents = b.get("sentences")
            if not isinstance(sents, list) or not sents:
                err(f, f"{w}: reading without sentences")
                continue
            for j, s in enumerate(sents):
                check_sentence(f, s, f"{w} sentence {j + 1}")
            for j, q in enumerate(b.get("questions") or []):
                if not isinstance(q.get("options"), list) or not isinstance(q.get("answer"), int):
                    err(f, f"{w} question {j + 1}: needs options and answer")
        elif t == "tips":
            if not isinstance(b.get("items"), list) or not b["items"]:
                err(f, f"{w}: tips without items")
        elif t == "letters":
            if not isinstance(b.get("letters"), list) or not b["letters"]:
                err(f, f"{w}: letters block without letters")
            if b.get("md") is not None:
                check_md(f, b["md"], w)
        elif t == "exercise":
            n_ex += 1
            check_exercise(f, b, w)
    if n_ex < 2:
        warn(f, f"only {n_ex} exercise blocks")
    if n_vocab < 6 and d["level"] != "script":
        warn(f, f"only {n_vocab} vocabulary items")


def check_story(f, d, imgs):
    for k in ("id", "level", "kind", "title", "titleFa", "titleR", "intro", "paragraphs", "vocab", "questions"):
        if k not in d:
            err(f, f"story missing {k}")
            return
    if d["id"] != os.path.basename(f)[:-5]:
        err(f, "id does not match file name")
    if d["level"] not in LEVELS[1:]:
        err(f, f"bad level {d['level']!r}")
    if d["kind"] not in KINDS:
        warn(f, f"unusual kind {d['kind']!r}")
    check_sentence(f, {"fa": d["titleFa"], "r": d["titleR"], "en": d["title"]}, "title")
    check_image(f, d.get("image"), "image", imgs)
    n = 0
    for i, p in enumerate(d["paragraphs"]):
        sents = p.get("sentences") if isinstance(p, dict) else None
        if not isinstance(sents, list) or not sents:
            err(f, f"paragraph {i + 1}: needs sentences")
            continue
        for j, s in enumerate(sents):
            check_sentence(f, s, f"paragraph {i + 1} sentence {j + 1}")
            n += len(s.get("fa", "").split())
    for j, it in enumerate(d["vocab"]):
        check_sentence(f, it, f"vocab {j + 1}")
    for j, q in enumerate(d["questions"]):
        if not isinstance(q.get("options"), list) or not isinstance(q.get("answer"), int) or not (0 <= q["answer"] < len(q["options"])):
            err(f, f"question {j + 1}: needs options and a valid answer")
    lo = {"A1": 30, "A2": 90, "B1": 200, "B2": 350, "C1": 500}[d["level"]]
    if n < lo:
        warn(f, f"{d['level']} story has only {n} words")


def check_article(f, d, imgs):
    for k in ("id", "topic", "title", "titleFa", "titleR", "summary", "body", "sentences", "vocab"):
        if k not in d:
            err(f, f"article missing {k}")
            return
    if d["id"] != os.path.basename(f)[:-5]:
        err(f, "id does not match file name")
    if d["topic"] not in TOPICS:
        err(f, f"bad topic {d['topic']!r}")
    check_sentence(f, {"fa": d["titleFa"], "r": d["titleR"], "en": d["title"]}, "title")
    check_image(f, d.get("image"), "image", imgs)
    words = 0
    for i, sec in enumerate(d["body"]):
        if not isinstance(sec, dict) or not isinstance(sec.get("md"), str):
            err(f, f"body {i + 1}: needs md")
            continue
        check_md(f, sec["md"], f"body {i + 1}")
        check_image(f, sec.get("image"), f"body {i + 1}", imgs)
        words += len(sec["md"].split())
    if words < 200:
        warn(f, f"article body has only {words} words")
    for j, s in enumerate(d["sentences"]):
        check_sentence(f, s, f"sentence {j + 1}")
    for j, it in enumerate(d["vocab"]):
        check_sentence(f, it, f"vocab {j + 1}")


def check_poem(f, d, imgs):
    for k in ("id", "poet", "poetFa", "title", "titleFa", "intro", "lines", "commentary"):
        if k not in d:
            err(f, f"poem missing {k}")
            return
    if d["id"] != os.path.basename(f)[:-5]:
        err(f, "id does not match file name")
    check_image(f, d.get("image"), "image", imgs)
    if d.get("titleR"):
        check_sentence(f, {"fa": d["titleFa"], "r": d["titleR"], "en": d["title"]}, "title")
    for j, ln in enumerate(d["lines"]):
        check_sentence(f, ln, f"line {j + 1}")
        for w in ln.get("words") or []:
            if not (isinstance(w, list) and len(w) == 3):
                err(f, f"line {j + 1}: words must be [fa, r, en] triples")
            else:
                check_fa_text(f, w[0], f"line {j + 1} word")


def check_phrasebook(f, d):
    for i, sec in enumerate(d.get("sections", [])):
        w = f"section {i + 1}"
        for k in ("id", "title", "titleFa", "titleR", "items"):
            if k not in sec:
                err(f, f"{w}: missing {k}")
        if "titleFa" in sec and "titleR" in sec:
            check_sentence(f, {"fa": sec["titleFa"], "r": sec["titleR"], "en": sec.get("title", "")}, w + " title")
        for j, it in enumerate(sec.get("items", [])):
            check_sentence(f, it, f"{w} item {j + 1}")


def check_idioms(f, d):
    for j, it in enumerate(d.get("items", [])):
        check_sentence(f, it, f"item {j + 1}")
        if not it.get("lit"):
            warn(f, f"item {j + 1}: no literal meaning")
        if isinstance(it.get("ex"), dict):
            check_sentence(f, it["ex"], f"item {j + 1} ex")


def check_verbs(f, d):
    seen = set()
    for j, v in enumerate(d.get("verbs", [])):
        for k in ("inf", "r", "stem", "stemR", "en"):
            if k not in v:
                err(f, f"verb {j + 1}: missing {k}")
        if v.get("inf") in seen:
            err(f, f"verb {j + 1}: duplicate {v['inf']}")
        seen.add(v.get("inf"))
        if "inf" in v and "r" in v:
            check_sentence(f, {"fa": v["inf"], "r": v["r"], "en": v.get("en", "")}, f"verb {j + 1}")
            check_sentence(f, {"fa": v["stem"], "r": v["stemR"], "en": "stem"}, f"verb {j + 1} stem")
        if isinstance(v.get("ex"), dict):
            check_sentence(f, v["ex"], f"verb {j + 1} ex")


def check_news(f, d):
    for i, s in enumerate(d.get("stories", [])):
        w = f"story {i + 1}"
        for k in ("id", "date", "title", "titleFa", "titleR", "level", "sentences", "vocab", "source", "url"):
            if k not in s:
                err(f, f"{w}: missing {k}")
        if "titleFa" in s:
            check_sentence(f, {"fa": s["titleFa"], "r": s.get("titleR", ""), "en": s.get("title", "")}, w + " title")
        for j, sent in enumerate(s.get("sentences", [])):
            check_sentence(f, sent, f"{w} sentence {j + 1}")
        for j, it in enumerate(s.get("vocab", [])):
            check_sentence(f, it, f"{w} vocab {j + 1}")


def check_course(f, d, lesson_ids):
    listed = []
    for lv in d.get("levels", []):
        for lid in lv.get("lessons", []):
            listed.append(lid)
            if lid not in lesson_ids:
                warn(f, f"course lists a lesson that is not written yet: {lid}")
    for lid in lesson_ids:
        if lid not in listed:
            err(f, f"lesson {lid} is not in course.json")
    if len(set(listed)) != len(listed):
        err(f, "course lists a lesson twice")
    for group, ids in [("stories", d.get("stories", []))] + [("culture/" + t, v) for t, v in d.get("culture", {}).items()] + [("poems", d.get("poems", []))]:
        folder = group.split("/")[0]
        for i in ids:
            if not os.path.exists(os.path.join(CONTENT, folder, i + ".json")):
                warn(f, f"{group}: not written yet: {i}")


def load(f):
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(f, f"invalid JSON: {e}")
        return None


def stats(files):
    n = {"lessons": 0, "stories": 0, "articles": 0, "poems": 0, "sentences": 0, "fa_words": 0, "en_words": 0}

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("fa"), str) and isinstance(x.get("r"), str):
                n["sentences"] += 1
                n["fa_words"] += len(x["fa"].split())
            for k, v in x.items():
                if isinstance(v, str) and k in ("en", "md", "intro", "summary", "commentary", "after", "note", "context"):
                    n["en_words"] += len(v.split())
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for f in files:
        d = load(f)
        if d is None:
            continue
        if "/lessons/" in f:
            n["lessons"] += 1
        elif "/stories/" in f:
            n["stories"] += 1
        elif "/culture/" in f:
            n["articles"] += 1
        elif "/poems/" in f:
            n["poems"] += 1
        walk(d)
    for k, v in n.items():
        print(f"{k:10} {v:>8,}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--images" in sys.argv:
        for k, v in sorted(images().items()):
            print(f"{k:32} {v.get('caption', '')[:70]}")
        return
    files = args or sorted(glob.glob(os.path.join(CONTENT, "**", "*.json"), recursive=True))
    if "--stats" in sys.argv:
        stats(files)
        return
    imgs = images()
    lesson_ids = set()
    course = None
    for f in files:
        d = load(f)
        if d is None:
            continue
        rel = os.path.relpath(f, CONTENT)
        if rel.startswith("lessons/"):
            check_lesson(f, d, imgs)
            if isinstance(d, dict) and d.get("id"):
                lesson_ids.add(d["id"])
        elif rel.startswith("stories/"):
            check_story(f, d, imgs)
        elif rel.startswith("culture/"):
            check_article(f, d, imgs)
        elif rel.startswith("poems/"):
            check_poem(f, d, imgs)
        elif rel == "phrasebook.json":
            check_phrasebook(f, d)
        elif rel == "idioms.json":
            check_idioms(f, d)
        elif rel == "verbs.json":
            check_verbs(f, d)
        elif rel == "news.json":
            check_news(f, d)
        elif rel == "course.json":
            course = (f, d)
        else:
            warn(f, "unknown content file")
    if course and not args:
        check_course(course[0], course[1], lesson_ids)
    for w in warnings[: (len(warnings) if args else 60)]:
        print("warning:", w)
    if len(warnings) > 60 and not args:
        print(f"... {len(warnings) - 60} more warnings")
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"{len(errors)} errors, {len(warnings)} warnings")
        sys.exit(1)
    print(f"OK ({len(files)} files, {len(warnings)} warnings)")


if __name__ == "__main__":
    main()
