"""Write the whole course as a Markdown book in book/, readable directly on GitHub.

usage: python3 tools/build_book.py

book/README.md is the table of contents; every lesson, story, article and poem gets its own chapter file.
The website (built by tools/build_site.py) has the audio and interactive exercises; the book has everything
else, with answers to the exercises in collapsible blocks.
"""
import glob
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.path.join(ROOT, "book")
SITE = "https://zhangbing9708-maker.github.io/Learn-Farsi/"
INLINE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]|]*))?(?:\|([^\]]*))?\]\]")


def load(p, d=None):
    p = os.path.join(ROOT, p)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d


def load_dir(folder):
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "content", folder, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
            out[d.get("id") or os.path.basename(p)[:-5]] = d
        except Exception:  # noqa: BLE001
            pass
    return out


COURSE = load("content/course.json", {})
LESSONS, STORIES, ARTICLES, POEMS = load_dir("lessons"), load_dir("stories"), load_dir("culture"), load_dir("poems")
IMAGES = load("data/images.json", {})
LEVELS = {"script": "The script", "A1": "Beginner (A1)", "A2": "Elementary (A2)", "B1": "Intermediate (B1)", "B2": "Upper intermediate (B2)", "C1": "Advanced (C1)"}
TOPICS = [("history", "History"), ("places", "Places"), ("food", "Food"), ("festivals", "Festivals"), ("arts", "Arts"),
          ("people", "People"), ("language", "Language"), ("life", "Everyday life")]


def inl(s):
    def rep(m):
        fa, r, g = m.group(1).strip(), (m.group(2) or "").strip(), (m.group(3) or "").strip()
        extra = ", ".join(x for x in [f"*{r}*" if r else "", f"‘{g}’" if g else ""] if x)
        return f"{fa} ({extra})" if extra else fa
    return INLINE.sub(rep, str(s or ""))


def cellmd(s):
    return inl(s).replace("|", "\\|").replace("\n", " ")


def photo(key):
    im = IMAGES.get(key or "")
    if not im:
        return ""
    return f"![{im['caption']}]({im['url']})\n<sub>{im['caption']}. Photo: [{im['artist']}]({im['page']}), {im['license']}.</sub>\n\n"


def sentence(s, who=None):
    out = f"- {'**' + who + ':** ' if who else ''}{s.get('fa', '')}  \n  *{s.get('r', '')}* — {inl(s.get('en', ''))}"
    if s.get("col"):
        out += f"  \n  Spoken: {s['col']} *{s.get('colR', '')}*"
    if s.get("lit"):
        out += f"  \n  Literally: {inl(s['lit'])}"
    if s.get("note"):
        out += f"  \n  _{inl(s['note'])}_"
    return out + "\n"


def vocab(items):
    rows = ["| Persian | Pronunciation | Meaning | Notes |", "| --- | --- | --- | --- |"]
    for it in items:
        note = " ".join(x for x in [it.get("pos", ""), inl(it.get("note", ""))] if x)
        if isinstance(it.get("ex"), dict) and it["ex"].get("fa"):
            note += f" — e.g. {it['ex']['fa']} (*{it['ex'].get('r', '')}*, {inl(it['ex'].get('en', ''))})"
        rows.append(f"| {cellmd(it.get('fa', ''))} | *{cellmd(it.get('r', ''))}* | {cellmd(it.get('en', ''))} | {cellmd(note)} |")
    return "\n".join(rows) + "\n\n"


def table(tb):
    head = tb.get("head") or [""] * len((tb.get("rows") or [[]])[0])
    out = ["| " + " | ".join(cellmd(h) for h in head) + " |", "|" + " --- |" * len(head)]
    for row in tb.get("rows", []):
        out.append("| " + " | ".join(cellmd(c) for c in row) + " |")
    return "\n".join(out) + "\n\n"


def exercise(b):
    kind, items = b.get("kind"), b.get("items", [])
    q, a = [], []
    for i, it in enumerate(items, 1):
        if kind == "mcq":
            opts = " / ".join(it.get("options", []))
            q.append(f"{i}. {inl(it.get('q', ''))} — {opts}")
            ans = it.get("options", [""])[it.get("answer", 0)] if it.get("options") else ""
            a.append(f"{i}. {ans}" + (f" — {inl(it.get('explain'))}" if it.get("explain") else ""))
        elif kind == "fill":
            q.append(f"{i}. {it.get('fa', '')} (*{it.get('r', '')}*) — {it.get('en', '')}" + (f" (hint: {it['hint']})" if it.get("hint") else ""))
            a.append(f"{i}. {it.get('answer', '')}")
        elif kind == "translate":
            q.append(f"{i}. {it.get('en', '')}")
            a.append(f"{i}. {it.get('fa', '')} — *{it.get('r', '')}*")
        elif kind == "order":
            words = sorted(it.get("fa", "").split(), key=lambda w: hash(w) % 97)
            q.append(f"{i}. {' / '.join(words)} — {it.get('en', '')}")
            a.append(f"{i}. {it.get('fa', '')}")
        elif kind == "match":
            q.append(f"{i}. {it.get('fa', '')} — ?")
            a.append(f"{i}. {it.get('fa', '')} = {it.get('en', '')}")
        elif kind == "listen":
            q.append(f"{i}. (Listen on the website.) {' / '.join(it.get('options', []))}")
            a.append(f"{i}. {it.get('fa', '')} — {it.get('en', '')}")
    title = {"mcq": "Choose the right answer", "fill": "Fill in the missing word", "translate": "Say it in Persian",
             "order": "Put the words in order", "match": "Give the meaning", "listen": "Listening"}.get(kind, "Practice")
    return (f"**{title}**\n\n" + "\n".join(q) + "\n\n<details><summary>Answers</summary>\n\n" + "\n".join(a) + "\n\n</details>\n\n")


def lesson_md(L, prev_id, next_id):
    lv = LEVELS.get(L.get("level"), "")
    out = [f"# {L.get('title')}\n", f"## {L.get('titleFa', '')}\n", f"*{L.get('titleR', '')}* — {lv}, lesson {L.get('n', '')}. "
           f"[Open this lesson with audio and interactive exercises]({SITE}course/{L['id']}.html)\n\n", inl(L.get("intro", "")) + "\n\n"]
    if L.get("goals"):
        out.append("**In this lesson you will learn to:**\n\n" + "\n".join(f"- {inl(g)}" for g in L["goals"]) + "\n\n")
    out.append(photo(L.get("image")))
    for b in L.get("sections", []):
        t = b.get("type")
        if b.get("title"):
            out.append(f"### {inl(b['title'])}\n\n")
        if t in ("text", "culture"):
            out.append(inl(b.get("md", "")) + "\n\n" + photo(b.get("image")))
        elif t == "vocab":
            out.append(vocab(b.get("items", [])))
        elif t == "dialogue":
            if b.get("context"):
                out.append(f"_{inl(b['context'])}_\n\n")
            out.append("".join(sentence(ln, ln.get("who")) for ln in b.get("lines", [])) + "\n")
        elif t == "grammar":
            out.append(inl(b.get("md", "")) + "\n\n")
            if isinstance(b.get("table"), dict):
                out.append(table(b["table"]))
            out.append("".join(sentence(e) for e in b.get("examples") or []) + "\n")
        elif t == "reading":
            if b.get("intro"):
                out.append(f"_{inl(b['intro'])}_\n\n")
            out.append("".join(sentence(s) for s in b.get("sentences", [])) + "\n")
            if b.get("questions"):
                out.append(exercise({"kind": "mcq", "items": b["questions"]}))
        elif t == "tips":
            out.append("\n".join(f"- {inl(x)}" for x in b.get("items", [])) + "\n\n")
        elif t == "letters":
            out.append(inl(b.get("md", "")) + "\n\n" + "  ".join(f"**{g}**" for g in b.get("letters", [])) + "\n\n")
        elif t == "exercise":
            out.append(exercise(b))
    nav = []
    if prev_id:
        nav.append(f"← [{LESSONS[prev_id]['title']}]({prev_id}.md)")
    nav.append("[Contents](../README.md)")
    if next_id:
        nav.append(f"[{LESSONS[next_id]['title']}]({next_id}.md) →")
    out.append("---\n\n" + " · ".join(nav) + "\n")
    return "".join(out)


def story_md(S):
    out = [f"# {S.get('title')}\n", f"## {S.get('titleFa', '')}\n", f"*{S.get('titleR', '')}* — {LEVELS.get(S.get('level'), '')}, {S.get('kind', '')}. "
           f"[Read with audio]({SITE}stories/{S['id']}.html)\n\n", inl(S.get("intro", "")) + "\n\n", photo(S.get("image"))]
    out.append("### The story\n\n" + "\n\n".join(" ".join(s.get("fa", "") for s in p.get("sentences", [])) for p in S.get("paragraphs", [])) + "\n\n")
    out.append("### Line by line\n\n" + "".join(sentence(s) for p in S.get("paragraphs", []) for s in p.get("sentences", [])) + "\n")
    if S.get("vocab"):
        out.append("### Words\n\n" + vocab(S["vocab"]))
    if S.get("questions"):
        out.append("### Did you follow?\n\n" + exercise({"kind": "mcq", "items": S["questions"]}))
    if S.get("after"):
        out.append("### About this story\n\n" + inl(S["after"]) + "\n\n")
    if S.get("source"):
        out.append(f"_{inl(S['source'])}_\n\n")
    out.append("---\n\n[Contents](../README.md)\n")
    return "".join(out)


def article_md(A):
    out = [f"# {A.get('title')}\n", f"## {A.get('titleFa', '')}\n", f"*{A.get('titleR', '')}* — [read on the website with audio]({SITE}culture/{A['id']}.html)\n\n",
           f"_{inl(A.get('summary', ''))}_\n\n", photo(A.get("image"))]
    for sec in A.get("body", []):
        if sec.get("h"):
            out.append(f"### {inl(sec['h'])}\n\n")
        out.append(photo(sec.get("image")) + inl(sec.get("md", "")) + "\n\n")
    if A.get("facts"):
        out.append("### Facts\n\n" + "\n".join(f"- {inl(x)}" for x in A["facts"]) + "\n\n")
    if A.get("sentences"):
        out.append("### Say it in Persian\n\n" + "".join(sentence(s) for s in A["sentences"]) + "\n")
    if A.get("vocab"):
        out.append("### Words\n\n" + vocab(A["vocab"]))
    out.append("---\n\n[Contents](../README.md)\n")
    return "".join(out)


def poem_md(P):
    out = [f"# {P.get('title')}\n", f"## {P.get('titleFa', '')}\n", f"{P.get('poet', '')} ({P.get('poetFa', '')}), {P.get('work', '')}, {P.get('century', '')} century. "
           f"[Listen on the website]({SITE}poetry/{P['id']}.html)\n\n", inl(P.get("intro", "")) + "\n\n", photo(P.get("image"))]
    out.append("### The poem\n\n" + "\n".join(f"> {ln.get('fa', '').replace(' / ', ' &nbsp;&nbsp;&nbsp; ')}  " for ln in P.get("lines", [])) + "\n\n")
    out.append("### Line by line\n\n")
    for ln in P.get("lines", []):
        out.append(sentence(ln))
        if ln.get("words"):
            out.append("  <details><summary>Word by word</summary>\n\n  " + " · ".join(f"{w[0]} *{w[1]}* {w[2]}" for w in ln["words"] if len(w) >= 3) + "\n\n  </details>\n")
    out.append("\n### Reading the poem\n\n" + inl(P.get("commentary", "")) + "\n\n---\n\n[Contents](../README.md)\n")
    return "".join(out)


def phrasebook_md(pb):
    out = ["# Phrasebook\n\n", inl(pb.get("intro", "")) + "\n\n", f"[Open the phrasebook with audio]({SITE}phrasebook/index.html)\n\n"]
    for s in pb.get("sections", []):
        out.append(f"## {s.get('title')} — {s.get('titleFa', '')}\n\n" + (inl(s.get("intro", "")) + "\n\n" if s.get("intro") else ""))
        out.append("".join(sentence(it) for it in s.get("items", [])) + "\n")
    return "".join(out) + "---\n\n[Contents](README.md)\n"


def idioms_md(d):
    out = ["# Proverbs and idioms\n\n", inl(d.get("intro", "")) + "\n\n"]
    for it in d.get("items", []):
        out.append(f"### {it.get('fa', '')}\n\n*{it.get('r', '')}*  \nLiterally: {inl(it.get('lit', ''))}  \nMeaning: **{inl(it.get('en', ''))}**\n\n"
                   + (inl(it.get("note", "")) + "\n\n" if it.get("note") else "") + (sentence(it["ex"]) + "\n" if isinstance(it.get("ex"), dict) and it["ex"].get("fa") else ""))
    return "".join(out) + "---\n\n[Contents](README.md)\n"


def verbs_md(d):
    out = ["# Verbs\n\nEvery verb with its present stem (the past stem is the infinitive without ن). "
           f"[Conjugate any of them on the website]({SITE}verbs/index.html).\n\n", "| Infinitive | | Present stem | | Meaning | Example |", "| --- | --- | --- | --- | --- | --- |"]
    for v in d.get("verbs", []):
        ex = v.get("ex") or {}
        out.append(f"| {v.get('inf')} | *{v.get('r')}* | {v.get('stem')} | *{v.get('stemR')}* | {v.get('en')} | {ex.get('fa', '')} ({ex.get('en', '')}) |")
    return "\n".join(out) + "\n\n---\n\n[Contents](README.md)\n"


def main():
    if os.path.exists(BOOK):
        shutil.rmtree(BOOK)
    for sub in ("lessons", "stories", "culture", "poetry"):
        os.makedirs(os.path.join(BOOK, sub))
    toc = ["# Learn Farsi – the book\n\n",
           "The whole course as a book you can read here on GitHub. For recorded audio, interactive exercises, flashcards, "
           f"the dictionary and the verb conjugator, use the website: **{SITE}**\n\n",
           "Persian is written right to left. Every Persian line is followed by its pronunciation in *italics* "
           "(ā as in *father*, kh as in *loch*, gh a throaty r, ' a catch in the throat) and its meaning.\n\n"]
    order = [lid for lv in COURSE.get("levels", []) for lid in lv.get("lessons", []) if lid in LESSONS]
    for i, lid in enumerate(order):
        open(os.path.join(BOOK, "lessons", lid + ".md"), "w", encoding="utf-8").write(
            lesson_md(LESSONS[lid], order[i - 1] if i else None, order[i + 1] if i + 1 < len(order) else None))
    part = 0
    for lv in COURSE.get("levels", []):
        ready = [l for l in lv.get("lessons", []) if l in LESSONS]
        if not ready:
            continue
        part += 1
        toc.append(f"## Part {part}. {lv['name']} — {lv.get('fa', '')}\n\n{lv.get('blurb', '')}\n\n")
        toc.extend(f"{LESSONS[l].get('n')}. [{LESSONS[l]['title']}](lessons/{l}.md) — {LESSONS[l].get('titleFa', '')}\n" for l in ready)
        toc.append("\n")
    if STORIES:
        part += 1
        toc.append(f"## Part {part}. Stories — داستان‌ها\n\nGraded readers, from very easy to literary.\n\n")
        for lvl in ["A1", "A2", "B1", "B2", "C1"]:
            ids = [s for s in COURSE.get("stories", []) if s in STORIES and STORIES[s].get("level") == lvl]
            if ids:
                toc.append(f"**{LEVELS[lvl]}**\n\n" + "".join(f"- [{STORIES[s]['title']}](stories/{s}.md) — {STORIES[s].get('titleFa', '')}\n" for s in ids) + "\n")
        for s in STORIES:
            open(os.path.join(BOOK, "stories", s + ".md"), "w", encoding="utf-8").write(story_md(STORIES[s]))
    if ARTICLES:
        part += 1
        toc.append(f"## Part {part}. Iran in pictures and stories — فرهنگ ایران\n\n")
        plan = COURSE.get("culture", {})
        for key, name in TOPICS:
            ids = [a for a in plan.get(key, []) if a in ARTICLES] + [a for a, A in ARTICLES.items() if A.get("topic") == key and a not in plan.get(key, [])]
            if ids:
                toc.append(f"**{name}**\n\n" + "".join(f"- [{ARTICLES[a]['title']}](culture/{a}.md) — {ARTICLES[a].get('titleFa', '')}\n" for a in ids) + "\n")
        for a in ARTICLES:
            open(os.path.join(BOOK, "culture", a + ".md"), "w", encoding="utf-8").write(article_md(ARTICLES[a]))
    if POEMS:
        part += 1
        toc.append(f"## Part {part}. Poetry — شعر\n\n" + "".join(f"- [{POEMS[p]['title']}](poetry/{p}.md) — {POEMS[p].get('poet', '')}\n"
                                                           for p in COURSE.get("poems", []) if p in POEMS) + "\n")
        for p in POEMS:
            open(os.path.join(BOOK, "poetry", p + ".md"), "w", encoding="utf-8").write(poem_md(POEMS[p]))
    extra = []
    pb, idi, vb = load("content/phrasebook.json"), load("content/idioms.json"), load("content/verbs.json")
    if pb:
        open(os.path.join(BOOK, "phrasebook.md"), "w", encoding="utf-8").write(phrasebook_md(pb))
        extra.append("- [Phrasebook](phrasebook.md)")
    if idi:
        open(os.path.join(BOOK, "idioms.md"), "w", encoding="utf-8").write(idioms_md(idi))
        extra.append("- [Proverbs and idioms](idioms.md)")
    if vb:
        open(os.path.join(BOOK, "verbs.md"), "w", encoding="utf-8").write(verbs_md(vb))
        extra.append("- [Verbs and their stems](verbs.md)")
    if extra:
        part += 1
        toc.append(f"## Part {part}. Reference\n\n" + "\n".join(extra) + f"\n- [Dictionary of the 5,000 most common words]({SITE}dictionary/index.html) (website)\n\n")
    open(os.path.join(BOOK, "README.md"), "w", encoding="utf-8").write("".join(toc))
    n = sum(len(os.listdir(os.path.join(BOOK, s))) for s in ("lessons", "stories", "culture", "poetry"))
    print(f"book/: {n} chapters")


if __name__ == "__main__":
    main()
