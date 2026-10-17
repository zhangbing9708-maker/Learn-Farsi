"""Record Farsi audio for Learn Farsi.

usage:
  python3 tools/make_audio.py            make audio for every Farsi word and sentence that has none yet
  python3 tools/make_audio.py --dry      only add faV/a fields and report what would be recorded
  python3 tools/make_audio.py --prune    also delete audio files nothing refers to any more
  python3 tools/make_audio.py --jobs 4   number of parallel synthesis workers

Most phones and computers have no Persian voice, so the site plays recorded files. This script walks every
JSON file under content/ and the reused data files (data/glossary.json, data/alphabets.json, data/dict.json,
data/grammar.json) and records:

  - every object with a Farsi string `fa` and a transliteration `r` (vocabulary, dialogue lines, examples,
    story sentences, phrases, exercise answers...)   -> fields `faV` (vowel-marked text) and `a` (audio id)
  - the spoken form `col` + `colR` of such objects                               -> `colV`, `colA`
  - `titleFa` + `titleR` of lessons, stories, articles, poems, phrasebook sections -> `titleV`, `titleA`
  - data files: as in World News Words (fa.v / ex.faV / v / faV -> a)

Vowel marks come from tools/vowelize_text.py (derived from `r`); an author may write `faV` by hand and it is
kept. An audio id is a hash of the spoken text, so identical sentences share a file and only new text is
synthesised. The voice is the open-source Piper "gyro" Persian voice run with sherpa-onnx; both are downloaded
into ~/.cache/wnw-tts the first time. ffmpeg makes the MP3s.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vowelize_text import vowelize_sentence  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CONTENT = os.path.join(ROOT, "content")
AUDIO_DIR = os.path.join(DATA, "audio", "fa")
CACHE = os.path.expanduser("~/.cache/wnw-tts")
RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
ENGINE = "sherpa-onnx-v1.13.7-linux-x64-static"
ENGINE_URL = f"{RELEASES}/v1.13.7/{ENGINE}.tar.bz2"
SHARED = "sherpa-onnx-v1.13.7-linux-x64-shared"            # C library: load the voice once per worker (much faster)
SHARED_URL = f"{RELEASES}/v1.13.7/{SHARED}.tar.bz2"
VOICE = "vits-piper-fa_IR-gyro-medium"
VOICE_URL = f"{RELEASES}/tts-models/{VOICE}.tar.bz2"
TATWEEL = "ـ"
SKIP_KEYS = {"words", "table", "options", "p", "e"}   # lists without audio of their own


def ensure(name, url):
    path = os.path.join(CACHE, name)
    if os.path.isdir(path):
        return path
    os.makedirs(CACHE, exist_ok=True)
    print(f"Downloading {name} ...", flush=True)
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        tmp = os.path.join(td, "x.tar.bz2")
        subprocess.run(["curl", "-sSL", "--fail", "--retry", "2", "-o", tmp, url], check=True)
        with tarfile.open(tmp, "r:bz2") as tf:
            tf.extractall(CACHE, filter="data")
    if not os.path.isdir(path):
        sys.exit(f"Download of {name} did not produce {path}")
    return path


def audio_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def spoken(text):
    return re.sub(r"\s+", " ", str(text or "").replace(TATWEEL, "")).strip()


class Collector:
    def __init__(self):
        self.jobs = {}      # id -> spoken text
        self.problems = []  # (file, fa, problems)
        self.changed = set()

    def want(self, text):
        t = spoken(text)
        if not t:
            return None
        i = audio_id(t)
        self.jobs[i] = t
        return i

    def mark(self, obj, fa_key, r_key, v_key, a_key, fname):
        fa = obj.get(fa_key)
        if not isinstance(fa, str) or not fa.strip() or "___" in fa:
            return
        r = obj.get(r_key)
        v = obj.get(v_key)
        if not (isinstance(v, str) and v.strip()):
            v, probs = vowelize_sentence(fa, r if isinstance(r, str) else None)
            if probs:
                self.problems.append((fname, fa, probs))
            obj[v_key] = v
            self.changed.add(fname)
        i = self.want(v)
        if i and obj.get(a_key) != i:
            obj[a_key] = i
            self.changed.add(fname)

    def walk_content(self, x, fname):
        if isinstance(x, dict):
            if "fa" in x and isinstance(x.get("fa"), str):
                self.mark(x, "fa", "r", "faV", "a", fname)
            if "col" in x and isinstance(x.get("col"), str):
                self.mark(x, "col", "colR", "colV", "colA", fname)
            if "titleFa" in x and isinstance(x.get("titleFa"), str):
                self.mark(x, "titleFa", "titleR", "titleV", "titleA", fname)
            if "inf" in x and isinstance(x.get("inf"), str) and isinstance(x.get("r"), str):
                self.mark(x, "inf", "r", "infV", "a", fname)
            for k, v in x.items():
                if k in SKIP_KEYS:
                    continue
                self.walk_content(v, fname)
        elif isinstance(x, list):
            for v in x:
                self.walk_content(v, fname)


def collect_data_files(col):
    """The reused World News Words files, with their own conventions."""
    out = {}
    p = os.path.join(DATA, "glossary.json")
    if os.path.exists(p):
        g = json.load(open(p, encoding="utf-8"))
        for e in g["entries"].values():
            fa = e.get("fa") or {}
            i = col.want(fa.get("v") or fa.get("w"))
            if i:
                fa["a"] = i
            ex = e.get("ex")
            if isinstance(ex, dict) and ex.get("fa"):
                i = col.want(ex.get("faV") or ex.get("fa"))
                if i:
                    ex["faA"] = i
        out[p] = (g, False)
    p = os.path.join(DATA, "alphabets.json")
    if os.path.exists(p):
        a = json.load(open(p, encoding="utf-8"))
        for sec in a.get("fa", {}).get("sections", []):
            for c in sec.get("cells", []):
                ex = (c or {}).get("ex")
                if isinstance(ex, dict):
                    i = col.want(ex.get("v") or ex.get("w"))
                    if i:
                        ex["a"] = i
        out[p] = (a, False)
    p = os.path.join(DATA, "dict.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for e in d.get("entries", []):
            i = col.want(e.get("v") or e.get("w"))
            if i:
                e["a"] = i
        out[p] = (d, False)
    p = os.path.join(DATA, "grammar.json")
    if os.path.exists(p):
        g = json.load(open(p, encoding="utf-8"))

        def walk(x):
            if isinstance(x, dict):
                if isinstance(x.get("faV"), str) and x["faV"].strip():
                    i = col.want(x["faV"])
                    if i:
                        x["a"] = i
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(g)
        out[p] = (g, True)
    return out


def main():
    dry = "--dry" in sys.argv
    prune = "--prune" in sys.argv
    jobs_n = None
    if "--jobs" in sys.argv:
        jobs_n = int(sys.argv[sys.argv.index("--jobs") + 1])
    exclude = None
    if "--exclude" in sys.argv:          # regex of content paths to leave alone (files other people are still editing)
        exclude = re.compile(sys.argv[sys.argv.index("--exclude") + 1])
    settled = 0
    if "--settled" in sys.argv:          # skip content files changed in the last N minutes (still being written)
        settled = float(sys.argv[sys.argv.index("--settled") + 1]) * 60
    if not dry and not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed to make MP3 files.")
    col = Collector()
    data_files = collect_data_files(col)
    content = {}
    loaded_at = {}      # file -> mtime when read, so a file edited while we record is not overwritten
    extra = [os.path.join(DATA, "numbers.json")]
    import time
    for p in sorted(glob.glob(os.path.join(CONTENT, "**", "*.json"), recursive=True)) + [x for x in extra if os.path.exists(x)]:
        if exclude and exclude.search(os.path.relpath(p, ROOT)):
            continue
        if settled and time.time() - os.path.getmtime(p) < settled:
            print("  still being written, skipped:", os.path.relpath(p, ROOT))
            continue
        try:
            x = json.load(open(p, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print("  invalid JSON, skipped:", os.path.relpath(p, ROOT), e)
            continue
        col.walk_content(x, p)
        content[p] = x
        loaded_at[p] = os.stat(p).st_mtime_ns

    os.makedirs(AUDIO_DIR, exist_ok=True)
    todo = {i: t for i, t in col.jobs.items() if not os.path.exists(os.path.join(AUDIO_DIR, i + ".mp3"))}
    if col.problems:
        print(f"{len(col.problems)} sentences have words that could not be vowel-marked (see check_content.py):")
        for f, fa, probs in col.problems[:15]:
            print("  ", os.path.relpath(f, ROOT), "|", fa, "|", probs)
    if dry:
        print(f"Would record {len(todo)} new files ({len(col.jobs) - len(todo)} reused).")
    elif todo:
        voice = ensure(VOICE, VOICE_URL)
        workers = jobs_n or max(1, min(6, (os.cpu_count() or 2)))
        items = sorted(todo.items())
        print(f"Making {len(todo)} audio files with {workers} workers ...", flush=True)
        done = 0
        try:
            shared = ensure(SHARED, SHARED_URL)
            import multiprocessing as mp
            import tts_fast
            with mp.get_context("fork").Pool(workers, initializer=tts_fast.init,
                                             initargs=(os.path.join(shared, "lib"), voice, "fa_IR-gyro-medium.onnx")) as pool:
                for _ in pool.imap_unordered(tts_fast.synth, [(i, t, AUDIO_DIR) for i, t in items], chunksize=8):
                    done += 1
                    if done % 250 == 0:
                        print(f"  {done}/{len(todo)}", flush=True)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as e:
            print("fast synthesis unavailable (" + str(e) + "); using the command-line program", flush=True)
            engine = ensure(ENGINE, ENGINE_URL)
            binary = os.path.join(engine, "bin", "sherpa-onnx-offline-tts")
            model = os.path.join(voice, "fa_IR-gyro-medium.onnx")

            def synth(item):
                i, text = item
                out = os.path.join(AUDIO_DIR, i + ".mp3")
                if os.path.exists(out):
                    return i
                with tempfile.TemporaryDirectory() as td:
                    wav = os.path.join(td, "a.wav")
                    subprocess.run([binary, f"--vits-model={model}", f"--vits-tokens={os.path.join(voice, 'tokens.txt')}",
                                    f"--vits-data-dir={os.path.join(voice, 'espeak-ng-data')}", "--num-threads=1",
                                    f"--output-filename={wav}", text], check=True, capture_output=True)
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "adelay=60:all=1",
                                    "-ac", "1", "-ar", "22050", "-c:a", "libmp3lame", "-b:a", "32k", out + ".tmp.mp3"], check=True)
                    os.replace(out + ".tmp.mp3", out)
                return i
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for _ in pool.map(synth, items):
                    done += 1
                    if done % 250 == 0:
                        print(f"  {done}/{len(todo)}", flush=True)

    for p, (x, indent) in data_files.items():
        if indent:
            open(p, "w", encoding="utf-8").write(json.dumps(x, ensure_ascii=False, indent=1))
        else:
            json.dump(x, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for p, x in content.items():
        if p in col.changed:
            st = os.stat(p)
            if st.st_mtime_ns != loaded_at.get(p):
                print("  changed while recording, not updated (run again):", os.path.relpath(p, ROOT))
                continue
            open(p, "w", encoding="utf-8").write(json.dumps(x, ensure_ascii=False, indent=1) + "\n")
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))   # adding audio fields is not an edit: keep the file "settled"

    removed = 0
    if prune and not dry:
        for f in os.listdir(AUDIO_DIR):
            if f.endswith(".mp3") and f[:-4] not in col.jobs:
                os.remove(os.path.join(AUDIO_DIR, f))
                removed += 1
    size = sum(os.path.getsize(os.path.join(AUDIO_DIR, f)) for f in os.listdir(AUDIO_DIR))
    print(f"Farsi audio: {len(todo)} new, {len(col.jobs) - len(todo)} reused, {removed} removed; "
          f"{len(os.listdir(AUDIO_DIR))} files, {size / 1e6:.1f} MB.")


if __name__ == "__main__":
    main()
