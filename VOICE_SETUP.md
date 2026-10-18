# Friend's voice – switching on Google sign-in

The **Friend's voice** feature lets a learner record a Persian-speaking friend reading any line on the site and hear
that recording later – next to the computer voice, or instead of it (dialogues, *Play all*, listening exercises).

Recordings are stored **only in the learner's own storage**:

- **Google Drive (recommended):** the learner signs in with their own Google account and each recording is saved as a
  small audio file (`lf-<line id>.webm`) in the hidden **app-data folder** of *their* Drive. The site asks only for the
  `https://www.googleapis.com/auth/drive.appdata` scope, so it can see nothing else in the Drive, and the files do not
  appear among the learner's documents.
- **This device only:** without an account, recordings are kept in the browser (IndexedDB).

The site has no server: audio goes straight from the learner's browser to their Google Drive. Nothing is committed to
this repository or sent anywhere else. The code is in `assets/voice.js`; the settings page is `voice/index.html`.

Until a Google client ID is set, the *Sign in with Google* button explains that Google sign-in isn't switched on yet,
and learners can still use *This device only*.

## One-time setup (about 10 minutes)

1. Go to <https://console.cloud.google.com/>, sign in, and create a project (for example *Learn Farsi*).
2. **APIs & Services → Library**: find **Google Drive API** and press *Enable*.
3. **Google Auth Platform** (formerly *OAuth consent screen*):
   - *Branding*: app name *Learn Farsi*, your support email, home page
     `https://zhangbing9708-maker.github.io/Learn-Farsi/`, privacy policy
     `https://zhangbing9708-maker.github.io/Learn-Farsi/voice/index.html` (the Privacy section there), authorised domain
     `zhangbing9708-maker.github.io`.
   - *Audience*: **External**. While the app is in *Testing*, only the Google accounts you add as test users can sign
     in; press **Publish app** to let every learner sign in. `drive.appdata` is a non-sensitive scope, so publishing
     normally does not need Google's review.
   - *Data access*: add the scope `.../auth/drive.appdata`.
4. **Clients → Create client → Web application**:
   - Authorised JavaScript origins: `https://zhangbing9708-maker.github.io` (and `http://localhost:8000` if you want
     to test locally with `python3 -m http.server 8000` from the folder above the repository).
   - No redirect URIs are needed. Create it and copy the **Client ID** (it ends in `.apps.googleusercontent.com`).
     A client ID is not a secret; it is meant to be public.
5. Put it in `tools/site_config.json`:

   ```json
   { "google_client_id": "1234567890-abc123.apps.googleusercontent.com" }
   ```

6. Rebuild and publish:

   ```
   python3 tools/build_site.py
   git commit -am "Switch on Google sign-in for Friend's voice" && git push
   ```

## How learners use it

1. Open **Tools → Friend's voice**, press **Sign in with Google** (or *Keep them on this device only*).
2. On any lesson, story, article or poem, press **Friend's voice** in the bar at the top. A **microphone** button appears
   under every speaker icon; the friend presses it, reads the Persian shown, listens back and saves.
3. A **person** button then plays the friend's recording. Tick *Use my friend's voice instead of the computer voice*
   on the Friend's voice page to hear it everywhere, including *Play all* and the listening exercises.
4. The Friend's voice page lists every recording, with play and delete. Signing out leaves the recordings in the
   learner's Drive; Drive → Settings → Manage apps → Learn Farsi → *Delete hidden app data* removes them all.
