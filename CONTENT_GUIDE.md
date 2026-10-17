# Learn Farsi – content guide

Everything the site shows is written in JSON files under `content/` (plus the dictionary and grammar data under
`data/`, reused from World News Words). `tools/build_site.py` turns them into the static pages in `site/`,
`tools/make_audio.py` records every Farsi word and sentence, and `tools/check_content.py` must print `OK`
before anything is committed.

## 1. Writing Farsi

- **Standard Iranian Persian**, written register (كتابی) in lessons, stories and articles. Where spoken
  Persian differs, give the spoken form separately in a `col` field (see below) – never mix registers in one
  sentence.
- Persian letters only: `ی` and `ک`, never Arabic `ي` `ك`. Persian digits (`۱۲۳`) inside Persian text.
- **ZWNJ** (U+200C, written `‌`) where Persian uses it: `می‌روم`, `نمی‌دانم`, `کتاب‌ها`, `خانه‌ی من`,
  `بی‌کار`, `هم‌کلاس`, `آن‌ها`, `این‌جا`. Never a space between `می` and the verb.
- Ezafe after a final silent `ه` is written `‌ی` (ZWNJ + ye): `خانه‌ی بزرگ`. After `ا`/`و` it is `ی`:
  `پای من`, `موی او`. After a consonant it is not written.
- Punctuation: Persian comma `،`, question mark `؟`, full stop `.`.
- Every Persian string is **one sentence or one phrase**; longer texts are lists of sentences.

## 2. Transliteration (`r`)

The site's romanisation (the same as the dictionary's):

| Sound | Write | Example |
| --- | --- | --- |
| long a (ا / آ) | `ā` | `ketāb`, `āb` |
| short vowels | `a` `e` `o` | `dar`, `del`, `pol` |
| long vowels (و / ی) | `u` `i` | `dur`, `shir` |
| diphthongs | `ow` `ey` | `nowruz`, `mey` |
| خ غ/ق ش چ ژ | `kh` `gh` `sh` `ch` `zh` | `khub`, `ghalam`, `shab`, `chāy`, `zhāle` |
| ع / ء | `'` | `sā'at`, `ba'd`, `mas'ul` |
| ه (consonant) | `h` | `māh`, `hezār` |
| final silent ه | `e` (or `a` in `na`) | `khāne`, `na` |

- Lowercase, except for names (`Sārā`, `Tehrān`, `Irān`) at any position.
- **One space in `r` for every space in `fa`** – the checker aligns them token by token. Inside a word use
  hyphens, never spaces: `mi-ravam` ↔ `می‌روم`, `nemi-dānam` ↔ `نمی‌دانم`, `ketāb-hā` ↔ `کتاب‌ها`,
  `khāne-ye man` ↔ `خانه‌ی من`, `ketāb-e man` ↔ `کتاب من`, `ketāb-am` ↔ `کتابم`, `in-jā` ↔ `این‌جا`.
- Hyphenate: `mi-`, `nemi-`, `na-`, `be-` (subjunctive/imperative), ezafe `-e`/`-ye`, plural `-hā`,
  indefinite `-i`, possessive `-am -at -ash -emān -etān -eshān`, `-tar`, `-tarin`, and the parts of a compound
  joined by ZWNJ. Do **not** hyphenate verb endings (`raftam`, `mi-ravand`) or the plural `-ān` (`mardān`).
- Punctuation in `r` mirrors `fa`: `salām!` ↔ `سلام!`, `chetori?` ↔ `چطوری؟`.
- Doubled consonants for tashdid: `ammā`, `bacche`, `tavarrom`.

The transliteration is what `tools/vowelize_text.py` uses to put vowel marks on the Persian for the voice,
so it has to be right: a wrong `r` makes wrong audio.

## 3. English

- Plain, friendly, concrete. Short paragraphs. Explain grammar with examples, not terminology – name the
  term once (in English and Persian) and then use examples.
- Translations (`en`) are natural English, not word-for-word; when a literal reading helps, put it in `lit`.
- Markdown-lite in `md` fields: paragraphs separated by blank lines, `**bold**`, `*italic*`, `- ` bullet
  lists, `1. ` numbered lists, `## ` sub-headings. Inline Farsi inside English text is written as
  `[[خانه|khāne|house]]` (Farsi | transliteration | gloss; the last two may be omitted: `[[خانه|khāne]]`).

## 4. The common sentence object

Every Farsi example anywhere is an object with these fields (audio fields are added by tools):

```json
{"fa": "من کتاب می‌خوانم.", "r": "man ketāb mi-khānam.", "en": "I read a book.",
 "col": "من کتاب می‌خونم.", "colR": "man ketāb mi-khunam.", "lit": "I book read-am", "note": "..."}
```

`col`/`colR` (spoken Tehrani form), `lit` and `note` are optional. Tools add `faV` (vowel-marked), `a` (audio
id) and, for `col`, `colA`.

## 5. Lessons – `content/lessons/<id>.json`

```json
{
  "id": "a1-03-family",
  "level": "A1",
  "n": 3,
  "title": "My family",
  "titleFa": "خانواده‌ی من",
  "titleR": "khānevāde-ye man",
  "intro": "One short paragraph: what you will be able to do after this lesson.",
  "goals": ["name the people in your family", "say 'my', 'your', 'his/her' with -am, -at, -ash", "make plurals with -hā"],
  "image": "iranian-family",
  "sections": [ ...blocks in order... ]
}
```

- `id`: `<level>-<two-digit number>-<slug>`; levels: `script`, `a1`, `a2`, `b1`, `b2`, `c1`.
- `image`: a key of `data/images.json` (optional).

### Blocks

Every block has `type` and usually `title`.

| type | fields | what it is |
| --- | --- | --- |
| `text` | `md` | Explanation in English (markdown-lite, inline `[[...]]` Farsi). |
| `vocab` | `items: [{fa, r, en, pos?, note?, ex?: sentence}]` | Word list; `pos` ∈ `n v adj adv pron prep conj num phrase name`. 8–20 items. |
| `dialogue` | `context`, `lines: [{who, fa, r, en, col?, colR?}]` | A conversation; `who` is a name. 6–14 lines. |
| `grammar` | `md`, `table?: {head: [...], rows: [[...]]}`, `examples?: [sentence]` | One grammar point: explanation, a table (Persian cells may contain `[[fa|r]]` or plain Persian), examples. |
| `reading` | `intro?`, `sentences: [sentence]`, `questions?` | A short connected text, one sentence per object (A1: 4–6 sentences, A2: 6–10, B1+: 10–18). |
| `culture` | `md`, `image?` | A note about life in Iran / the Persian-speaking world. |
| `tips` | `items: [string]` | Learning tips, pronunciation tips, false friends. |
| `letters` | `letters: [string]`, `md?` | (script lessons) letters of the alphabet to show from `data/alphabets.json`. |
| `exercise` | `kind`, `items` | See below. 3–6 exercises per lesson, varied kinds. |

Exercise kinds:

- `mcq`: `{q, options: [string], answer: index, explain?}` – `q` may contain `[[...]]`; options are Persian or English strings.
- `fill`: `{fa, r, en, answer, hint?}` – `fa` and `r` contain `___` exactly once; `answer` is the Persian word that goes in; `en` is the full meaning.
- `translate`: `{en, fa, r}` – translate into Farsi; the answer is revealed.
- `match`: `{fa, r, en}` pairs (5–8).
- `order`: `{fa, r, en}` – the learner puts the words of `fa` in order.
- `listen`: `{fa, r, en, options: [string], answer: index}` – hear the sentence, choose what was said / what it means.

### Lesson shape

Script lessons: `text` → `letters` → `vocab` (words that use only letters learned so far) → `tips` → exercises.

Level lessons: `intro` → `dialogue` (or `reading`) → `vocab` → 1–3 `grammar` blocks → `reading` →
`culture` → `tips` → 3–6 `exercise` blocks → a final `text` "In this lesson you learned…" is **not** needed
(the goals do that).

## 6. Stories – `content/stories/<id>.json`

```json
{
  "id": "a2-the-shepherd-and-the-moon",
  "level": "A2",
  "kind": "folk tale",
  "title": "The shepherd and the moon",
  "titleFa": "چوپان و ماه",
  "titleR": "chupān o māh",
  "image": "alborz-shepherd",
  "intro": "English lead-in: what kind of story this is, where it comes from, what to look for.",
  "source": "Retold from a traditional Iranian tale (public domain).",
  "paragraphs": [ {"sentences": [ sentence, sentence ]}, ... ],
  "vocab": [ {fa, r, en} ],
  "questions": [ {"q": "...", "options": ["..."], "answer": 0} ],
  "after": "Optional English note: culture, grammar seen in the story, a proverb it illustrates."
}
```

`kind` ∈ `folk tale`, `fable`, `legend`, `everyday life`, `history`, `biography`, `humour`, `travel`, `dialogue`.
Length: A1 40–90 words (6–10 sentences, present tense, known structures), A2 120–220, B1 250–450, B2 450–800,
C1 700–1200. Sentences stay short at A1/A2. Every story gets 8–16 `vocab` items and 3–5 questions.

Only retell what is public domain or your own: classical tales (Shahnameh, Kalila and Dimna, Mullah
Nasreddin, folk tales), history, everyday life. Never copy modern authors.

## 7. Articles – `content/culture/<id>.json`

```json
{
  "id": "food-ghormeh-sabzi",
  "topic": "food",
  "title": "Ghormeh sabzi",
  "titleFa": "قورمه‌سبزی",
  "titleR": "ghorme-sabzi",
  "image": "ghormeh-sabzi",
  "summary": "One or two sentences.",
  "body": [ {"h": "Heading", "md": "English text with [[فارسی|fārsi|Persian]] inline", "image": "optional image key"} ],
  "sentences": [ sentence ],
  "vocab": [ {fa, r, en} ],
  "facts": [ "short fact", "short fact" ]
}
```

`topic` ∈ `history`, `places`, `food`, `festivals`, `arts`, `people`, `language`, `life`. 300–700 English
words in `body`, 6–12 useful Farsi `sentences` about the topic (graded roughly A2–B1), 10–20 `vocab`.

## 8. Poems – `content/poems/<id>.json`

Only poets who died before 1926 (public domain): Rudaki, Ferdowsi, Khayyam, Nezami, Attar, Rumi, Saadi, Hafez,
Baba Taher, Jami, Nasir Khusraw, Sanai, Parvin E'tesami is **not** (d. 1941).

```json
{
  "id": "saadi-bani-adam",
  "poet": "Saadi", "poetFa": "سعدی", "work": "Golestan", "century": "13th",
  "title": "Children of Adam", "titleFa": "بنی‌آدم",
  "form": "qet'e",
  "intro": "English: the poem's place, story, why it matters.",
  "lines": [ {"fa": "...", "r": "...", "en": "...", "words": [["بنی‌آدم", "bani-ādam", "the children of Adam"]], "note": "..."} ],
  "commentary": "English paragraphs on language, imagery, grammar in the lines.",
  "image": "saadi-tomb"
}
```

Lines are single hemistichs or whole verses (both halves separated by ` / ` in `fa` and `r`). Quote the poem
exactly as it is commonly printed; note variant readings in `note`.

## 9. Phrasebook, idioms, verbs

- `content/phrasebook.json`: `{"sections": [{"id", "title", "titleFa", "titleR", "intro", "items": [sentence + {"formal": true|false}]}]}`.
- `content/idioms.json`: `{"items": [{"fa", "r", "lit", "en", "ex": sentence, "note"?}]}` – proverbs and idioms, `lit` is the literal meaning.
- `content/verbs.json`: `{"verbs": [{"inf", "r", "stem", "stemR", "en", "note"?, "ex"?: sentence}]}` – infinitive and
  present stem; the site conjugates them.

## 10. Images

`data/images.json` maps a key to a Wikimedia Commons photo: `{"url", "page", "artist", "license", "licenseUrl", "caption"}`.
Use only keys that exist (see `tools/check_content.py --images` for the list). The page shows the credit under
every photo.

## 11. Before committing

```
python3 tools/check_content.py       # must print OK (lists token mismatches, Arabic letters, missing images, bad ids)
python3 tools/make_audio.py          # records new Farsi (adds faV and a); commit data/audio/fa/*.mp3 too
python3 tools/build_site.py          # regenerates site/
python3 tools/build_book.py          # regenerates book/*.md
```
