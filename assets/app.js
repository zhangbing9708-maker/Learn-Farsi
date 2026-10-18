/* Learn Farsi – everything interactive. No frameworks; works on any static host. */
(function () {
  "use strict";
  var R = document.body.getAttribute("data-root") || "";
  var ZWNJ = "‌";
  var MIN = 60000, HOUR = 3600000, DAY = 86400000;

  /* ---------------------------------------------------------- storage */
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem("lf:" + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem("lf:" + k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  };

  /* ---------------------------------------------------------- helpers */
  function $(s, el) { return (el || document).querySelector(s); }
  function $$(s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); }
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null || attrs[k] === false) continue;
      if (k === "text") el.textContent = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      if (Array.isArray(c)) c.forEach(function (x) { if (x != null) el.append(x); });
      else el.append(c);
    }
    return el;
  }
  function isFa(s) { return /[؀-ۿ]/.test(s || ""); }
  function faEl(tag, text, cls) { return h(tag, { lang: "fa", dir: "rtl", "class": cls || null, text: text }); }
  function norm(s) {
    return String(s || "").replace(/[ً-ْٰ]/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").replace(/[أإ]/g, "ا")
      .replace(/[‌\s.,،؛:؟?!«»"'()\-–—…]/g, "");
  }
  function normLat(s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[\s\-'’`.,!?;:]/g, "");
  }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function faNum(n) { return String(n).replace(/[0-9]/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹"[d]; }); }
  function enNum(s) { return String(s).replace(/[۰-۹]/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹".indexOf(d); }).replace(/[٠-٩]/g, function (d) { return "٠١٢٣٤٥٦٧٨٩".indexOf(d); }); }
  function hash(s) { var x = 5381; for (var i = 0; i < s.length; i++) x = ((x << 5) + x + s.charCodeAt(i)) >>> 0; return x.toString(36); }
  var SAY_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path class="w" d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12"/></svg>';
  function sayBtn(a, label) { return a ? h("button", { "class": "say", type: "button", "data-a": a, "aria-label": label || "Listen", html: SAY_SVG }) : null; }

  /* ---------------------------------------------------------- menu */
  var menuBtn = $(".menu-btn"), menu = $("#menu");
  if (menuBtn && menu) menuBtn.addEventListener("click", function () {
    var open = menu.classList.toggle("open");
    menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", function (e) {
    $$(".tools details[open]").forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });

  /* ---------------------------------------------------------- audio */
  var audio = new Audio(), curBtn = null, onEnd = null;
  audio.preload = "none";
  function play(a, btn, done) {
    if (!a) { if (done) done(); return; }
    if (curBtn) curBtn.classList.remove("on");
    curBtn = btn || null;
    if (curBtn) curBtn.classList.add("on");
    onEnd = done || null;
    var V = window.LFVoice;
    if (V && V.prefer() && V.has(a)) {          /* a friend's recording, if the learner prefers it */
      V.url(a).then(function (u) { start(u); }, function () { start(R + "data/audio/fa/" + a + ".mp3"); });
      return;
    }
    start(R + "data/audio/fa/" + a + ".mp3");
  }
  function start(src) {
    audio.src = src;
    var p = audio.play();
    if (p && p.catch) p.catch(function () { finish(); });
  }
  function finish() { if (curBtn) curBtn.classList.remove("on"); curBtn = null; var f = onEnd; onEnd = null; if (f) f(); }
  audio.addEventListener("ended", finish);
  audio.addEventListener("error", finish);
  window.LF = { R: R, h: h, faEl: faEl, isFa: isFa, store: store, $: $, $$: $$, play: play,
    stop: function () { audio.pause(); finish(); } };
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".say, .ab-btn");
    if (b && b.getAttribute("data-a")) { e.preventDefault(); stopAll(); play(b.getAttribute("data-a"), b); return; }
    var fa = e.target.closest(".ln > .ln-b > .fa");
    if (fa) {
      var ln = fa.closest(".ln");
      if (ln.closest(".story-text.as-text")) ln.classList.toggle("open");
      if (ln.getAttribute("data-a") && !window.getSelection().toString()) { stopAll(); play(ln.getAttribute("data-a"), $(".say", ln)); }
      return;
    }
    var en = e.target.closest(".ln .en, .vw-en, .ln .lit");
    if (en && document.body.classList.contains("hide-en")) { var p = en.closest(".ln, .vw"); if (p) p.classList.toggle("peek"); }
  });

  /* play all lines of the page, one after another */
  var playing = false;
  function stopAll() { if (!playing) return; playing = false; $$(".ln.playing").forEach(function (x) { x.classList.remove("playing"); }); $$("[data-playall]").forEach(function (b) { b.classList.remove("on"); b.textContent = "Play all"; }); }
  $$("[data-playall]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (playing) { stopAll(); audio.pause(); finish(); return; }
      var lines = $$("main .ln[data-a]").filter(function (x) { return !x.closest(".ex") && x.offsetParent !== null; });
      if (!lines.length) return;
      playing = true; btn.classList.add("on"); btn.textContent = "Stop";
      var i = 0;
      (function next() {
        $$(".ln.playing").forEach(function (x) { x.classList.remove("playing"); });
        if (!playing || i >= lines.length) { stopAll(); return; }
        var ln = lines[i++];
        ln.classList.add("playing");
        ln.scrollIntoView({ block: "center", behavior: "smooth" });
        play(ln.getAttribute("data-a"), $(".say", ln), function () { setTimeout(next, 450); });
      })();
    });
  });

  /* ---------------------------------------------------------- show / hide */
  var prefs = store.get("prefs", { tr: true, en: true, col: true });
  function applyPrefs() {
    ["tr", "en", "col"].forEach(function (k) {
      document.body.classList.toggle("hide-" + k, prefs[k] === false);
      $$('[data-toggle="' + k + '"]').forEach(function (b) { b.setAttribute("aria-pressed", prefs[k] === false ? "false" : "true"); });
    });
  }
  $$("[data-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      var k = b.getAttribute("data-toggle");
      prefs[k] = prefs[k] === false;
      store.set("prefs", prefs); applyPrefs();
      $$(".peek").forEach(function (x) { x.classList.remove("peek"); });
    });
  });
  applyPrefs();
  var astext = $("[data-astext]");
  if (astext) astext.addEventListener("click", function () {
    var t = $(".story-text");
    var on = t.classList.toggle("as-text");
    astext.textContent = on ? "Read line by line" : "Read as continuous text";
  });

  /* ---------------------------------------------------------- saved words (flashcards) */
  function deck() { return store.get("deck", {}); }
  function saveDeck(d) { store.set("deck", d); }
  function cardId(fa) { return "c" + hash(norm(fa)); }
  function addCard(c, d) {
    d = d || deck();
    var id = cardId(c.fa);
    if (!d[id]) d[id] = { id: id, fa: c.fa, r: c.r || "", en: c.en || "", a: c.a || "", src: c.src || "", added: Date.now(), state: "new" };
    return d;
  }
  function markSaved() {
    var d = deck();
    $$(".save[data-card]").forEach(function (b) {
      try { var c = JSON.parse(b.getAttribute("data-card")); var on = !!d[cardId(c.fa)]; b.classList.toggle("saved", on); b.textContent = on ? "✓" : "+"; b.setAttribute("aria-pressed", on ? "true" : "false"); } catch (e) {}
    });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".save[data-card]");
    if (b) {
      var c = JSON.parse(b.getAttribute("data-card")), d = deck(), id = cardId(c.fa);
      if (d[id]) delete d[id]; else addCard(c, d);
      saveDeck(d); markSaved(); return;
    }
    var all = e.target.closest("[data-save-all]");
    if (all) {
      var sec = all.closest("section") || document, d2 = deck();
      $$(".save[data-card]", sec).forEach(function (x) { addCard(JSON.parse(x.getAttribute("data-card")), d2); });
      saveDeck(d2); markSaved(); all.textContent = "Saved – review them in My flashcards";
    }
  });
  markSaved();

  /* ---------------------------------------------------------- lesson progress */
  var done = store.get("done", {});
  var lessonEl = $("article.lesson[data-lesson]");
  if (lessonEl) store.set("last", { u: location.pathname.split("/").slice(-2).join("/"), t: (document.title || "").replace(/ – Learn Farsi$/, "") });
  $$("[data-done]").forEach(function (b) {
    var id = b.getAttribute("data-done");
    function show() { var on = !!done[id]; b.classList.toggle("is-done", on); b.textContent = on ? "Done ✓ – tap to undo" : "Mark this lesson as done"; }
    b.addEventListener("click", function () {
      var now = !done[id];
      if (now) done[id] = Date.now(); else delete done[id];
      store.set("done", done); show();
      if (now) document.dispatchEvent(new CustomEvent("lf:done", { detail: { id: id } }));
    });
    show();
  });
  $$("[data-done-mark]").forEach(function (m) { if (done[m.getAttribute("data-done-mark")]) { m.classList.add("on"); m.setAttribute("title", "Done"); } });
  $$("[data-level-lessons]").forEach(function (el) {
    var ids = (el.getAttribute("data-level-lessons") || "").split(",").filter(Boolean);
    if (!ids.length) return;
    var n = ids.filter(function (i) { return done[i]; }).length;
    if (el.classList.contains("step-prog")) { el.innerHTML = '<span class="bar"><span style="width:' + Math.round(100 * n / ids.length) + '%"></span></span>'; return; }
    el.innerHTML = n ? n + " of " + ids.length + " done" + '<span class="bar"><span style="width:' + Math.round(100 * n / ids.length) + '%"></span></span>' : "";
  });
  var last = store.get("last", null);
  $$("[data-resume]").forEach(function (el) {
    if (!last || !last.u) return;
    var u = last.u.indexOf("course/") === 0 ? last.u : "course/" + last.u.split("/").pop();
    el.innerHTML = "";
    el.append("Continue where you left off: ", h("a", { href: R + u, text: last.t || "your last lesson" }));
  });

  /* ---------------------------------------------------------- Persian keyboard */
  var KB = [["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح", "ج", "چ"], ["ش", "س", "ی", "ب", "ل", "ا", "ت", "ن", "م", "ک", "گ"],
    ["ظ", "ط", "ز", "ر", "ذ", "د", "پ", "و", "آ", "ژ", "ئ", "ء"]];
  var kbTarget = null;
  document.addEventListener("focusin", function (e) { if (e.target.matches && e.target.matches("input, textarea")) kbTarget = e.target; });
  function insertAt(el, s) {
    if (!el) return;
    var a = el.selectionStart == null ? el.value.length : el.selectionStart, b = el.selectionEnd == null ? a : el.selectionEnd;
    if (s === "\b") { if (a === b && a > 0) a--; el.value = el.value.slice(0, a) + el.value.slice(b); el.setSelectionRange(a, a); }
    else { el.value = el.value.slice(0, a) + s + el.value.slice(b); el.setSelectionRange(a + s.length, a + s.length); }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.focus();
  }
  function keyboard() {
    var box = h("div", { "class": "kbd", role: "group", "aria-label": "Persian keyboard" });
    KB.forEach(function (row) {
      box.append(h("div", { "class": "kbd-row" }, row.map(function (k) {
        return h("button", { type: "button", text: k, onmousedown: function (e) { e.preventDefault(); }, onclick: function () { insertAt(kbTarget, k); } });
      })));
    });
    box.append(h("div", { "class": "kbd-row" },
      h("button", { type: "button", "class": "wide", text: "half-space", title: "ZWNJ, as in می‌روم", onmousedown: function (e) { e.preventDefault(); }, onclick: function () { insertAt(kbTarget, ZWNJ); } }),
      h("button", { type: "button", "class": "wide", text: "space", onmousedown: function (e) { e.preventDefault(); }, onclick: function () { insertAt(kbTarget, " "); } }),
      h("button", { type: "button", "class": "wide", text: "delete", onmousedown: function (e) { e.preventDefault(); }, onclick: function () { insertAt(kbTarget, "\b"); } })));
    return box;
  }
  function kbToggle(container) {
    var kb = null;
    return h("button", { type: "button", "class": "ex-small", text: "Persian keyboard", onclick: function () {
      if (kb) { kb.remove(); kb = null; return; }
      kb = keyboard(); container.append(kb);
    } });
  }

  /* ---------------------------------------------------------- exercises */
  function score(box, right, total) {
    var s = $(".ex-score", box) || box.appendChild(h("p", { "class": "ex-score" }));
    s.textContent = right + " of " + total + " right" + (right === total ? " – excellent!" : "");
    document.dispatchEvent(new CustomEvent("lf:score", { detail: { right: right, total: total, box: box } }));
  }
  var EX = {
    mcq: function (body, items, box) {
      var answered = 0, right = 0;
      items.forEach(function (it) {
        var fb = h("p", { "class": "ex-fb", "aria-live": "polite" });
        var opts = h("div", { "class": "ex-opts" });
        (it.o || []).forEach(function (o, i) {
          var b = h("button", { type: "button", "class": "ex-opt", text: o, dir: isFa(o) ? "rtl" : null, lang: isFa(o) ? "fa" : null });
          b.addEventListener("click", function () {
            $$("button", opts).forEach(function (x, j) { x.disabled = true; if (j === it.ans) x.classList.add("right"); });
            if (i === it.ans) { right++; fb.className = "ex-fb right"; fb.innerHTML = "Right. " + (it.x || ""); }
            else { b.classList.add("wrong"); fb.className = "ex-fb wrong"; fb.innerHTML = "Not quite. " + (it.x || ""); }
            answered++; if (answered === items.length) score(box, right, items.length);
          });
          opts.append(b);
        });
        body.append(h("div", { "class": "ex-item" }, h("p", { "class": "ex-q", html: it.q }), opts, fb));
      });
    },
    listen: function (body, items, box) {
      var answered = 0, right = 0;
      items.forEach(function (it, n) {
        var fb = h("p", { "class": "ex-fb", "aria-live": "polite" });
        var reveal = h("div", { "class": "ex-ans", hidden: true }, faEl("p", it.fa, "fa"), h("p", { "class": "tr", text: it.r }), h("p", { text: it.en }));
        var opts = h("div", { "class": "ex-opts" });
        (it.o || []).forEach(function (o, i) {
          var b = h("button", { type: "button", "class": "ex-opt", text: o, dir: isFa(o) ? "rtl" : null, lang: isFa(o) ? "fa" : null });
          b.addEventListener("click", function () {
            $$("button", opts).forEach(function (x, j) { x.disabled = true; if (j === it.ans) x.classList.add("right"); });
            if (i === it.ans) { right++; fb.className = "ex-fb right"; fb.textContent = "Right."; } else { b.classList.add("wrong"); fb.className = "ex-fb wrong"; fb.textContent = "Not quite – listen again."; }
            reveal.hidden = false; answered++; if (answered === items.length) score(box, right, items.length);
          });
          opts.append(b);
        });
        var head = h("div", { "class": "ex-row" }, it.a ? sayBtn(it.a, "Play sentence " + (n + 1)) : h("button", { type: "button", "class": "ex-small", text: "No audio – show the sentence", onclick: function () { reveal.hidden = false; } }), h("span", { text: "Sentence " + (n + 1) }));
        body.append(h("div", { "class": "ex-item" }, head, opts, fb, reveal));
      });
    },
    fill: function (body, items, box) {
      var right = 0, checked = 0;
      items.forEach(function (it) {
        var parts = (it.fa || "").split("___");
        var inp = h("input", { type: "text", lang: "fa", dir: "rtl", autocomplete: "off", "aria-label": "Missing word" + (it.hint ? ": " + it.hint : "") });
        var sent = h("p", { "class": "ex-sent", lang: "fa", dir: "rtl" }, parts[0] || "", inp, parts[1] || "");
        var fb = h("p", { "class": "ex-fb", "aria-live": "polite" });
        var done1 = false;
        function check() {
          var v = inp.value.trim();
          if (!v) return;
          var ok = isFa(v) ? norm(v) === norm(it.ans) : (it.ansR && normLat(v) === normLat(it.ansR));
          inp.classList.toggle("right", !!ok); inp.classList.toggle("wrong", !ok);
          fb.className = "ex-fb " + (ok ? "right" : "wrong");
          fb.innerHTML = "";
          fb.append(ok ? "Right: " : "The answer is ", faEl("bdi", it.ans), it.ansR ? " (" + it.ansR + ")" : "");
          if (!done1) { done1 = true; checked++; if (ok) right++; if (checked === items.length) score(box, right, items.length); }
        }
        inp.addEventListener("keydown", function (e) { if (e.key === "Enter") check(); });
        var row = h("div", { "class": "ex-row" }, h("button", { type: "button", "class": "ex-small", text: "Check", onclick: check }),
          it.hint ? h("span", { "class": "meta", text: "Hint: " + it.hint }) : null);
        var item = h("div", { "class": "ex-item" }, sent, h("p", { "class": "tr", text: it.r }), h("p", { "class": "meta", text: it.en }), row, fb);
        row.append(kbToggle(item));
        body.append(item);
      });
    },
    translate: function (body, items) {
      items.forEach(function (it) {
        var inp = h("input", { type: "text", lang: "fa", dir: "auto", autocomplete: "off", placeholder: "Type in Persian or transliteration", "aria-label": "Your translation" });
        inp.style.width = "100%";
        var ans = h("div", { "class": "ex-ans", hidden: true }, h("div", { "class": "ex-row" }, sayBtn(it.a), faEl("p", it.fa, "fa")), h("p", { "class": "tr", text: it.r }));
        var fb = h("p", { "class": "ex-fb", "aria-live": "polite" });
        function show() {
          var v = inp.value.trim();
          if (v) {
            var ok = isFa(v) ? norm(v) === norm(it.fa) : normLat(v) === normLat(it.r);
            fb.className = "ex-fb " + (ok ? "right" : ""); fb.textContent = ok ? "Exactly right." : "Compare yours with the answer:";
          }
          ans.hidden = false;
          if (it.a) play(it.a, $(".say", ans));
        }
        inp.addEventListener("keydown", function (e) { if (e.key === "Enter") show(); });
        var item = h("div", { "class": "ex-item" }, h("p", { "class": "ex-q", text: it.en }), inp,
          h("div", { "class": "ex-row" }, h("button", { type: "button", "class": "ex-small", text: "Show answer", onclick: show })), fb, ans);
        $(".ex-row", item).append(kbToggle(item));
        body.append(item);
      });
    },
    match: function (body, items, box) {
      var pairs = items.slice(0, 8);
      var left = h("div", { "class": "match-col" }), rightc = h("div", { "class": "match-col" });
      var selL = null, selR = null, doneN = 0, tries = 0;
      function tryPair() {
        if (!selL || !selR) return;
        tries++;
        if (selL.getAttribute("data-i") === selR.getAttribute("data-i")) {
          [selL, selR].forEach(function (b) { b.classList.remove("sel"); b.classList.add("done"); b.disabled = true; });
          var a = pairs[+selL.getAttribute("data-i")].a; if (a) play(a);
          doneN++;
          if (doneN === pairs.length) score(box, pairs.length, tries);
        } else {
          [selL, selR].forEach(function (b) { b.classList.remove("sel"); b.classList.add("no"); setTimeout(function () { b.classList.remove("no"); }, 350); });
        }
        selL = selR = null;
      }
      shuffle(pairs.map(function (p, i) { return i; })).forEach(function (i) {
        var p = pairs[i];
        left.append(h("button", { type: "button", "class": "m-fa", "data-i": i, lang: "fa", onclick: function (e) { var b = e.currentTarget; if (selL) selL.classList.remove("sel"); selL = b; b.classList.add("sel"); tryPair(); } },
          p.fa, h("small", { text: p.r })));
      });
      shuffle(pairs.map(function (p, i) { return i; })).forEach(function (i) {
        rightc.append(h("button", { type: "button", "data-i": i, text: pairs[i].en, onclick: function (e) { var b = e.currentTarget; if (selR) selR.classList.remove("sel"); selR = b; b.classList.add("sel"); tryPair(); } }));
      });
      body.append(h("div", { "class": "match" }, left, rightc));
      box.addEventListener("ex-score", function () {});
      score = (function (orig) { return function (bx, n, t) { if (bx === box) { var s = $(".ex-score", box) || box.appendChild(h("p", { "class": "ex-score" })); s.textContent = "All matched in " + t + " tries" + (t === n ? " – perfect!" : "."); } else orig(bx, n, t); }; })(score);
    },
    order: function (body, items) {
      items.forEach(function (it) {
        var toks = (it.fa || "").split(/\s+/).filter(Boolean), rt = (it.r || "").split(/\s+/);
        var withR = rt.length === toks.length;
        var built = h("div", { "class": "order-built", "aria-label": "Your sentence" }), pool = h("div", { "class": "order-pool" });
        var fb = h("p", { "class": "ex-fb", "aria-live": "polite" });
        function tile(i) {
          return h("button", { type: "button", "class": "tile-w", "data-i": i, lang: "fa", onclick: function (e) {
            var b = e.currentTarget;
            (b.parentNode === pool ? built : pool).append(b);
            fb.textContent = ""; fb.className = "ex-fb";
            if (!pool.children.length) {
              var s = $$("button", built).map(function (x) { return toks[+x.getAttribute("data-i")]; }).join(" ");
              var ok = norm(s) === norm(it.fa);
              fb.className = "ex-fb " + (ok ? "right" : "wrong");
              fb.textContent = ok ? "Right!" : "Not yet – tap words to move them back.";
              if (ok && it.a) play(it.a);
            }
          } }, toks[i], withR ? h("small", { text: rt[i] }) : null);
        }
        var idx = shuffle(toks.map(function (t, i) { return i; }));
        if (idx.length > 1 && idx.every(function (v, i) { return v === i; })) idx.reverse();
        idx.forEach(function (i) { pool.append(tile(i)); });
        body.append(h("div", { "class": "ex-item" }, h("p", { "class": "ex-q", text: it.en }), built, pool, fb,
          h("div", { "class": "ex-row" }, h("button", { type: "button", "class": "ex-small", text: "Show answer", onclick: function () { fb.className = "ex-fb"; fb.innerHTML = ""; fb.append(faEl("bdi", it.fa), " – " + it.r); } }))));
      });
    }
  };
  $$(".ex").forEach(function (box) {
    var data;
    try { data = JSON.parse($(".ex-data", box).textContent); } catch (e) { return; }
    var body = $(".ex-body", box); body.innerHTML = "";
    if (EX[data.kind]) EX[data.kind](body, data.items || [], box);
  });

  /* ---------------------------------------------------------- idioms filter */
  var idf = $("[data-idiom-filter]");
  if (idf) idf.addEventListener("change", function () {
    var k = $('[data-f="kind"]', idf).value, c = $('[data-f="cat"]', idf).value;
    $$(".idiom").forEach(function (li) { li.hidden = (k && li.getAttribute("data-kind") !== k) || (c && li.getAttribute("data-cat") !== c); });
  });

  /* ---------------------------------------------------------- calendar (jalaali algorithm, after jalaali-js, MIT) */
  function div(a, b) { return ~~(a / b); }
  function mod(a, b) { return a - ~~(a / b) * b; }
  var BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178];
  function jalCal(jy) {
    var gy = jy + 621, leapJ = -14, jp = BREAKS[0], jm, jump = 0, leap, n, i;
    for (i = 1; i < BREAKS.length; i++) { jm = BREAKS[i]; jump = jm - jp; if (jy < jm) break; leapJ += div(jump, 33) * 8 + div(mod(jump, 33), 4); jp = jm; }
    n = jy - jp;
    leapJ += div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
    if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1;
    var leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150, march = 20 + leapJ - leapG;
    if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33;
    leap = mod(mod(n + 1, 33) - 1, 4); if (leap === -1) leap = 4;
    return { leap: leap, gy: gy, march: march };
  }
  function g2d(gy, gm, gd) {
    var d = div((gy + div(gm - 8, 6) + 100100) * 1461, 4) + div(153 * mod(gm + 9, 12) + 2, 5) + gd - 34840408;
    return d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
  }
  function d2g(jdn) {
    var j = 4 * jdn + 139361631; j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
    var i = div(mod(j, 1461), 4) * 5 + 308, gd = div(mod(i, 153), 5) + 1, gm = mod(div(i, 153), 12) + 1;
    return { gy: div(j, 1461) - 100100 + div(8 - gm, 6), gm: gm, gd: gd };
  }
  function j2d(jy, jm, jd) { var r = jalCal(jy); return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1; }
  function d2j(jdn) {
    var gy = d2g(jdn).gy, jy = gy - 621, r = jalCal(jy), k = jdn - g2d(gy, 3, r.march), jm, jd;
    if (k >= 0) { if (k <= 185) return { jy: jy, jm: 1 + div(k, 31), jd: mod(k, 31) + 1 }; k -= 186; }
    else { jy -= 1; k += 179; if (r.leap === 1) k += 1; }
    jm = 7 + div(k, 30); jd = mod(k, 30) + 1;
    return { jy: jy, jm: jm, jd: jd };
  }
  var MONTHS = [["فروردین", "Farvardin", "spring"], ["اردیبهشت", "Ordibehesht", "spring"], ["خرداد", "Khordād", "spring"], ["تیر", "Tir", "summer"], ["مرداد", "Mordād", "summer"], ["شهریور", "Shahrivar", "summer"],
    ["مهر", "Mehr", "autumn"], ["آبان", "Ābān", "autumn"], ["آذر", "Āzar", "autumn"], ["دی", "Dey", "winter"], ["بهمن", "Bahman", "winter"], ["اسفند", "Esfand", "winter"]];
  var DAYS = [["شنبه", "shanbe", "Saturday"], ["یکشنبه", "yekshanbe", "Sunday"], ["دوشنبه", "doshanbe", "Monday"], ["سه‌شنبه", "seshanbe", "Tuesday"], ["چهارشنبه", "chahārshanbe", "Wednesday"], ["پنجشنبه", "panjshanbe", "Thursday"], ["جمعه", "jom'e", "Friday"]];
  function persianDate(d) {
    var j = d2j(g2d(d.getFullYear(), d.getMonth() + 1, d.getDate())), wd = DAYS[(d.getDay() + 1) % 7], m = MONTHS[j.jm - 1];
    return { j: j, wd: wd, m: m, fa: wd[0] + " " + faNum(j.jd) + " " + m[0] + " " + faNum(j.jy), r: wd[1] + " " + j.jd + " " + m[1] + " " + j.jy };
  }
  var now = new Date(), pd = persianDate(now);
  $$("[data-today-short]").forEach(function (el) { el.innerHTML = ""; el.append("Today in Iran: ", faEl("bdi", pd.fa), " – " + pd.r); });
  $$("[data-today]").forEach(function (el) {
    el.innerHTML = "";
    el.append(faEl("span", pd.fa, "fa"), h("span", { text: pd.r + " (" + pd.wd[2] + "), the " + pd.j.jd + (pd.j.jd === 1 ? "st" : pd.j.jd === 2 ? "nd" : pd.j.jd === 3 ? "rd" : "th") + " day of " + pd.m[1] + ", the " + pd.j.jm + (pd.j.jm < 4 ? ["st", "nd", "rd"][pd.j.jm - 1] : "th") + " month, in the year " + pd.j.jy + "." }));
  });
  $$("[data-months]").forEach(function (ol) {
    MONTHS.forEach(function (m, i) { ol.append(h("li", null, faEl("bdi", m[0]), " " + m[1] + " – " + (i < 6 ? 31 : i < 11 ? 30 : "29 or 30") + " days, " + m[2])); });
  });
  var g2j = $("[data-g2j]"), j2g = $("[data-j2g]");
  if (g2j) {
    g2j.value = now.toISOString().slice(0, 10);
    var g2jo = $("[data-g2j-out]");
    var upd = function () { var p = g2j.value.split("-").map(Number); if (p.length !== 3 || !p[0]) return; var x = persianDate(new Date(p[0], p[1] - 1, p[2])); g2jo.innerHTML = ""; g2jo.append(faEl("bdi", x.fa), " – " + x.r); };
    g2j.addEventListener("input", upd); upd();
  }
  if (j2g) {
    var j2go = $("[data-j2g-out]");
    j2g.value = pd.j.jy + "/" + pd.j.jm + "/" + pd.j.jd;
    var upd2 = function () {
      var p = enNum(j2g.value).split(/[\/\-. ]/).map(Number);
      if (p.length !== 3 || !p[0] || p[1] < 1 || p[1] > 12 || p[2] < 1 || p[2] > 31) { j2go.textContent = "Write the date as year/month/day, e.g. 1405/1/1."; return; }
      var g = d2g(j2d(p[0], p[1], p[2])), dt = new Date(g.gy, g.gm - 1, g.gd);
      j2go.textContent = dt.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    };
    j2g.addEventListener("input", upd2); upd2();
  }

  /* ---------------------------------------------------------- numbers */
  var ONES = [["", ""], ["یک", "yek"], ["دو", "do"], ["سه", "se"], ["چهار", "chahār"], ["پنج", "panj"], ["شش", "shesh"], ["هفت", "haft"], ["هشت", "hasht"], ["نه", "noh"]];
  var TEENS = [["ده", "dah"], ["یازده", "yāzdah"], ["دوازده", "davāzdah"], ["سیزده", "sizdah"], ["چهارده", "chahārdah"], ["پانزده", "pānzdah"], ["شانزده", "shānzdah"], ["هفده", "hefdah"], ["هجده", "hejdah"], ["نوزده", "nuzdah"]];
  var TENS = [["", ""], ["", ""], ["بیست", "bist"], ["سی", "si"], ["چهل", "chehel"], ["پنجاه", "panjāh"], ["شصت", "shast"], ["هفتاد", "haftād"], ["هشتاد", "hashtād"], ["نود", "navad"]];
  var HUND = [["", ""], ["صد", "sad"], ["دویست", "devist"], ["سیصد", "sisad"], ["چهارصد", "chahārsad"], ["پانصد", "pānsad"], ["ششصد", "sheshsad"], ["هفتصد", "haftsad"], ["هشتصد", "hashtsad"], ["نهصد", "nohsad"]];
  var SCALE = [["", ""], ["هزار", "hezār"], ["میلیون", "milyun"], ["میلیارد", "milyārd"], ["تریلیون", "teriliyun"]];
  function below1000(n) {
    var out = [], hu = Math.floor(n / 100), rest = n % 100;
    if (hu) out.push(HUND[hu]);
    if (rest >= 10 && rest < 20) out.push(TEENS[rest - 10]);
    else { if (Math.floor(rest / 10)) out.push(TENS[Math.floor(rest / 10)]); if (rest % 10) out.push(ONES[rest % 10]); }
    return out;
  }
  function numWords(n) {
    if (n === 0) return ["صفر", "sefr"];
    var groups = [], i = 0;
    while (n > 0) {
      var g = n % 1000; n = Math.floor(n / 1000);
      if (g) {
        var w = below1000(g);
        if (i) {
          var fa = (i === 1 && g === 1) ? "" : w.map(function (x) { return x[0]; }).join(" ");
          var r = (i === 1 && g === 1) ? "" : w.map(function (x) { return x[1]; }).join(" ");
          w = [[(fa ? fa + " " : "") + SCALE[i][0], (r ? r + " " : "") + SCALE[i][1]]];
        }
        groups.unshift(w);
      }
      i++;
    }
    var flat = [].concat.apply([], groups);
    return [flat.map(function (x) { return x[0]; }).join(" و "), flat.map(function (x) { return x[1]; }).join(" o ")];
  }
  var numIn = $("[data-num-in]"), numOut = $("[data-num-out]");
  if (numIn) {
    var updN = function () {
      var raw = enNum(numIn.value).replace(/[,\s٬]/g, "");
      numOut.innerHTML = "";
      if (!/^\d{1,15}$/.test(raw)) { numOut.textContent = "Type a whole number (up to 15 digits)."; return; }
      var n = Number(raw), w = numWords(n);
      var grouped = raw.length > 4 ? raw.replace(/\B(?=(\d{3})+(?!\d))/g, "٬") : raw;
      numOut.append(h("p", { "class": "big-d", lang: "fa", text: faNum(grouped) }), faEl("p", w[0], "big-fa"), h("p", { "class": "tr", text: w[1] }));
      if (n >= 1300 && n <= 1500) numOut.append(h("p", { "class": "meta", text: "As an Iranian year, " + n + " began in March " + (n + 621) + "." }));
    };
    numIn.addEventListener("input", updN); updN();
  }

  /* ---------------------------------------------------------- verbs */
  var PERS = [["من", "man"], ["تو", "to"], ["او", "u"], ["ما", "mā"], ["شما", "shomā"], ["آن‌ها", "ān-hā"]];
  var EP = [["م", "am"], ["ی", "i"], ["د", "ad"], ["یم", "im"], ["ید", "id"], ["ند", "and"]];
  var EPAST = [["م", "am"], ["ی", "i"], ["", ""], ["یم", "im"], ["ید", "id"], ["ند", "and"]];
  var PERF = [["‌ام", "-am"], ["‌ای", "-i"], [" است", " ast"], ["‌ایم", "-im"], ["‌اید", "-id"], ["‌اند", "-and"]];
  function lastWord(s) { var i = s.lastIndexOf(" "); return [i < 0 ? "" : s.slice(0, i + 1), s.slice(i + 1)]; }
  var VPREF = [["فرا", "farā"], ["باز", "bāz"], ["بر", "bar"], ["در", "dar"], ["وا", "vā"]];
  var BASES = { "گشتن": 1, "گرداندن": 1, "داشتن": 1, "آوردن": 1, "آمدن": 1, "خاستن": 1, "خوردن": 1, "گذشتن": 1, "ماندن": 1, "رسیدن": 1, "کردن": 1, "گرفتن": 1, "انداختن": 1, "کشیدن": 1, "شدن": 1, "زدن": 1 };
  function conjugate(v) {
    var f = lastWord(v.inf), fr = lastWord(v.r || ""), s = lastWord(v.stem || ""), sr = lastWord(v.stemR || "");
    var pre = f[0], preR = fr[0], inf = f[1], infR = fr[1], st = s[1], stR = sr[1];
    var compound = !!pre, useSubj = !!v.subj;
    // verbs with a separable prefix: برگشتن → برمی‌گردم, برنگشتم, برگرد
    if (!compound) VPREF.some(function (p) {
      var rest = inf.slice(p[0].length);
      if (inf.indexOf(p[0]) === 0 && st.indexOf(p[0]) === 0 && BASES[rest] && infR.indexOf(p[1]) === 0) {
        pre = p[0]; preR = p[1] + "-"; inf = rest; infR = infR.slice(p[1].length).replace(/^-/, ""); st = st.slice(p[0].length); stR = stR.slice(p[1].length).replace(/^-/, "");
        compound = true; useSubj = false; return true;
      }
      return false;
    });
    var past = inf.replace(/ن$/, ""), pastR = infR.replace(/an$/, "");
    var vowel = /[aeiouā]$/.test(stR);
    var isBudan = inf === "بودن", isDashtan = inf === "داشتن" && pre !== "نگه " && pre !== "بر";
    function pres(stem, stemR, e) { return [stem + (vowel ? "ی" : "") + e[0], stemR + (vowel ? "y" : "") + e[1]]; }
    function neg(stem, stemR) {
      if (stem[0] === "آ") return ["نیا" + stem.slice(1), "na-y" + stemR];
      if (stem[0] === "ا") return ["نی" + stem.slice(1), "na-y" + stemR];
      return ["ن" + stem, "na-" + stemR];
    }
    function subjStem() {
      if (useSubj) return [v.subj, v.subjR || ""];
      if (compound) return [st, stR];
      if (st[0] === "آ") return ["بیا" + st.slice(1), "bi-y" + stR];
      if (st[0] === "ا") return ["بی" + st.slice(1), "bi-y" + stR];
      return ["ب" + st, (v.pre || "be") + "-" + stR];
    }
    function P(fn) { return PERS.map(function (p, i) { var x = fn(i); return [p, [pre + x[0], preR + x[1]]]; }); }
    var T = [];
    if (isBudan) {
      var H = [["هستم", "hastam"], ["هستی", "hasti"], ["است", "ast"], ["هستیم", "hastim"], ["هستید", "hastid"], ["هستند", "hastand"]];
      T.push(["Present", "is, am, are", P(function (i) { return H[i]; })]);
      T.push(["Present, negative", "am not", P(function (i) { return ["نیست" + EP[i][0].replace(/^د$/, ""), "nist" + EP[i][1].replace(/^ad$/, "")]; })]);
      T.push(["Past", "was", P(function (i) { return ["بود" + EPAST[i][0], "bud" + EPAST[i][1]]; })]);
      T.push(["Past, negative", "was not", P(function (i) { return ["نبود" + EPAST[i][0], "na-bud" + EPAST[i][1]]; })]);
      T.push(["Present perfect", "have been", P(function (i) { return ["بوده" + PERF[i][0], "bude" + PERF[i][1]]; })]);
      T.push(["Subjunctive", "(that I) be", P(function (i) { return ["باش" + EP[i][0], "bāsh" + EP[i][1]]; })]);
      T.push(["Future", "will be", P(function (i) { return ["خواه" + EP[i][0] + " بود", "khāh" + EP[i][1] + " bud"]; })]);
      T.push(["Imperative", "be!", [[["تو", "to"], [pre + "باش", preR + "bāsh"]], [["شما", "shomā"], [pre + "باشید", preR + "bāshid"]], [["تو, not", "to"], [pre + "نباش", preR + "na-bāsh"]]]]);
      return T;
    }
    T.push(["Present", "I go, I am going", P(function (i) { var x = pres(st, stR, EP[i]); return isDashtan ? x : ["می‌" + x[0], "mi-" + x[1]]; })]);
    T.push(["Present, negative", "I don't go", P(function (i) { var x = pres(st, stR, EP[i]); if (isDashtan) { var n0 = neg(x[0], x[1]); return n0; } return ["نمی‌" + x[0], "nemi-" + x[1]]; })]);
    T.push(["Simple past", "I went", P(function (i) { return [past + EPAST[i][0], pastR + EPAST[i][1]]; })]);
    T.push(["Simple past, negative", "I didn't go", P(function (i) { var n = neg(past, pastR); return [n[0] + EPAST[i][0], n[1] + EPAST[i][1]]; })]);
    if (!isDashtan) T.push(["Past continuous", "I was going, I used to go", P(function (i) { return ["می‌" + past + EPAST[i][0], "mi-" + pastR + EPAST[i][1]]; })]);
    T.push(["Present perfect", "I have gone", P(function (i) { return [past + "ه" + PERF[i][0], pastR + "e" + PERF[i][1]]; })]);
    T.push(["Past perfect", "I had gone", P(function (i) { return [past + "ه بود" + EPAST[i][0], pastR + "e bud" + EPAST[i][1]]; })]);
    if (isDashtan) {
      T.push(["Subjunctive", "(that) I have", P(function (i) { return ["داشته باش" + EP[i][0], "dāshte bāsh" + EP[i][1]]; })]);
    } else {
      var ss = subjStem();
      T.push(["Subjunctive", "(that) I go – after want, must, maybe", P(function (i) { return pres(ss[0], ss[1], EP[i]); })]);
      T.push(["Subjunctive, negative", "(that) I don't go", P(function (i) { var n = neg(st, stR); return pres(n[0], n[1], EP[i]); })]);
    }
    var sep = compound && !/ $/.test(pre) ? " " : "";
    T.push(["Future (formal)", "I will go", PERS.map(function (p, i) { return [p, [pre + sep + "خواه" + EP[i][0] + " " + past, preR.replace(/-$/, sep ? " " : "") + "khāh" + EP[i][1] + " " + pastR]]; })]);
    if (!isDashtan) {
      var AUX = [["دارم", "dāram"], ["داری", "dāri"], ["دارد", "dārad"], ["داریم", "dārim"], ["دارید", "dārid"], ["دارند", "dārand"]];
      T.push(["Right now (spoken)", "I'm going right now", PERS.map(function (p, i) { var x = pres(st, stR, EP[i]); return [p, [AUX[i][0] + " " + pre + "می‌" + x[0], AUX[i][1] + " " + preR + "mi-" + x[1]]]; })]);
    }
    if (isDashtan) {
      T.push(["Imperative", "have!", [[["تو", "to"], [pre + "داشته باش", preR + "dāshte bāsh"]], [["شما", "shomā"], [pre + "داشته باشید", preR + "dāshte bāshid"]]]]);
    } else {
      var s2 = subjStem(), ng = neg(st, stR);
      var sgR = s2[1].replace(/av$/, "o"), ngR = ng[1].replace(/av$/, "o");
      T.push(["Imperative", "go!", [[["تو", "to"], [pre + s2[0], preR + sgR]], [["شما", "shomā"], (function (x) { return [pre + x[0], preR + x[1]]; })(pres(s2[0], s2[1], ["ید", "id"]))],
        [["تو, not", "to"], [pre + ng[0], preR + ngR]], [["شما, not", "shomā"], (function (x) { return [pre + x[0], preR + x[1]]; })(pres(ng[0], ng[1], ["ید", "id"]))]]]);
    }
    return T;
  }
  function showConj(v, box) {
    box.innerHTML = ""; box.hidden = false;
    var grid = h("div", { "class": "conj-grid" });
    conjugate(v).forEach(function (t) {
      var tb = h("tbody");
      t[2].forEach(function (row) { tb.append(h("tr", null, h("td", { "class": "cp", text: row[0][0].indexOf(",") > 0 ? row[0][0] : row[0][1] }), h("td", { "class": "cf", lang: "fa", dir: "rtl", text: row[1][0] }), h("td", { "class": "tr", text: row[1][1] }))); });
      grid.append(h("div", { "class": "conj-t" }, h("h4", { text: t[0] }), h("p", { "class": "meta", text: t[1] }), h("table", null, tb)));
    });
    var ex = v.ex && v.ex.fa ? h("div", { "class": "ln ln-ex", "data-a": v.ex.a || null }, sayBtn(v.ex.a), h("div", { "class": "ln-b" }, faEl("p", v.ex.fa, "fa"), h("p", { "class": "tr", text: v.ex.r }), h("p", { "class": "en", text: v.ex.en }))) : null;
    box.append(h("h3", null, h("span", null, faEl("bdi", v.inf), " ", h("span", { "class": "tr", text: v.r }), " – " + (v.en || "")), h("span", { "class": "meta", text: "past stem " + v.inf.replace(/ن$/, "") + ", present stem " + v.stem })),
      v.note ? h("p", { "class": "note", text: v.note }) : null, ex, grid);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  var vdata = $("#verb-data"), conjBox = $("[data-conj]");
  if (conjBox) {
    var VERBS = []; try { VERBS = JSON.parse(vdata ? vdata.textContent : "[]"); } catch (e) {}
    $$(".verb-open").forEach(function (b) {
      b.addEventListener("click", function () { var li = b.closest(".verb"); li.parentNode.insertBefore(conjBox, li.nextSibling); showConj(VERBS[+li.getAttribute("data-i")], conjBox); });
    });
    var vq = $("[data-verb-q]");
    if (vq) vq.addEventListener("input", function () {
      var q = vq.value.trim(), qf = norm(q), ql = normLat(q), qe = q.toLowerCase();
      $$(".verb").forEach(function (li) {
        var v = VERBS[+li.getAttribute("data-i")] || {};
        li.hidden = !!q && !(norm(v.inf).indexOf(qf) >= 0 && isFa(q) || (!isFa(q) && (normLat(v.r).indexOf(ql) >= 0 || (v.en || "").toLowerCase().indexOf(qe) >= 0)));
      });
    });
    var go = $("[data-cv-go]");
    if (go) go.addEventListener("click", function () {
      var v = { inf: $('[data-cv="inf"]').value.trim(), r: $('[data-cv="r"]').value.trim(), stem: $('[data-cv="stem"]').value.trim(), stemR: $('[data-cv="stemR"]').value.trim(), en: "" };
      if (!v.inf || !v.stem) return;
      if (!/ن$/.test(v.inf)) { alertBox(go, "An infinitive ends in ن (-an), like نوشتن."); return; }
      go.closest("details").after(conjBox); showConj(v, conjBox);
    });
    var hashI = location.hash.match(/^#v(\d+)$/);
    if (hashI && VERBS[+hashI[1]]) { var li0 = $('.verb[data-i="' + hashI[1] + '"]'); if (li0) { li0.parentNode.insertBefore(conjBox, li0.nextSibling); showConj(VERBS[+hashI[1]], conjBox); } }
  }
  function alertBox(after, msg) { var p = h("p", { "class": "ex-fb wrong", text: msg }); after.after(p); setTimeout(function () { p.remove(); }, 4000); }

  /* ---------------------------------------------------------- dictionary */
  var dictList = $("[data-dict]");
  if (dictList) {
    var dq = $("[data-dict-q]"), dl = $("[data-dict-level]"), dli = $("[data-dict-list]"), dp = $("[data-dict-pos]"), dc = $("[data-dict-count]"), dm = $("[data-dict-more]");
    var D = null, conc = null, shown = 0, results = [];
    var params = new URLSearchParams(location.search); if (params.get("q")) dq.value = params.get("q");
    fetch(R + "data/dict.json").then(function (r) { return r.json(); }).then(function (d) {
      D = d;
      (d.lists || []).forEach(function (l) { dli.append(h("option", { value: "l" + l.n, text: l.t })); });
      (d.cats || []).forEach(function (c) { dli.append(h("option", { value: "c" + c.id, text: c.t })); });
      d.entries.forEach(function (e) { e._w = norm(e.w); e._r = normLat(e.r); e._g = (e.g || "").toLowerCase(); });
      search();
    }).catch(function () { dc.textContent = "The dictionary could not be loaded."; });
    function level(n) { return n <= 1000 ? 1 : n <= 3000 ? 2 : n <= 5000 ? 3 : 4; }
    var LV = ["", "Beginner", "Intermediate", "Advanced", "5,000+"];
    function search() {
      if (!D) return;
      var q = dq.value.trim(), lv = dl.value, li = dli.value, pos = dp.value;
      var catRanks = null;
      if (li && li[0] === "c") { var c = (D.cats || []).filter(function (x) { return "c" + x.id === li; })[0]; catRanks = c ? new Set(c.ranks) : null; }
      var qf = norm(q), ql = normLat(q), qe = q.toLowerCase(), num = /^\d+$/.test(enNum(q)) ? +enNum(q) : null;
      results = [];
      D.entries.forEach(function (e) {
        if (lv && String(level(e.n)) !== lv) return;
        if (li && li[0] === "l" && (e.l || []).indexOf(+li.slice(1)) < 0) return;
        if (catRanks && !catRanks.has(e.n)) return;
        if (pos && (e.p || "").split(",").indexOf(pos) < 0) return;
        var s = 0;
        if (!q) s = 1;
        else if (num !== null) s = e.n === num ? 3 : 0;
        else if (isFa(q)) s = e._w === qf ? 3 : e._w.indexOf(qf) === 0 ? 2 : e._w.indexOf(qf) > 0 ? 1 : 0;
        else {
          var gw = e._g.split(/[^a-z']+/);
          s = e._r === ql ? 3 : gw.indexOf(qe) >= 0 ? 3 : e._r.indexOf(ql) === 0 ? 2 : e._g.indexOf(qe) >= 0 ? 1.5 : (ql.length > 2 && e._r.indexOf(ql) > 0) ? 1 : 0;
        }
        if (s > 0) results.push([s, e]);
      });
      results.sort(function (a, b) { return b[0] - a[0] || a[1].n - b[1].n; });
      dictList.innerHTML = ""; shown = 0; more();
      dc.textContent = results.length ? results.length.toLocaleString() + (results.length === 1 ? " word" : " words") : "No words found. Try another spelling, or search in English.";
    }
    function card(e) { return JSON.stringify({ fa: e.w, r: e.r, en: e.g, a: e.a || "", src: "Dictionary" }); }
    function more() {
      results.slice(shown, shown + 60).forEach(function (x) {
        var e = x[1], ctx = h("div", { "class": "de-ctx", hidden: true });
        var mb = h("button", { type: "button", "class": "de-more", text: "In context", onclick: function () {
          if (!ctx.hidden) { ctx.hidden = true; return; }
          ctx.hidden = false; ctx.textContent = "Loading…";
          (conc ? Promise.resolve(conc) : fetch(R + "assets/concordance.json").then(function (r) { return r.json(); }).then(function (c) { conc = c; return c; })).then(function (c) {
            ctx.innerHTML = "";
            var ids = c.w[e._w] || [];
            if (!ids.length) { ctx.append(h("p", { "class": "meta", text: "This word doesn't appear in the lessons and stories yet." })); return; }
            ids.forEach(function (i) {
              var s = c.s[i], u = c.u[s[3]];
              ctx.append(h("div", { "class": "ln ln-ex", "data-a": s[2] || null }, sayBtn(s[2]), h("div", { "class": "ln-b" }, faEl("p", s[0], "fa"), h("p", { "class": "en", text: s[1] }), h("a", { href: R + u[0], text: "From: " + u[1] }))));
            });
          });
        } });
        dictList.append(h("li", { "class": "de" }, h("div", { "class": "de-h" }, h("span", { "class": "de-n", text: e.x ? "–" : "#" + e.n }), sayBtn(e.a, "Listen: " + e.w) || h("span"),
          h("div", { "class": "de-main" }, faEl("span", e.w, "de-w"), " ", h("span", { "class": "tr", text: e.r }), h("br"), h("span", { "class": "de-g", text: e.g }), " ", h("span", { "class": "pos", text: e.p }), " ", mb),
          h("span", { "class": "de-lv", text: LV[level(e.n)] }), h("button", { type: "button", "class": "save", "data-card": card(e), "aria-label": "Save to flashcards", text: "+" })), ctx));
      });
      shown += 60; dm.hidden = shown >= results.length; markSaved();
    }
    var t0 = null;
    dq.addEventListener("input", function () { clearTimeout(t0); t0 = setTimeout(search, 150); });
    [dl, dli, dp].forEach(function (s) { s.addEventListener("change", search); });
    dm.addEventListener("click", more);
  }

  /* ---------------------------------------------------------- flashcards */
  function dayStart(t) { var d = new Date(t); if (d.getHours() < 4) d.setDate(d.getDate() - 1); d.setHours(4, 0, 0, 0); return d.getTime(); }
  function dueIn(t, days) { var d = new Date(dayStart(t)); d.setDate(d.getDate() + days); return d.getTime(); }
  function schedule(c, r, t) {
    var ivl = c.ivl || 0, ease = c.ease || 2.5, lapses = c.lapses || 0, step = c.step || 0, st = c.state || "new", due;
    if (st === "review") {
      if (r === 1) { lapses++; ease = Math.max(1.3, ease - .2); ivl = Math.max(1, Math.round(ivl * .5)); st = "relearning"; step = 0; due = t + 10 * MIN; }
      else if (r === 2) { ivl = Math.max(ivl + 1, Math.round(ivl * 1.2)); ease = Math.max(1.3, ease - .15); due = dueIn(t, ivl); }
      else if (r === 3) { ivl = Math.max(ivl + 1, Math.round(ivl * ease)); due = dueIn(t, ivl); }
      else { ivl = Math.max(ivl + 1, Math.round(ivl * ease * 1.3)); ease += .15; due = dueIn(t, ivl); }
    } else {
      var re = st === "relearning";
      if (r === 1) { step = 0; due = t + MIN; st = re ? "relearning" : "learning"; }
      else if (r === 2) { due = t + (step === 0 ? 6 : 10) * MIN; st = re ? "relearning" : "learning"; }
      else if (r === 3) { if (!re && step === 0) { step = 1; due = t + 10 * MIN; st = "learning"; } else { ivl = re ? Math.max(1, ivl) : 1; step = 0; st = "review"; due = dueIn(t, ivl); } }
      else { ivl = re ? Math.max(1, ivl) + 1 : 4; step = 0; st = "review"; due = dueIn(t, ivl); }
    }
    return { ivl: Math.min(ivl, 3650), ease: Math.round(ease * 100) / 100, reps: (c.reps || 0) + 1, lapses: lapses, step: step, state: st, due: due, last: t };
  }
  function label(c, r, t) { var p = schedule(c, r, t); if (p.state === "review") return p.ivl < 60 ? p.ivl + "d" : Math.round(p.ivl / 30) + "mo"; var m = Math.round((p.due - t) / MIN); return m < 60 ? m + "m" : Math.round(m / 60) + "h"; }
  var fc = $("[data-fc]");
  if (fc) {
    var stats = $("[data-fc-stats]"), cardBox = $("[data-fc-card]"), front = $("[data-fc-front]"), listBox = $("[data-fc-list]");
    front.value = store.get("fcfront", "fa");
    front.addEventListener("change", function () { store.set("fcfront", front.value); });
    var nextCard = function (t, avoid) {
      var all = Object.values(deck()), learn = function (c) { return c.state === "learning" || c.state === "relearning"; };
      var pick = function (l, k) { return l.sort(function (a, b) { return a[k] - b[k]; })[0]; };
      return pick(all.filter(function (c) { return learn(c) && c.due <= t; }), "due") || pick(all.filter(function (c) { return c.state === "review" && c.due <= t; }), "due")
        || pick(all.filter(function (c) { return (c.state || "new") === "new"; }), "added") || pick(all.filter(function (c) { return learn(c) && c.id !== avoid && c.due <= t + 20 * MIN; }), "due") || null;
    };
    var refresh = function () {
      var all = Object.values(deck()), t = Date.now();
      var n = all.filter(function (c) { return (c.state || "new") === "new"; }).length, l = all.filter(function (c) { return (c.state === "learning" || c.state === "relearning"); }).length,
        d = all.filter(function (c) { return c.state === "review" && c.due <= t; }).length;
      stats.textContent = all.length ? all.length + " saved words: " + n + " new, " + l + " learning, " + d + " due for review." : "No saved words yet. Tap + next to any word in a lesson, story or the dictionary, or add a set below.";
      listBox.innerHTML = "";
      if (all.length) {
        var tb = h("tbody");
        all.sort(function (a, b) { return b.added - a.added; }).forEach(function (c) {
          tb.append(h("tr", null, h("td", { lang: "fa", dir: "rtl", text: c.fa }), h("td", { "class": "tr", text: c.r }), h("td", { text: c.en }), h("td", { "class": "meta", text: c.state === "review" ? "every " + c.ivl + "d" : c.state || "new" }),
            h("td", null, h("button", { type: "button", "class": "del", text: "remove", "aria-label": "Remove " + c.en, onclick: function () { var dd = deck(); delete dd[c.id]; saveDeck(dd); refresh(); } }))));
        });
        listBox.append(h("div", { "class": "tbl-wrap" }, h("table", null, tb)));
      }
    };
    var review = function (avoid) {
      var t = Date.now(), c = nextCard(t, avoid);
      cardBox.hidden = false; cardBox.innerHTML = "";
      if (!c) { cardBox.append(h("p", { text: "All done for now. Come back later – or add more words." })); refresh(); return; }
      var fa1 = front.value !== "en";
      var back = h("div", { "class": "fc-back", hidden: true }, fa1 ? null : faEl("p", c.fa, "fa"), h("p", { "class": "tr", text: c.r }), fa1 ? h("p", { text: c.en }) : null, c.src ? h("p", { "class": "meta", text: "From: " + c.src }) : null);
      var grades = h("div", { "class": "fc-grades", hidden: true });
      [[1, "Again"], [2, "Hard"], [3, "Good"], [4, "Easy"]].forEach(function (g) {
        grades.append(h("button", { type: "button", "class": "g" + g[0], onclick: function () { var dd = deck(); dd[c.id] = Object.assign(dd[c.id] || c, schedule(c, g[0], Date.now())); saveDeck(dd); refresh(); review(c.id); } }, g[1], h("small", { text: label(c, g[0], t) })));
      });
      var showB = h("button", { type: "button", "class": "btn", text: "Show answer", onclick: function () { back.hidden = false; grades.hidden = false; showB.remove(); if (c.a) play(c.a); } });
      cardBox.append(fa1 ? faEl("p", c.fa, "fc-front") : h("p", { "class": "fc-front", text: c.en }), fa1 ? sayBtn(c.a) : null, back, showB, grades);
      showB.focus();
    };
    $("[data-fc-start]").addEventListener("click", function () { review(null); });
    var sel = $("[data-fc-deck]"), DK = {};
    fetch(R + "assets/decks.json").then(function (r) { return r.json(); }).then(function (d) {
      DK = d;
      var groups = { "Lessons": [], "Stories": [], "Articles": [], "News": [], "Phrasebook": [] };
      Object.keys(d).forEach(function (k) {
        var g = k.indexOf("story-") === 0 ? "Stories" : k.indexOf("article-") === 0 ? "Articles" : k.indexOf("news-") === 0 ? "News" : k.indexOf("phrasebook-") === 0 ? "Phrasebook" : "Lessons";
        groups[g].push(h("option", { value: k, text: d[k].t + " (" + d[k].w.length + ")" }));
      });
      Object.keys(groups).forEach(function (g) { if (groups[g].length) sel.append(h("optgroup", { label: g }, groups[g])); });
    });
    $("[data-fc-add]").addEventListener("click", function () {
      var k = sel.value; if (!DK[k]) return;
      var dd = deck(); DK[k].w.forEach(function (w) { addCard({ fa: w[0], r: w[1], en: w[2], a: w[3], src: DK[k].t }, dd); }); saveDeck(dd); refresh();
    });
    $("[data-fc-export]").addEventListener("click", function () {
      var blob = new Blob([JSON.stringify({ app: "learn-farsi", v: 1, deck: deck() }, null, 1)], { type: "application/json" });
      var a = h("a", { href: URL.createObjectURL(blob), download: "learn-farsi-flashcards.json" }); document.body.append(a); a.click(); a.remove();
    });
    $("[data-fc-import]").addEventListener("change", function (e) {
      var f = e.target.files[0]; if (!f) return;
      f.text().then(function (t) { var j = JSON.parse(t), dd = deck(); Object.keys(j.deck || {}).forEach(function (k) { if (!dd[k] || (j.deck[k].last || 0) > (dd[k].last || 0)) dd[k] = j.deck[k]; }); saveDeck(dd); refresh(); })
        .catch(function () { stats.textContent = "That file isn't a Learn Farsi backup."; });
    });
    $("[data-fc-csv]").addEventListener("click", function () {
      var rows = Object.values(deck()).map(function (c) { return [c.fa, c.r + " – " + c.en, c.src].map(function (x) { return String(x || "").replace(/\t|\n/g, " "); }).join("\t"); });
      var blob = new Blob(["#separator:tab\n#columns:Persian\tMeaning\tSource\n" + rows.join("\n")], { type: "text/tab-separated-values" });
      var a = h("a", { href: URL.createObjectURL(blob), download: "learn-farsi-anki.txt" }); document.body.append(a); a.click(); a.remove();
    });
    refresh();
  }

  /* ---------------------------------------------------------- word of the day */
  var wb = $("[data-wotd]");
  if (wb) fetch(R + "assets/wotd.json").then(function (r) { return r.json(); }).then(function (list) {
    if (!list.length) return;
    var day = Math.floor((Date.now() - new Date().getTimezoneOffset() * 60000) / DAY), w = list[day % list.length];
    wb.innerHTML = "";
    wb.append(h("h2", { text: "Word of the day" }),
      h("p", { "class": "wotd-w" }, sayBtn(w[3], "Listen: " + w[0]), faEl("span", w[0], "wotd-fa"), " ", h("span", { "class": "tr", text: w[1] }), " – " + w[2],
        h("button", { type: "button", "class": "save", "data-card": JSON.stringify({ fa: w[0], r: w[1], en: w[2], a: w[3], src: "Word of the day" }), "aria-label": "Save to flashcards", text: "+" })),
      h("div", { "class": "ln ln-ex", "data-a": w[6] || null }, sayBtn(w[6]), h("div", { "class": "ln-b" }, faEl("p", w[4], "fa"), h("p", { "class": "en", text: w[5] }), h("a", { href: R + w[7], text: "From: " + w[8] }))));
    wb.hidden = false; markSaved();
  });

  /* ---------------------------------------------------------- search */
  var sOut = $("[data-search-out]");
  if (sOut) {
    var sq = $("[data-search-q]"), q0 = new URLSearchParams(location.search).get("q") || "";
    sq.value = q0;
    var TYPES = [["lesson", "Lessons"], ["story", "Stories"], ["history", "History"], ["places", "Places"], ["food", "Food"], ["festivals", "Festivals"], ["arts", "Arts"], ["people", "People"], ["language", "Language"], ["life", "Everyday life"],
      ["poem", "Poems"], ["news", "News"], ["phrase", "Phrases"], ["idiom", "Proverbs and idioms"], ["verb", "Verbs"], ["word", "Words in lessons and stories"]];
    fetch(R + "assets/search.json").then(function (r) { return r.json(); }).then(function (idx) {
      idx.forEach(function (e) { e._k = ((e.ti || "") + " " + (e.s || "") + " " + (e.k || "")).toLowerCase(); e._f = norm(e.fa); e._r = normLat(e.r); });
      var run = function () {
        var q = sq.value.trim(); sOut.innerHTML = "";
        if (!q) return;
        var qf = norm(q), ql = normLat(q), qe = q.toLowerCase(), fa = isFa(q);
        var hits = idx.filter(function (e) { return fa ? e._f.indexOf(qf) >= 0 : (e._k.indexOf(qe) >= 0 || (ql.length > 1 && e._r.indexOf(ql) >= 0)); });
        if (!hits.length) sOut.append(h("p", { text: "Nothing found for “" + q + "”." }));
        TYPES.forEach(function (t) {
          var hs = hits.filter(function (e) { return e.t === t[0]; });
          if (!hs.length) return;
          var ul = h("ul", { "class": "sr" });
          hs.slice(0, t[0] === "word" ? 40 : 25).forEach(function (e) { ul.append(h("li", null, h("a", { href: R + e.u }, h("span", { text: e.ti }), faEl("span", e.fa || "", "s-fa"), h("span", { "class": "s-s", text: [e.r, e.s].filter(Boolean).join(" – ") })))); });
          sOut.append(h("section", { "class": "sr-group" }, h("h2", { text: t[1] + " (" + hs.length + ")" }), ul));
        });
        sOut.append(h("p", null, h("a", { href: R + "dictionary/index.html?q=" + encodeURIComponent(q), text: "Look up “" + q + "” in the 5,000-word dictionary" })));
      };
      sq.addEventListener("input", function () { clearTimeout(sq._t); sq._t = setTimeout(run, 200); });
      run();
    });
  }

  /* ---------------------------------------------------------- print (A4): exercises become a worksheet, answers go on the last page */
  var LET = "abcdefghijklmnopqrstuvwxyz";
  function seededShuffle(arr, seed) {
    var a = arr.slice(), s = seed;
    for (var i = a.length - 1; i > 0; i--) { s = (s * 9301 + 49297) % 233280; var j = Math.floor(s / 233280 * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function optLine(opts) {
    return h("div", { "class": "exp-opts" }, (opts || []).map(function (o, i) {
      return h("span", null, LET[i] + ") ", isFa(o) ? faEl("bdi", o) : o);
    }));
  }
  function buildPrint() {
    if (document.body.getAttribute("data-print-ready")) return;
    document.body.setAttribute("data-print-ready", "1");
    var keys = [], n = 0;
    $$("main .ex").forEach(function (box) {
      var el = $(".ex-data", box), d;
      if (!el) return;
      try { d = JSON.parse(el.textContent); } catch (e) { return; }
      n++;
      var items = d.items || [], list = h("ol", { "class": "exp-list" }), ans = [], title = "Exercise " + n;
      if (d.kind === "match") {
        var order = seededShuffle(items.map(function (x, i) { return i; }), n * 31 + items.length);
        var tb = h("tbody");
        items.forEach(function (it, i) {
          var right = items[order[i]];
          tb.append(h("tr", null, h("td", { text: (i + 1) + "." }), faEl("td", it.fa, "fa"), h("td", { text: "____" }),
            h("td", { text: LET[i] + ") " + (right.en || "") })));
          ans.push((i + 1) + " " + LET[order.indexOf(i)]);
        });
        box.append(h("div", { "class": "ex-print" }, h("p", { "class": "exp-n", text: title + " – match the Persian with the English." }), h("table", { "class": "exp-match" }, tb)));
      } else {
        var how = { mcq: "Choose the right answer.", listen: "Read the sentence and choose its meaning.", fill: "Write the missing word.",
          translate: "Write in Persian.", order: "Put the words in the right order." }[d.kind] || "";
        items.forEach(function (it, i) {
          var li = h("li");
          if (d.kind === "mcq") { li.append(h("div", { html: it.q }), optLine(it.o)); ans.push((i + 1) + " " + LET[it.ans]); }
          else if (d.kind === "listen") { li.append(faEl("p", it.fa, "fa"), optLine(it.o)); ans.push((i + 1) + " " + LET[it.ans]); }
          else if (d.kind === "fill") {
            li.append(faEl("p", (it.fa || "").replace("___", " ……………… "), "fa"), h("p", { "class": "meta", text: it.en + (it.hint ? " (hint: " + it.hint + ")" : "") }));
            ans.push([(i + 1) + " ", faEl("bdi", it.ans)]);
          } else if (d.kind === "translate") { li.append(h("p", { text: it.en }), h("div", { "class": "exp-line" })); ans.push([(i + 1) + " ", faEl("bdi", it.fa)]); }
          else if (d.kind === "order") {
            var words = (it.fa || "").replace(/[.؟!،]+$/, "").split(" ");
            li.append(faEl("p", seededShuffle(words, n * 17 + i + 3).join("  /  "), "fa exp-words"), h("p", { "class": "meta", text: it.en }), h("div", { "class": "exp-line" }));
            ans.push([(i + 1) + " ", faEl("bdi", it.fa)]);
          } else { li.append(faEl("p", it.fa, "fa"), h("p", { text: it.en })); }
          list.append(li);
        });
        box.append(h("div", { "class": "ex-print" }, h("p", { "class": "exp-n", text: title + (how ? " – " + how : "") }), list));
      }
      if (ans.length) keys.push([title, ans]);
    });
    var host = $("main article") || $("main .narrow-in") || $("main .narrow") || $("main");
    if (keys.length) {
      var sec = h("section", { "class": "print-key" }, h("h2", { text: "Answer key" }));
      keys.forEach(function (k) {
        if (Array.isArray(k[1][0])) {          /* Persian answers: one per line */
          sec.append(h("p", null, h("strong", { text: k[0] })),
            h("ol", { "class": "key-list" }, k[1].map(function (a) { return h("li", null, a[1]); })));
        } else {
          sec.append(h("p", null, h("strong", { text: k[0] + ": " }), k[1].join("  ·  ")));
        }
      });
      host.append(sec);
    }
    host.append(h("p", { "class": "print-foot", text: document.title + " – " + location.href.split("#")[0] + " – free audio for every sentence at this address." }));
  }
  var reopened = [];
  window.addEventListener("beforeprint", function () {
    buildPrint();
    reopened = $$("main details:not([open])");
    reopened.forEach(function (d) { d.setAttribute("open", ""); });
  });
  window.addEventListener("afterprint", function () { reopened.forEach(function (d) { d.removeAttribute("open"); }); reopened = []; });
  $$("[data-print]").forEach(function (btn) { btn.addEventListener("click", function () { buildPrint(); window.print(); }); });

  /* ---------------------------------------------------------- offline */
  var canCache = "serviceWorker" in navigator && "caches" in window && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1");
  if (canCache) {
    window.addEventListener("load", function () { navigator.serviceWorker.register(R + "sw.js").catch(function () {}); });
    var pageUrl = location.href.split("#")[0].split("?")[0];
    $$("[data-offline]").forEach(function (btn) {
      var ids = [];
      $$("main [data-a]").forEach(function (el) { var a = el.getAttribute("data-a"); if (a && ids.indexOf(a) < 0) ids.push(a); });
      btn.hidden = false;
      caches.open("lf-saved").then(function (c) { return c.match(pageUrl); }).then(function (hit) { if (hit) { btn.textContent = "Saved offline ✓"; btn.classList.add("on"); } }).catch(function () {});
      btn.addEventListener("click", function () {
        if (btn.disabled) return;
        btn.disabled = true;
        var urls = ids.map(function (a) { return new URL(R + "data/audio/fa/" + a + ".mp3", location.href).href; }), i = 0, done = 0;
        caches.open("lf-audio").then(function (c) {
          function next() {
            if (i >= urls.length) return Promise.resolve();
            var u = urls[i++];
            return c.match(u).then(function (hit) { return hit || fetch(u).then(function (r) { if (r.ok) return c.put(u, r); }); })
              .catch(function () {}).then(function () { done++; btn.textContent = "Saving " + done + " / " + urls.length; return next(); });
          }
          return Promise.all([next(), next(), next(), next(), next(), next()]);
        }).then(function () {
          return Promise.all([caches.open("lf-pages").then(function (c) { return c.add(pageUrl); }),
            caches.open("lf-saved").then(function (c) { return c.put(pageUrl, new Response(document.title.replace(/ – Learn Farsi$/, ""), { headers: { "Content-Type": "text/plain; charset=utf-8" } })); })]);
        }).then(function () { btn.textContent = "Saved offline ✓"; btn.classList.add("on"); btn.disabled = false; })
          .catch(function () { btn.textContent = "Couldn't save – try again"; btn.disabled = false; });
      });
    });
    var offList = $("[data-offline-list]");
    if (offList) caches.open("lf-saved").then(function (c) {
      return c.keys().then(function (keys) { return Promise.all(keys.map(function (k) { return c.match(k).then(function (r) { return r.text(); }).then(function (t) { return [k.url, t]; }); })); });
    }).then(function (rows) {
      offList.innerHTML = "";
      if (!rows.length) { offList.append(h("li", { text: "Nothing saved yet. Pages you have opened before may still work – try the back button." })); return; }
      rows.sort(function (a, b) { return a[1] < b[1] ? -1 : 1; }).forEach(function (r) { offList.append(h("li", null, h("a", { href: r[0], text: r[1] }))); });
    }).catch(function () {});
  }
})();
