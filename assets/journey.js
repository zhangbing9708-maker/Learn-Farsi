/* Learn Farsi – "My journey": progress that feels like progress.
   - a caravan travels the old road from Tabriz to Shiraz as levels are finished;
   - every finished lesson weaves one medallion into the learner's own Persian carpet;
   - streaks count towards a chelle (چله), the traditional forty days of devoted practice;
   - badges with Persian names; a celebration with a word of praise (and its audio) and a fāl-e Hāfez when a lesson is done;
   - "what you can do now" statements, words known and how much of everyday text they cover, and a printable certificate.
   Everything is kept in this browser (localStorage); nothing is sent anywhere. */
(function () {
  "use strict";
  var LF = window.LF;
  if (!LF) return;
  var h = LF.h, $ = LF.$, $$ = LF.$$, store = LF.store, R = LF.R, faEl = LF.faEl;
  var LEVEL_COLOURS = { script: "#13a3ab", a1: "#1f3a8a", a2: "#08727a", b1: "#d9971a", b2: "#b3243c", c1: "#6b3fa0" };

  /* ---------------------------------------------------------------- days and streaks */
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function dayKey(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function touch() {
    var d = new Date(), days = store.get("days", {}), k = dayKey(d);
    days[k] = (days[k] || 0) + 1;
    store.set("days", days);
    var flags = store.get("jflags", {}), m = d.getMonth() + 1, dd = d.getDate();
    if (d.getHours() < 4) flags.night = 1;
    if ((m === 12 && (dd === 20 || dd === 21 || dd === 22))) flags.yalda = 1;
    if ((m === 3 && dd >= 19) || (m === 4 && dd <= 2)) flags.nowruz = 1;
    store.set("jflags", flags);
  }
  document.addEventListener("click", function (e) {
    if (e.target.closest(".say, .ex-opt, .ex-small, [data-done], [data-read], [data-fc-start], .fc-card button, .ab-btn, [data-vrec], [data-playall]")) touch();
  }, true);
  function streak() {
    var days = store.get("days", {}), d = new Date(), n = 0;
    if (!days[dayKey(d)]) d.setDate(d.getDate() - 1);       // today not studied yet: the streak is still alive until midnight
    while (days[dayKey(d)]) { n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function longest() {
    var keys = Object.keys(store.get("days", {})).sort(), best = 0, run = 0, prev = null;
    keys.forEach(function (k) {
      var t = new Date(k + "T12:00:00");
      run = prev && Math.round((t - prev) / 86400000) === 1 ? run + 1 : 1;
      best = Math.max(best, run); prev = t;
    });
    return best;
  }

  /* ---------------------------------------------------------------- the data built with the site */
  var jp = null;
  function J() { if (!jp) jp = fetch(R + "assets/journey.json").then(function (r) { return r.json(); }); return jp; }

  function stats(j) {
    var done = store.get("done", {}), read = store.get("read", {}), deck = store.get("deck", {});
    var st = { done: 0, levels: {}, words: {}, top1000: 0, coverage: 0, stories: 0, poems: 0, articles: 0,
      perfect: store.get("perfect", 0) || 0, cards: Object.keys(deck).length, streak: streak(), longest: longest(),
      daysActive: Object.keys(store.get("days", {})).length, flags: store.get("jflags", {}), recordings: 0, total: 0 };
    j.levels.forEach(function (lv) {
      var n = lv.lessons.filter(function (l) { return done[l]; }).length;
      st.levels[lv.id] = { done: n, of: lv.lessons.length };
      st.done += n; st.total += lv.lessons.length;
      lv.lessons.forEach(function (l) { if (done[l] && j.lessons[l]) j.lessons[l].w.forEach(function (w) { st.words[w] = 1; }); });
    });
    Object.keys(deck).forEach(function (k) { if (deck[k].fa) st.words[deck[k].fa] = 1; });
    var cov = 0;
    Object.keys(st.words).forEach(function (w) {
      var f = j.freq[w];
      if (f) { if (f[0] <= 1000) st.top1000++; cov += f[1]; }
    });
    st.nWords = Object.keys(st.words).length;
    st.coverage = j.total ? Math.round(100 * cov / j.total) : 0;
    Object.keys(read).forEach(function (k) {
      if (k.indexOf("story:") === 0) st.stories++; else if (k.indexOf("poem:") === 0) st.poems++; else if (k.indexOf("article:") === 0) st.articles++;
    });
    var vi = store.get("voice:index:google", {}) || {}, vd = store.get("voice:index:device", {}) || {};
    st.recordings = Object.keys(vi).length + Object.keys(vd).length;
    st.nStories = Object.keys(j.stories).length; st.nPoems = Object.keys(j.poems).length;
    return st;
  }

  /* ---------------------------------------------------------------- badges */
  function lvDone(st, id) { var l = st.levels[id]; return l && l.of && l.done === l.of; }
  function badges(j) {
    var list = [
      ["first", "نخستین گام", "First step", "Finish your first lesson", function (s) { return s.done >= 1; }],
      ["words100", "صد واژه", "A hundred words", "Know 100 words", function (s) { return s.nWords >= 100; }],
      ["words500", "پانصد واژه", "Five hundred words", "Know 500 words", function (s) { return s.nWords >= 500; }],
      ["words1000", "هزار واژه", "A thousand words", "Know 1,000 words", function (s) { return s.nWords >= 1000; }],
      ["top500", "واژه‌های پرکاربرد", "The words that matter", "Know 500 of the 1,000 most common words", function (s) { return s.top1000 >= 500; }],
      ["streak3", "سه روز پیاپی", "Three days running", "Study three days in a row", function (s) { return s.longest >= 3; }],
      ["streak7", "یک هفته", "A whole week", "Study seven days in a row", function (s) { return s.longest >= 7; }],
      ["chelle", "چله", "Chelle – forty days", "Forty days in a row: the traditional chelle of devoted practice", function (s) { return s.longest >= 40; }],
      ["streak100", "صد روز", "A hundred days", "Study a hundred days in a row", function (s) { return s.longest >= 100; }],
      ["story1", "نخستین داستان", "First story", "Read a whole story", function (s) { return s.stories >= 1; }],
      ["story10", "کتاب‌خوان", "Bookworm", "Read ten stories", function (s) { return s.stories >= 10; }],
      ["story25", "قصه‌گو", "Storyteller", "Read twenty-five stories", function (s) { return s.stories >= 25; }],
      ["storyall", "هزار و یک شب", "A Thousand and One Nights", "Read every story on the site", function (s) { return s.nStories && s.stories >= s.nStories; }],
      ["poem1", "دوستدار شعر", "Lover of poetry", "Read a poem to the end", function (s) { return s.poems >= 1; }],
      ["poem5", "دیوان‌خوان", "Reader of the Divan", "Read five poems", function (s) { return s.poems >= 5; }],
      ["poemall", "سخن‌شناس", "Connoisseur", "Read every poem on the site", function (s) { return s.nPoems && s.poems >= s.nPoems; }],
      ["travel10", "جهانگرد", "World traveller", "Read ten culture articles", function (s) { return s.articles >= 10; }],
      ["perfect10", "بی‌غلط", "Flawless", "Get every answer right in ten exercises", function (s) { return s.perfect >= 10; }],
      ["perfect50", "تیزهوش", "Sharp mind", "Fifty perfect exercises", function (s) { return s.perfect >= 50; }],
      ["cards50", "دفترچه‌ی واژه", "Word notebook", "Save fifty words to your flashcards", function (s) { return s.cards >= 50; }],
      ["voice1", "صدای دوست", "A friend's voice", "Record a friend reading Persian", function (s) { return s.recordings >= 1; }],
      ["yalda", "شب یلدا", "Yalda night", "Study on Yalda, the longest night of the year", function (s) { return !!s.flags.yalda; }],
      ["nowruz", "نوروز", "Nowruz", "Study during the Persian New Year", function (s) { return !!s.flags.nowruz; }],
      ["night", "شب‌زنده‌دار", "Night owl", "Study after midnight", function (s) { return !!s.flags.night; }]
    ];
    j.levels.forEach(function (lv, i) {
      list.splice(1 + i, 0, ["lv-" + lv.id, lv.cityFa, "Reached " + lv.city, "Finish " + lv.name, function (s) { return lvDone(s, lv.id); }, LEVEL_COLOURS[lv.id]]);
    });
    return list;
  }
  function checkBadges(j, st) {
    var got = store.get("badges", {}), fresh = [];
    badges(j).forEach(function (b) { if (!got[b[0]] && b[4](st)) { got[b[0]] = Date.now(); fresh.push(b); } });
    if (fresh.length) store.set("badges", got);
    return fresh;
  }
  var STAR = "M50 4l13 18 22-4-4 22 18 13-18 13 4 22-22-4-13 18-13-18-22 4 4-22L4 53l18-13-4-22 22 4z";
  function medal(b, on) {
    var c = on ? (b[5] || "#d9971a") : "#c9cfdc";
    var svg = '<svg viewBox="0 0 100 106" aria-hidden="true"><path d="' + STAR + '" fill="' + c + '"/><path d="' + STAR + '" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2" transform="translate(50 53) scale(.78) translate(-50 -53)"/>'
      + '<circle cx="50" cy="53" r="17" fill="#fff" fill-opacity="' + (on ? ".92" : ".6") + '"/></svg>';
    return h("div", { "class": "medal" + (on ? " on" : ""), title: b[3] }, h("span", { "class": "medal-i", html: svg }),
      faEl("span", b[1], "medal-fa"), h("span", { "class": "medal-en", text: b[2] }), h("span", { "class": "medal-d", text: b[3] }));
  }

  /* ---------------------------------------------------------------- celebrations */
  function rand(a) { return a[Math.floor(Math.random() * a.length)]; }
  function petals(n) {
    var box = h("div", { "class": "petals", "aria-hidden": "true" });
    for (var i = 0; i < (n || 26); i++) {
      var p = h("span", { "class": "petal" });
      p.style.left = Math.random() * 100 + "%";
      p.style.animationDelay = (Math.random() * 1.2).toFixed(2) + "s";
      p.style.animationDuration = (2.6 + Math.random() * 2.2).toFixed(2) + "s";
      p.style.setProperty("--drift", (Math.random() * 160 - 80).toFixed(0) + "px");
      p.style.setProperty("--hue", ["#e8506b", "#f08aa0", "#d9971a", "#f4c27a", "#c2304f"][i % 5]);
      box.append(p);
    }
    document.body.append(box);
    setTimeout(function () { box.remove(); }, 6500);
  }
  function playA(a) { if (a) { try { LF.play(a); } catch (e) { /* ignore */ } } }
  var dlg = null;
  function modal(nodes) {
    if (!dlg) { dlg = h("dialog", { "class": "jcele" }); document.body.append(dlg); }
    dlg.innerHTML = "";
    nodes.forEach(function (n) { if (n) dlg.append(n); });
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
    dlg.scrollTop = 0;
  }
  function closeBtn(label) { return h("button", { type: "button", "class": "btn-quiet", text: label || "Close", onclick: function () { try { dlg.close(); } catch (e) { dlg.removeAttribute("open"); } } }); }

  function celebrateLesson(id) {
    J().then(function (j) {
      var L = j.lessons[id]; if (!L) return;
      var st = stats(j), fresh = checkBadges(j, st), lv = null, li = 0;
      j.levels.forEach(function (x, i) { if (x.id === L.lv) { lv = x; li = i; } });
      var praise = rand(j.praise.filter(function (p) { return p[3]; }).length ? j.praise.filter(function (p) { return p[3]; }) : j.praise);
      var lvs = st.levels[L.lv], next = null;
      var order = []; j.levels.forEach(function (x) { order = order.concat(x.lessons); });
      var done = store.get("done", {});
      for (var k = order.indexOf(id) + 1; k < order.length; k++) if (!done[order[k]]) { next = order[k]; break; }
      var fal = j.fal.length ? rand(j.fal) : null;
      var levelDone = lvs.done === lvs.of;
      petals(levelDone ? 60 : 28);
      modal([
        faEl("p", praise ? praise[0] : "آفرین!", "jc-fa"),
        h("p", { "class": "jc-r", text: praise ? praise[1] + " – " + praise[2] : "" }),
        h("h2", { text: levelDone ? "You have reached " + lv.city + "!" : "Lesson " + L.n + " done" }),
        h("p", { "class": "jc-lv", text: levelDone ? "You have finished " + lv.name + " – every lesson. Your caravan rests in " + lv.city + " tonight." : lvs.done + " of " + lvs.of + " lessons in " + lv.name + " – your caravan is on its way to " + lv.city + "." }),
        h("div", { "class": "bar jc-bar" }, h("span", { style: "width:" + Math.round(100 * lvs.done / lvs.of) + "%" })),
        L.g.length ? h("div", { "class": "jc-can" }, h("p", { "class": "jc-h", text: "Now you can" }), h("ul", null, L.g.map(function (g) { return h("li", { text: g }); }))) : null,
        h("p", { "class": "jc-words", html: "<strong>" + st.nWords + "</strong> words learnt" + (st.top1000 ? ", including <strong>" + st.top1000 + "</strong> of the 1,000 most common – about <strong>" + st.coverage + "%</strong> of the words in everyday Persian text." : ".") }),
        st.streak > 1 ? h("p", { "class": "jc-streak", text: "🔥 " + st.streak + " days in a row" + (st.streak < 40 ? " – " + (40 - st.streak) + " more for a chelle." : " – a chelle!") }) : null,
        fresh.length ? h("div", { "class": "jc-badges" }, h("p", { "class": "jc-h", text: fresh.length === 1 ? "New badge" : "New badges" }), h("div", { "class": "medals" }, fresh.slice(0, 3).map(function (b) { return medal(b, true); })),
          fresh.length > 3 ? h("p", { "class": "meta", text: "and " + (fresh.length - 3) + " more on your journey page" }) : null) : null,
        fal ? h("div", { "class": "jc-fal" }, h("p", { "class": "jc-h", text: fal[4] === "Hafez" ? "Your fāl-e Hāfez for today" : "A verse for today" }), faEl("p", fal[0].replace(" / ", " – "), "jc-fal-fa"), h("p", { text: fal[1] + " – " + fal[4] }),
          h("p", null, h("button", { type: "button", "class": "btn-quiet", text: "▶ Listen", onclick: function () { playA(fal[2]); } }), " ", h("a", { href: R + fal[3], text: "Read the poem" }))) : null,
        h("div", { "class": "jc-actions" }, next ? h("a", { "class": "btn", href: R + j.lessons[next].u, text: "Next: " + j.lessons[next].t + " →" }) : null,
          h("a", { "class": "btn-quiet", href: R + "journey/index.html", text: "See my journey" }), closeBtn("Stay here"))
      ]);
      if (praise && praise[3]) setTimeout(function () { playA(praise[3]); }, 350);
    });
  }
  document.addEventListener("lf:done", function (e) { touch(); celebrateLesson(e.detail.id); });

  function toast(html) {
    var t = h("div", { "class": "jtoast", html: html });
    document.body.append(t);
    setTimeout(function () { t.classList.add("show"); }, 20);
    setTimeout(function () { t.classList.remove("show"); setTimeout(function () { t.remove(); }, 400); }, 3800);
  }
  document.addEventListener("lf:score", function (e) {
    var d = e.detail;
    if (!d || d.right !== d.total || !d.total) return;
    store.set("perfect", (store.get("perfect", 0) || 0) + 1);
    J().then(function (j) {
      var p = rand(j.praise.slice(0, 5));
      toast('<span lang="fa" dir="rtl" class="jt-fa">' + p[0] + "</span> " + d.right + " out of " + d.total + " – " + p[2]);
      var fresh = checkBadges(j, stats(j));
      if (fresh.length) setTimeout(function () { toast("New badge: <strong>" + fresh[0][2] + "</strong> " + '<span lang="fa" dir="rtl">' + fresh[0][1] + "</span>"); petals(18); }, 1600);
    });
  });

  /* "I've read this" at the end of stories, poems and articles */
  $$("[data-read]").forEach(function (b) {
    var k = b.getAttribute("data-read"), read = store.get("read", {});
    function show() { var on = !!store.get("read", {})[k]; b.classList.toggle("is-done", on); b.textContent = on ? "Read ✓ – tap to undo" : "I've read this"; }
    b.addEventListener("click", function () {
      var r = store.get("read", {}), now = !r[k];
      if (now) r[k] = Date.now(); else delete r[k];
      store.set("read", r); show();
      if (!now) return;
      touch();
      J().then(function (j) {
        var st = stats(j), fresh = checkBadges(j, st);
        var kind = k.split(":")[0];
        var line = kind === "story" ? st.stories + (st.stories === 1 ? " story" : " stories") + " read in Persian." : kind === "poem" ? st.poems + (st.poems === 1 ? " poem" : " poems") + " read." : st.articles + (st.articles === 1 ? " article" : " articles") + " read.";
        petals(fresh.length ? 40 : 16);
        toast('<span lang="fa" dir="rtl" class="jt-fa">آفرین!</span> ' + line + (fresh.length ? " New badge: <strong>" + fresh[0][2] + "</strong>" : ""));
      });
    });
    void read; show();
  });

  /* ---------------------------------------------------------------- the journey page */
  function routeSvg(j, st) {
    var n = j.levels.length, W = 760, H = 190, pts = [];
    for (var i = 0; i < n; i++) pts.push([60 + i * (W - 120) / (n - 1), 95 + (i % 2 ? -38 : 38)]);
    var d = "M" + pts.map(function (p) { return p[0] + " " + p[1]; }).join(" L");
    var reached = 0;   // position of the caravan: index + fraction of the next level done
    for (i = 0; i < n; i++) {
      var l = st.levels[j.levels[i].id];
      if (l.done === l.of && l.of) { reached = i; continue; }     // arrived at this level's city
      reached = i - 1 + (l.of ? l.done / l.of : 0); break;      // on the road towards it
    }
    reached = Math.max(0, Math.min(reached, n - 1));
    var a = Math.floor(reached), f = reached - a, b = Math.min(a + 1, n - 1);
    var cx = pts[a][0] + (pts[b][0] - pts[a][0]) * f, cy = pts[a][1] + (pts[b][1] - pts[a][1]) * f;
    var s = '<svg class="route" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Caravan route from Tabriz to Shiraz">'
      + '<path d="' + d + '" fill="none" stroke="var(--line)" stroke-width="5" stroke-dasharray="2 10" stroke-linecap="round"/>';
    var dd = "M" + pts[0][0] + " " + pts[0][1];
    for (i = 1; i <= a; i++) dd += " L" + pts[i][0] + " " + pts[i][1];
    dd += " L" + cx + " " + cy;
    s += '<path d="' + dd + '" fill="none" stroke="var(--saffron)" stroke-width="5" stroke-linecap="round"/>';
    j.levels.forEach(function (lv, k) {
      var l = st.levels[lv.id], full = l.of && l.done === l.of, p = pts[k], up = k % 2 === 1;
      s += '<g><circle cx="' + p[0] + '" cy="' + p[1] + '" r="13" fill="' + (full ? LEVEL_COLOURS[lv.id] : "var(--paper)") + '" stroke="' + LEVEL_COLOURS[lv.id] + '" stroke-width="3"/>'
        + (full ? '<path d="M' + (p[0] - 6) + " " + p[1] + " l4 4 l8 -9" + '" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>' : "")
        + '<text x="' + p[0] + '" y="' + (up ? p[1] - 24 : p[1] + 36) + '" text-anchor="middle" class="rt-fa">' + lv.cityFa + "</text>"
        + '<text x="' + p[0] + '" y="' + (up ? p[1] - 46 : p[1] + 54) + '" text-anchor="middle" class="rt-en">' + lv.city + " · " + lv.name.replace(/ \(.*\)/, "") + "</text></g>";
    });
    s += '<text x="' + cx + '" y="' + (cy + 9) + '" text-anchor="middle" class="rt-camel">🐪</text></svg>';
    return s;
  }
  function carpetSvg(j) {
    var done = store.get("done", {}), order = [];
    j.levels.forEach(function (lv) { lv.lessons.forEach(function (l) { order.push([l, lv.id]); }); });
    var cols = 8, rows = Math.ceil(order.length / cols), cell = 44, pad = 34, W = cols * cell + pad * 2, H = rows * cell + pad * 2;
    var s = '<svg class="carpet" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Your carpet: one medallion for each finished lesson">'
      + '<defs><pattern id="jb" width="16" height="16" patternUnits="userSpaceOnUse"><rect width="16" height="16" fill="#7a1f2e"/><path d="M8 1l7 7-7 7-7-7z" fill="#d9971a"/><circle cx="8" cy="8" r="2" fill="#f6f8fc"/></pattern></defs>'
      + '<rect x="0" y="0" width="' + W + '" height="' + H + '" rx="6" fill="url(#jb)"/>'
      + '<rect x="' + (pad - 10) + '" y="' + (pad - 10) + '" width="' + (W - 2 * pad + 20) + '" height="' + (H - 2 * pad + 20) + '" fill="#13234f" stroke="#d9971a" stroke-width="3"/>';
    order.forEach(function (o, i) {
      var x = pad + (i % cols) * cell + cell / 2, y = pad + Math.floor(i / cols) * cell + cell / 2, on = !!done[o[0]], c = LEVEL_COLOURS[o[1]];
      var info = j.lessons[o[0]];
      s += '<a href="' + R + info.u + '"><title>' + (on ? "✓ " : "") + info.t + "</title>";
      if (on) s += '<g transform="translate(' + x + " " + y + ') scale(.38) translate(-50 -53)"><path d="' + STAR + '" fill="' + c + '"/><circle cx="50" cy="53" r="15" fill="#f6f8fc"/><circle cx="50" cy="53" r="7" fill="' + c + '"/></g>';
      else s += '<path d="M' + x + " " + (y - 13) + " l13 13 -13 13 -13 -13z" + '" fill="none" stroke="#f6f8fc" stroke-opacity=".28" stroke-width="1.5" stroke-dasharray="3 3"/>';
      s += "</a>";
    });
    return s + "</svg>";
  }
  function tile(big, small, fa) { return h("div", { "class": "jtile" }, h("span", { "class": "jt-big", text: big }), fa ? faEl("span", fa, "jt-fa2") : null, h("span", { "class": "jt-small", text: small })); }
  function chelleRing(n) {
    var pct = Math.min(1, n / 40), r = 34, c = 2 * Math.PI * r;
    return '<svg viewBox="0 0 90 90" class="ring"><circle cx="45" cy="45" r="' + r + '" fill="none" stroke="var(--line)" stroke-width="9"/>'
      + '<circle cx="45" cy="45" r="' + r + '" fill="none" stroke="var(--saffron)" stroke-width="9" stroke-linecap="round" stroke-dasharray="' + (c * pct) + " " + c + '" transform="rotate(-90 45 45)"/>'
      + '<text x="45" y="51" text-anchor="middle" class="ring-n">' + n + "</text></svg>";
  }
  function renderJourney() {
    var root = $("[data-journey]"); if (!root) return;
    J().then(function (j) {
      var st = stats(j); checkBadges(j, st);
      $("[data-j-route]", root).innerHTML = routeSvg(j, st);
      var stb = $("[data-j-stats]", root); stb.innerHTML = "";
      stb.append(h("h2", { text: "So far" }), h("div", { "class": "jtiles" },
        tile(st.done + " / " + st.total, "lessons finished", "درس"),
        tile(String(st.nWords), "words learnt", "واژه"),
        tile(st.coverage + "%", "of everyday text is made of words you know", "پوشش"),
        tile(String(st.stories + st.poems), "stories and poems read", "داستان و شعر"),
        h("div", { "class": "jtile chelle" }, h("span", { "class": "jt-ring", html: chelleRing(Math.min(st.streak, 40)) }), faEl("span", "چله", "jt-fa2"),
          h("span", { "class": "jt-small", text: st.streak ? st.streak + (st.streak === 1 ? " day" : " days") + " in a row – " + (st.streak >= 40 ? "a full chelle!" : (40 - st.streak) + " to a chelle") : "Study today to start your chelle (40 days)" }))));
      if (st.longest > st.streak) stb.append(h("p", { "class": "meta", text: "Longest run: " + st.longest + " days · active on " + st.daysActive + " days in all." }));
      $("[data-j-carpet]", root).innerHTML = carpetSvg(j);
      var bx = $("[data-j-badges]", root), got = store.get("badges", {}), list = badges(j);
      bx.innerHTML = "";
      bx.append(h("p", { "class": "meta", text: Object.keys(got).length + " of " + list.length + " badges" }), h("div", { "class": "medals" }, list.map(function (b) { return medal(b, !!got[b[0]]); })));
      var cd = $("[data-j-cando]", root), done = store.get("done", {});
      cd.innerHTML = "";
      var any = false;
      j.levels.forEach(function (lv) {
        var items = [];
        lv.lessons.forEach(function (l) { if (done[l]) j.lessons[l].g.forEach(function (g) { items.push(g); }); });
        if (!items.length) return;
        any = true;
        cd.append(h("details", { "class": "cando", open: true }, h("summary", { text: lv.name + " – " + items.length + " things you can do" }), h("ul", null, items.map(function (g) { return h("li", { text: g }); }))));
      });
      if (!any) cd.append(h("p", { "class": "empty", text: "Finish a lesson (the button is at the end of each lesson) and what you've learnt to do appears here." }));
      var cert = $("[data-j-cert]", root); cert.innerHTML = "";
      var full = j.levels.filter(function (lv) { var l = st.levels[lv.id]; return l.of && l.done === l.of; });
      cert.append(h("h2", { text: "Certificates" }));
      if (!full.length) { cert.append(h("p", { "class": "empty", text: "Finish every lesson of a level to print a certificate for it." })); return; }
      var name = h("input", { type: "text", value: store.get("name", "") || "", placeholder: "Your name", "aria-label": "Your name for the certificate" });
      name.addEventListener("change", function () { store.set("name", name.value.trim()); });
      cert.append(h("p", null, h("label", null, "Name on the certificate: ", name)),
        h("p", { "class": "vbtns" }, full.map(function (lv) { return h("button", { type: "button", "class": "btn", text: "Print: " + lv.name, onclick: function () { store.set("name", name.value.trim()); printCert(lv, j); } }); })));
    });
  }
  function printCert(lv, j) {
    var old = $(".cert"); if (old) old.remove();
    var d = new Date(), fa = "";
    try { fa = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { year: "numeric", month: "long", day: "numeric" }).format(d); } catch (e) { /* ignore */ }
    var n = lv.lessons.length;
    var c = h("div", { "class": "cert" },
      h("div", { "class": "cert-in" },
        faEl("p", "گواهی‌نامه", "cert-fa"), h("p", { "class": "cert-en", text: "Certificate of achievement" }),
        h("p", { "class": "cert-line", text: "This is to certify that" }),
        h("p", { "class": "cert-name", text: store.get("name", "") || "______________________" }),
        h("p", { "class": "cert-line", text: "has completed all " + n + " lessons of" }),
        h("p", { "class": "cert-level", text: lv.name }), faEl("p", lv.fa || "", "cert-level-fa"),
        h("p", { "class": "cert-line", text: "of Learn Farsi, the open Persian course – and has travelled as far as " + lv.city + " (" + lv.cityFa + ")." }),
        faEl("p", "«توانا بود هر که دانا بود»", "cert-quote"),
        h("p", { "class": "cert-date", text: d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) + (fa ? "  ·  " : "") }, fa ? faEl("bdi", fa) : null),
        h("p", { "class": "cert-site", text: "zhangbing9708-maker.github.io/Learn-Farsi" })));
    document.body.append(c);
    document.body.classList.add("print-cert");
    var undo = function () { document.body.classList.remove("print-cert"); c.remove(); window.removeEventListener("afterprint", undo); };
    window.addEventListener("afterprint", undo);
    setTimeout(function () { window.print(); }, 50);
  }

  /* ---------------------------------------------------------------- the home page box */
  function renderHome() {
    var box = $("[data-journey-home]"); if (!box) return;
    var done = store.get("done", {}), days = store.get("days", {});
    if (!Object.keys(done).length && !Object.keys(days).length) return;
    J().then(function (j) {
      var st = stats(j), order = [];
      j.levels.forEach(function (lv) { order = order.concat(lv.lessons); });
      var next = order.filter(function (l) { return !done[l]; })[0];
      box.innerHTML = ""; box.hidden = false;
      box.append(h("div", { "class": "jh-text" },
        h("h2", { text: st.streak > 1 ? "🔥 " + st.streak + " days in a row – keep it going" : "Welcome back" }),
        h("p", { text: st.done + " of " + st.total + " lessons · " + st.nWords + " words · about " + st.coverage + "% of everyday text" }),
        h("p", { "class": "vbtns" }, next ? h("a", { "class": "btn", href: R + j.lessons[next].u, text: "Continue: " + j.lessons[next].t }) : null,
          h("a", { "class": "btn-quiet", href: R + "journey/index.html", text: "My journey" }))),
        h("div", { "class": "jh-route", html: routeSvg(j, st) }));
    });
  }

  renderJourney();
  renderHome();
})();
