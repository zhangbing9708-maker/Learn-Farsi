# Learn Farsi · فارسی بیاموز

**A free, open course in Persian (Farsi) – from the first letter of the alphabet to reading Hafez.**

🌐 **Website (with audio and exercises): https://zhangbing9708-maker.github.io/Learn-Farsi/**
📖 **Read it as a book here on GitHub: [book/README.md](book/README.md)**

Learn Farsi is written like an open textbook: every lesson, story and article is a plain JSON file in
[`content/`](content/), and both the website and the Markdown book are built from those files.

## What's inside

| | |
| --- | --- |
| **The course** | Six stages: the Script (8 lessons), Beginner A1 (20), Elementary A2 (16), Intermediate B1 (14), Upper intermediate B2 (9) and Advanced C1 (5). Each lesson has a dialogue or reading with recorded audio, the words to learn, grammar with tables, a culture note and self-checking exercises (multiple choice, fill-in with an on-screen Persian keyboard, word order, matching, listening, translation). |
| **Stories** | 74 graded readers (18 A1, 22 A2, 22 B1, 8 B2, 4 C1): Mulla Nasreddin, Kalila and Dimna, the Shahnameh (Rostam and Sohrab, Zal and the Simorgh, Kaveh, Arash), folk tales, history and everyday life in Tehran, Isfahan and Shiraz – every sentence with audio, transliteration and a translation you can hide. |
| **Culture** | 116 illustrated articles with Wikimedia Commons photos: history (23, Elam to today), places (Tehran, Isfahan, Shiraz, Yazd, Kashan, Tabriz, the Caspian, the Persian Gulf islands…), food (27, including a cook-along recipe series), festivals (Nowruz, Yalda, Chaharshanbe Suri…), arts, famous people, the Persian language and everyday life – each ending with useful sentences and words. |
| **Poetry** | 16 classical poems by Saadi, Rumi, Hafez, Ferdowsi, Khayyam, Rudaki, Baba Taher, Attar, Nezami, Sanai, Jami and Naser Khosrow, line by line with word-by-word glosses. |
| **News** | The week's news retold in simple Persian, with vocabulary and background. |
| **Tools** | A 5,000-word frequency dictionary with recorded pronunciation and example sentences in context, a verb conjugator (every tense, any verb), a phrasebook (336 phrases), 150 proverbs and idioms, sentence-pattern grammar, Persian numbers and the Iranian calendar, and flashcards with spaced repetition (Anki export). |

More than 16,000 sentences and words are recorded. Every lesson, story, article and poem has a **Print** button that lays the page out on A4 (exercises become a worksheet with an answer key), and a **Save offline** button that keeps the page and its audio on the device. Everything works on a phone and can be installed like an app. Progress and saved words stay in the learner's browser; nothing is tracked.

## How to use it

1. Can't read Persian yet? Start with **[the alphabet](https://zhangbing9708-maker.github.io/Learn-Farsi/course/script-01-how-persian-is-written.html)** – eight short lessons.
2. Work through the course in order. Listen to every line and say it aloud; then hide the English and the transliteration and read again.
3. Save words with **+** and review them for ten minutes a day on the flashcards page.
4. From the end of A1, read a story a week; from A2, the news in simple Persian.

## Repository

| Path | What it is |
| --- | --- |
| `content/` | The course: `lessons/`, `stories/`, `culture/`, `poems/`, `news.json`, `phrasebook.json`, `idioms.json`, `verbs.json`, `course.json` (the order of everything) |
| `data/` | The frequency dictionary, alphabet, sentence-pattern grammar, photo list and the recorded audio (`data/audio/fa/*.mp3`) |
| `tools/` | Python scripts: `check_content.py` (validation), `make_audio.py` (records the audio), `build_site.py` (the website), `build_book.py` (the Markdown book), `persian_numbers.py` (number words), `build_images.py`, `make_icons.py` |
| `assets/` | The site's stylesheet and script, plus generated search, flashcard and dictionary data |
| `book/` | The Markdown edition, generated |
| everything else | The generated website (`index.html`, `course/`, `stories/`, …), served by GitHub Pages |

To change or add content, edit the JSON (the format is in [CONTENT_GUIDE.md](CONTENT_GUIDE.md)), then:

```
python3 tools/check_content.py   # must print OK
python3 tools/make_audio.py      # records new Persian sentences (downloads an open-source voice the first time)
python3 tools/build_site.py      # rebuilds the website
python3 tools/build_book.py      # rebuilds the book
```

## Sources and credits

- **Audio**: synthesised with the open-source Piper "gyro" Persian voice, run with [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx). Vowel marks for the voice are derived from each sentence's transliteration (`tools/vowelize_text.py`).
- **Photos**: Wikimedia Commons, used under the licence shown with each photo and listed on the [photo credits page](https://zhangbing9708-maker.github.io/Learn-Farsi/about/photos.html).
- **Dictionary**: word list, frequency ranks, glosses and topics from Corey Miller and Karineh Aghajanian-Stewart, *A Frequency Dictionary of Persian* (Routledge, 2018); example sentences come from this course.
- **Poems**: public-domain classical poetry; translations and notes are new.
- **News**: original summaries in simple Persian of the reports linked on each story.
- Related project: [World News Words](https://github.com/zhangbing9708-maker/world-news-words) (learn Persian words from the week's English news), whose dictionary, alphabet, grammar and audio tools this course reuses.

## Licence

Course text: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Code: MIT. Photos: their own licences. Corrections and additions are welcome as issues or pull requests.
