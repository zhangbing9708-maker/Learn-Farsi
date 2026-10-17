"""Take screenshots of the built site for review (desktop and phone) and report JavaScript errors.

usage: python3 tools/screenshots.py OUTDIR [page ...]
Serves the repository on localhost:8765 while it runs.
"""
import http.server
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["index.html", "course/index.html", "course/a1-01-hello.html", "course/script-02-alef-be-pe-te-se.html",
         "stories/index.html", "stories/b1-rostam-and-sohrab.html", "culture/index.html",
         "culture/history-elam-and-the-first-cities.html", "alphabet/index.html", "news/index.html",
         "dictionary/index.html", "verbs/index.html", "numbers/index.html", "flashcards/index.html", "grammar/index.html"]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"
    pages = sys.argv[2:] or PAGES
    os.makedirs(out, exist_ok=True)
    os.chdir(ROOT)
    httpd = socketserver.TCPServer(("127.0.0.1", 8765), Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, vp in (("desk", {"width": 1366, "height": 900}), ("phone", {"width": 390, "height": 844})):
            ctx = b.new_context(viewport=vp, device_scale_factor=1)
            # block remote fonts and images so screenshots don't hang offline
            ctx.route("**/*", lambda route: route.abort() if not route.request.url.startswith("http://127.0.0.1") else route.continue_())
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "net::" not in m.text and "Failed to load resource" not in m.text else None)
            for path in pages:
                errs.clear()
                pg.goto(f"http://127.0.0.1:8765/{path}", wait_until="domcontentloaded")
                pg.wait_for_timeout(700)
                fn = os.path.join(out, f"{name}-{path.replace('/', '_').replace('.html', '')}.png")
                pg.screenshot(path=fn, full_page=(name == "desk"))
                if errs:
                    print(name, path, "JS errors:", errs[:5])
            ctx.close()
        b.close()
    httpd.shutdown()
    print("screenshots in", out)


if __name__ == "__main__":
    main()
