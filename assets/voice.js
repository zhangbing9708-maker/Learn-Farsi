/* Learn Farsi – "Friend's voice": a Persian-speaking friend records any Persian line on the site, and the learner
   can hear that recording instead of (or next to) the computer voice.

   Recordings are stored only in the learner's own storage:
   - with Google sign-in: in the hidden app-data folder of the learner's Google Drive (scope drive.appdata – this
     site can see only the files it created there, nothing else in the Drive);
   - or, without an account, in this browser on this device (IndexedDB).
   Nothing is uploaded anywhere else, and nothing goes into the site's repository. */
(function () {
  "use strict";
  var LF = window.LF;
  if (!LF) return;
  var h = LF.h, $ = LF.$, $$ = LF.$$, store = LF.store, R = LF.R;
  var CLIENT_ID = document.body.getAttribute("data-gcid") || "";
  var SCOPE = "https://www.googleapis.com/auth/drive.appdata";
  var API = "https://www.googleapis.com/drive/v3/", UP = "https://www.googleapis.com/upload/drive/v3/";
  var MAX_SECONDS = 40;
  var canRecord = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);

  /* ---------------------------------------------------------------- settings */
  function mode() { return store.get("voice:mode", "") || ""; }          // "google" | "device" | ""
  function setMode(m) { store.set("voice:mode", m); }
  function shown() { return !!store.get("voice:on", false); }
  function prefer() { return !!store.get("voice:prefer", false); }

  /* index of recordings: audio id -> {id: drive file id (google) | "", text, t} – cached so play buttons show at once */
  var index = store.get("voice:index:" + (mode() || "none"), {}) || {};
  function saveIndex() { store.set("voice:index:" + mode(), index); }
  var blobs = {};      // audio id -> object URL, for this page view

  /* ---------------------------------------------------------------- device storage (IndexedDB) */
  var dbp = null;
  function db() {
    if (dbp) return dbp;
    dbp = new Promise(function (ok, bad) {
      if (!window.indexedDB) { bad(new Error("no IndexedDB")); return; }
      var rq = indexedDB.open("lf-voice", 1);
      rq.onupgradeneeded = function () { rq.result.createObjectStore("rec", { keyPath: "a" }); };
      rq.onsuccess = function () { ok(rq.result); };
      rq.onerror = function () { bad(rq.error); };
    });
    return dbp;
  }
  function idb(modeRW, fn) {
    return db().then(function (d) {
      return new Promise(function (ok, bad) {
        var tx = d.transaction("rec", modeRW), st = tx.objectStore("rec"), out = fn(st);
        tx.oncomplete = function () { ok(out && out.result !== undefined ? out.result : undefined); };
        tx.onerror = function () { bad(tx.error); };
      });
    });
  }
  var Device = {
    list: function () {
      return idb("readonly", function (st) { return st.getAll(); }).then(function (rows) {
        var ix = {};
        (rows || []).forEach(function (r) { ix[r.a] = { id: "", text: r.text || "", t: r.t || 0 }; });
        return ix;
      });
    },
    get: function (a) { return idb("readonly", function (st) { return st.get(a); }).then(function (r) { if (!r) throw new Error("missing"); return r.blob; }); },
    put: function (a, blob, text) { return idb("readwrite", function (st) { return st.put({ a: a, blob: blob, type: blob.type, text: text, t: Date.now() }); }).then(function () { return ""; }); },
    del: function (a) { return idb("readwrite", function (st) { return st.delete(a); }); }
  };

  /* ---------------------------------------------------------------- Google Drive (app-data folder) */
  var token = null, tokenExp = 0, tokenClient = null, gisP = null, pendingToken = [];
  try { var tk = JSON.parse(sessionStorage.getItem("lf:voice:token") || "null"); if (tk && tk.exp > Date.now() + 60000) { token = tk.t; tokenExp = tk.exp; } } catch (e) { /* private mode */ }
  function loadGis() {
    if (gisP) return gisP;
    gisP = new Promise(function (ok, bad) {
      if (window.google && google.accounts && google.accounts.oauth2) { ok(); return; }
      var s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client"; s.async = true;
      s.onload = function () { ok(); }; s.onerror = function () { gisP = null; bad(new Error("Could not load Google sign-in.")); };
      document.head.appendChild(s);
    });
    return gisP;
  }
  function haveToken() { return token && tokenExp > Date.now() + 30000; }
  /* must be called from a click: Google opens its sign-in window */
  function signIn(consent) {
    if (!CLIENT_ID) return Promise.reject(new Error("Google sign-in has not been set up for this copy of the site yet."));
    return loadGis().then(function () {
      return new Promise(function (ok, bad) {
        pendingToken.push([ok, bad]);
        if (!tokenClient) {
          tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: CLIENT_ID, scope: SCOPE,
            callback: function (resp) {
              var waiting = pendingToken; pendingToken = [];
              if (resp && resp.access_token && google.accounts.oauth2.hasGrantedAllScopes(resp, SCOPE)) {
                token = resp.access_token; tokenExp = Date.now() + (Number(resp.expires_in) || 3600) * 1000;
                try { sessionStorage.setItem("lf:voice:token", JSON.stringify({ t: token, exp: tokenExp })); } catch (e) { /* ignore */ }
                waiting.forEach(function (w) { w[0](token); });
              } else {
                waiting.forEach(function (w) { w[1](new Error("Google did not give access to the app folder.")); });
              }
            },
            error_callback: function (err) {
              var waiting = pendingToken; pendingToken = [];
              waiting.forEach(function (w) { w[1](new Error(err && err.type === "popup_closed" ? "The Google window was closed." : "Google sign-in did not finish.")); });
            }
          });
        }
        tokenClient.requestAccessToken({ prompt: consent ? "consent" : "" });
      });
    });
  }
  function ensureToken() { return haveToken() ? Promise.resolve(token) : signIn(false); }
  function gfetch(url, opts) {
    return ensureToken().then(function (t) {
      opts = opts || {};
      opts.headers = opts.headers || {};
      opts.headers.Authorization = "Bearer " + t;
      return fetch(url, opts).then(function (r) {
        if (r.status === 401) { token = null; throw new Error("Your Google session has ended – press the button again to reconnect."); }
        if (!r.ok) throw new Error("Google Drive answered " + r.status + ".");
        return r;
      });
    });
  }
  var Drive = {
    list: function () {
      var ix = {};
      function page(tokenNext) {
        var u = API + "files?spaces=appDataFolder&pageSize=1000&fields=nextPageToken,files(id,name,appProperties,modifiedTime)" + (tokenNext ? "&pageToken=" + encodeURIComponent(tokenNext) : "");
        return gfetch(u).then(function (r) { return r.json(); }).then(function (j) {
          (j.files || []).forEach(function (f) {
            var p = f.appProperties || {}, a = p.a || (/^lf-([\w]+)\./.exec(f.name) || [])[1];
            if (!a) return;
            var t = Date.parse(f.modifiedTime) || 0;
            if (!ix[a] || ix[a].t < t) ix[a] = { id: f.id, text: p.text || "", t: t };
          });
          return j.nextPageToken ? page(j.nextPageToken) : ix;
        });
      }
      return page("");
    },
    get: function (a) {
      var e = index[a];
      if (!e || !e.id) return Promise.reject(new Error("missing"));
      return gfetch(API + "files/" + e.id + "?alt=media").then(function (r) { return r.blob(); });
    },
    put: function (a, blob, text) {
      var ext = /mp4|aac/.test(blob.type) ? "m4a" : /ogg/.test(blob.type) ? "ogg" : "webm";
      var meta = { name: "lf-" + a + "." + ext, parents: ["appDataFolder"], mimeType: blob.type || "audio/webm",
        appProperties: { a: a, text: String(text || "").slice(0, 100) } };
      var boundary = "lf" + Math.random().toString(36).slice(2);
      var body = new Blob(["--" + boundary + "\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" + JSON.stringify(meta) +
        "\r\n--" + boundary + "\r\nContent-Type: " + (blob.type || "audio/webm") + "\r\n\r\n", blob, "\r\n--" + boundary + "--"]);
      var old = index[a] && index[a].id;
      return gfetch(UP + "files?uploadType=multipart&fields=id", { method: "POST", body: body, headers: { "Content-Type": "multipart/related; boundary=" + boundary } })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (old) gfetch(API + "files/" + old, { method: "DELETE" }).catch(function () {});
          return j.id;
        });
    },
    del: function (a) {
      var e = index[a];
      if (!e || !e.id) return Promise.resolve();
      return gfetch(API + "files/" + e.id, { method: "DELETE" });
    },
    who: function () {
      return gfetch(API + "about?fields=user(displayName,emailAddress)").then(function (r) { return r.json(); })
        .then(function (j) { return j.user || {}; }).catch(function () { return {}; });
    }
  };
  function backend() { return mode() === "google" ? Drive : Device; }

  /* ---------------------------------------------------------------- public API used by app.js and the page */
  function has(a) { return !!(a && index[a]); }
  function url(a) {
    if (blobs[a]) return Promise.resolve(blobs[a]);
    return backend().get(a).then(function (b) { blobs[a] = URL.createObjectURL(b); return blobs[a]; });
  }
  function refresh() {
    if (!mode()) return Promise.resolve(index);
    if (mode() === "google" && !haveToken()) return Promise.resolve(index);   // keep the cached list until the learner reconnects
    return backend().list().then(function (ix) { index = ix; saveIndex(); decorate(); emit(); return ix; });
  }
  var listeners = [];
  function emit() { listeners.forEach(function (f) { try { f(); } catch (e) { /* ignore */ } }); }
  window.LFVoice = { has: has, url: url, prefer: function () { return prefer() && !!mode(); } };

  /* ---------------------------------------------------------------- the buttons next to every speaker icon */
  var MIC = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6"/></svg>';
  var FRIEND = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3.3 2.8-5 5.5-5s4.9 1.7 5.5 5"/><path class="w" d="M16.5 8.5a3.5 3.5 0 0 1 0 5M19 6.5a6.5 6.5 0 0 1 0 9"/></svg>';
  function textFor(btn) {
    var row = btn.closest(".ln, .vw, .verse, .ex-item, .wotd-w, .page-head, li, tr, .ab-row") || btn.parentNode;
    var fa = row && $("[lang=fa]", row);
    var r = row && $(".tr, .vw-r, .h-r", row);
    return { fa: fa ? fa.textContent.trim() : "", r: r ? r.textContent.trim() : "" };
  }
  function decorate() {
    var on = shown() && !!mode();
    document.body.classList.toggle("voice-on", on);
    if (!on) return;
    $$("main .say[data-a], main .ab-btn[data-a]").forEach(function (b) {
      var a = b.getAttribute("data-a"), box = b.nextElementSibling;
      if (!box || !box.classList.contains("vc")) {
        box = h("span", { "class": "vc" },
          canRecord ? h("button", { type: "button", "class": "vc-rec", "data-vrec": a, "aria-label": "Record a friend reading this", title: "Record a friend reading this", html: MIC }) : null,
          h("button", { type: "button", "class": "vc-play", "data-vplay": a, "aria-label": "Play your friend's recording", title: "Play your friend's recording", html: FRIEND }));
        b.parentNode.insertBefore(box, b.nextSibling);
      }
      var p = $(".vc-play", box);
      p.hidden = !has(a);
    });
  }
  var moT = null;
  new MutationObserver(function () { clearTimeout(moT); moT = setTimeout(decorate, 120); }).observe(document.querySelector("main") || document.body, { childList: true, subtree: true });

  var fAudio = new Audio(), fBtn = null;
  fAudio.addEventListener("ended", function () { if (fBtn) fBtn.classList.remove("on"); fBtn = null; });
  function playFriend(a, btn) {
    LF.stop();
    if (fBtn) fBtn.classList.remove("on");
    fBtn = btn; if (btn) btn.classList.add("on");
    url(a).then(function (u) { fAudio.src = u; return fAudio.play(); })
      .catch(function (e) { if (btn) btn.classList.remove("on"); toast(e.message || "Could not play the recording."); });
  }
  document.addEventListener("click", function (e) {
    var p = e.target.closest("[data-vplay]");
    if (p) { e.preventDefault(); playFriend(p.getAttribute("data-vplay"), p); return; }
    var r = e.target.closest("[data-vrec]");
    if (r) { e.preventDefault(); var t = textFor(r); openRecorder(r.getAttribute("data-vrec"), t.fa, t.r); return; }
    var tg = e.target.closest("[data-voice-toggle]");
    if (tg) {
      e.preventDefault();
      if (!mode()) { location.href = R + "voice/index.html"; return; }
      store.set("voice:on", !shown()); syncToggles(); decorate();
    }
  });
  function syncToggles() {
    $$("[data-voice-toggle]").forEach(function (b) {
      b.hidden = false;
      b.setAttribute("aria-pressed", shown() && mode() ? "true" : "false");
    });
  }

  function toast(msg) {
    var t = $(".vc-toast") || document.body.appendChild(h("div", { "class": "vc-toast", role: "status" }));
    t.textContent = msg; t.classList.add("show");
    clearTimeout(t._t); t._t = setTimeout(function () { t.classList.remove("show"); }, 4200);
  }

  /* ---------------------------------------------------------------- the recorder */
  var dlg = null;
  function openRecorder(a, fa, r) {
    if (!mode()) { location.href = R + "voice/index.html"; return; }
    if (mode() === "google" && !haveToken()) {        // sign in first (this click opens Google's window)
      ensureToken().then(function () { refresh(); openRecorder(a, fa, r); }, function (e) { toast(e.message); });
      return;
    }
    if (!dlg) {
      dlg = h("dialog", { "class": "vrec", "aria-label": "Record a friend" });
      document.body.append(dlg);
    }
    var stream = null, rec = null, chunks = [], blob = null, timer = null, secs = 0, previewUrl = null;
    dlg.innerHTML = "";
    var status = h("p", { "class": "vrec-status", "aria-live": "polite", text: "Ask your friend to read this aloud, naturally, at normal speed." });
    var recBtn = h("button", { type: "button", "class": "btn", text: "● Record" });
    var playBtn = h("button", { type: "button", "class": "btn-quiet", text: "▶ Listen back", disabled: true });
    var saveBtn = h("button", { type: "button", "class": "btn", text: "Save", disabled: true });
    var closeBtn = h("button", { type: "button", "class": "btn-quiet", text: "Cancel" });
    var where = mode() === "google" ? "your Google Drive (private app folder)" : "this browser on this device";
    dlg.append(
      h("h2", { text: "Record a friend" }),
      LF.faEl("p", fa || "", "vrec-fa"), r ? h("p", { "class": "tr", text: r }) : null,
      status, h("div", { "class": "vrec-actions" }, recBtn, playBtn, saveBtn, closeBtn),
      h("p", { "class": "vrec-where", text: "Saved only in " + where + "." + (has(a) ? " This replaces the recording you already have for this line." : "") }));
    function stopStream() { if (stream) stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    function stopRec() { if (rec && rec.state === "recording") rec.stop(); clearInterval(timer); }
    recBtn.onclick = function () {
      if (rec && rec.state === "recording") { stopRec(); return; }
      navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }).then(function (s) {
        stream = s; chunks = []; blob = null; secs = 0;
        var type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"].filter(function (t) { return MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t); })[0];
        rec = type ? new MediaRecorder(s, { mimeType: type }) : new MediaRecorder(s);
        rec.ondataavailable = function (ev) { if (ev.data && ev.data.size) chunks.push(ev.data); };
        rec.onstop = function () {
          stopStream();
          blob = new Blob(chunks, { type: (rec.mimeType || type || "audio/webm").split(";")[0] });
          if (previewUrl) URL.revokeObjectURL(previewUrl);
          previewUrl = URL.createObjectURL(blob);
          recBtn.textContent = "● Record again"; recBtn.classList.remove("on");
          playBtn.disabled = saveBtn.disabled = !blob.size;
          status.textContent = blob.size ? "Listen back, then save – or record again." : "Nothing was recorded – try again.";
        };
        rec.start();
        recBtn.textContent = "■ Stop"; recBtn.classList.add("on"); playBtn.disabled = saveBtn.disabled = true;
        status.textContent = "Recording… 0 s";
        timer = setInterval(function () { secs++; status.textContent = "Recording… " + secs + " s"; if (secs >= MAX_SECONDS) stopRec(); }, 1000);
      }, function () { status.textContent = "The microphone is blocked. Allow it in the browser's address bar and try again."; });
    };
    playBtn.onclick = function () { if (previewUrl) { fAudio.src = previewUrl; fAudio.play(); } };
    saveBtn.onclick = function () {
      if (!blob) return;
      saveBtn.disabled = true; status.textContent = "Saving…";
      backend().put(a, blob, fa).then(function (id) {
        index[a] = { id: id || "", text: fa || "", t: Date.now() }; saveIndex();
        if (blobs[a]) URL.revokeObjectURL(blobs[a]);
        blobs[a] = URL.createObjectURL(blob);
        decorate(); emit(); close(); toast("Saved. Press the person button to hear your friend.");
      }, function (e) { saveBtn.disabled = false; status.textContent = "Not saved: " + (e.message || e); });
    };
    function close() { stopRec(); stopStream(); try { dlg.close(); } catch (e) { dlg.removeAttribute("open"); } }
    closeBtn.onclick = close;
    dlg.onclose = function () { stopRec(); stopStream(); };
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  }

  /* ---------------------------------------------------------------- the Friend's voice page */
  var panel = $("[data-voice-page]");
  function renderPage() {
    if (!panel) return;
    var st = $("[data-voice-status]", panel), list = $("[data-voice-list]", panel);
    var m = mode();
    $$("[data-voice-signin]", panel).forEach(function (b) { b.hidden = m === "google" && haveToken(); });
    $$("[data-voice-signout]", panel).forEach(function (b) { b.hidden = m !== "google"; });
    $$("[data-voice-device]", panel).forEach(function (b) { b.hidden = m === "device"; });
    $$("[data-voice-settings]", panel).forEach(function (b) { b.hidden = !m; });
    var on = $("[data-voice-show]", panel), pf = $("[data-voice-prefer]", panel);
    if (on) on.checked = shown(); if (pf) pf.checked = prefer();
    if (!CLIENT_ID) $$("[data-voice-noclient]", panel).forEach(function (x) { x.hidden = false; });
    if (!m) st.textContent = "Not set up yet. Choose where your recordings are kept.";
    else if (m === "device") st.textContent = "Recordings are kept in this browser on this device only.";
    else st.textContent = haveToken() ? "Connected to Google Drive – recordings go to this site's private app folder in your Drive." : "Google Drive is chosen. Press “Sign in with Google” to connect again.";
    if (m === "google" && haveToken()) Drive.who().then(function (u) { if (u.emailAddress) st.textContent = "Signed in as " + (u.displayName ? u.displayName + " – " : "") + u.emailAddress + ". Recordings go to this site's private app folder in your Google Drive."; });
    list.innerHTML = "";
    var keys = Object.keys(index).sort(function (x, y) { return (index[y].t || 0) - (index[x].t || 0); });
    if (!m) return;
    if (!keys.length) { list.append(h("p", { "class": "empty", text: "No recordings yet. Turn on the buttons below, open any lesson and press the microphone next to a speaker icon." })); return; }
    var ul = h("ul", { "class": "vlist" });
    keys.forEach(function (a) {
      ul.append(h("li", null,
        h("button", { type: "button", "class": "vc-play", "data-vplay": a, "aria-label": "Play", html: FRIEND }),
        LF.faEl("span", index[a].text || a, "vlist-fa"),
        h("span", { "class": "meta", text: index[a].t ? new Date(index[a].t).toLocaleDateString() : "" }),
        h("button", { type: "button", "class": "btn-quiet", text: "Delete", onclick: function (e) {
          var b = e.currentTarget; b.disabled = true;
          backend().del(a).then(function () { delete index[a]; saveIndex(); renderPage(); decorate(); }, function (er) { b.disabled = false; toast(er.message); });
        } })));
    });
    list.append(h("p", { "class": "meta", text: keys.length + (keys.length === 1 ? " recording" : " recordings") }), ul);
  }
  if (panel) {
    listeners.push(renderPage);
    panel.addEventListener("click", function (e) {
      var t = e.target;
      if (t.closest("[data-voice-signin]")) {
        e.preventDefault();
        signIn(mode() !== "google").then(function () {
          if (mode() !== "google") { setMode("google"); index = store.get("voice:index:google", {}) || {}; store.set("voice:on", true); }
          return refresh();
        }).then(renderPage, function (er) { toast(er.message); renderPage(); });
      } else if (t.closest("[data-voice-device]")) {
        e.preventDefault();
        setMode("device"); index = {}; store.set("voice:on", true);
        refresh().then(renderPage, function (er) { toast("This browser cannot store recordings: " + er.message); });
      } else if (t.closest("[data-voice-signout]")) {
        e.preventDefault();
        if (token && window.google && google.accounts) { try { google.accounts.oauth2.revoke(token, function () {}); } catch (er) { /* ignore */ } }
        token = null; tokenExp = 0;
        try { sessionStorage.removeItem("lf:voice:token"); } catch (er) { /* ignore */ }
        store.set("voice:index:google", {}); setMode(""); index = {};
        renderPage(); decorate(); toast("Signed out. Your recordings stay in your Google Drive.");
      }
    });
    panel.addEventListener("change", function (e) {
      if (e.target.matches("[data-voice-show]")) { store.set("voice:on", e.target.checked); syncToggles(); decorate(); }
      if (e.target.matches("[data-voice-prefer]")) store.set("voice:prefer", e.target.checked);
    });
  }

  syncToggles();
  decorate();
  refresh().then(renderPage, function () { renderPage(); });
})();
