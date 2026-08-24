# MoodyTunes

A Django-based music player that recommends songs based on your mood. Mood can
be picked manually (Happy / Sad / Angry / Fear / Neutral), detected from your
webcam, or typed as free text — both routed through ML models rather than
opening any native windows.

## Features

- User signup / login (Django auth)
- Browse songs by language (Hindi/English) or mood, with combined
  mood+language+artist filtering and search
- Playlists — including **collaborative** ones (add collaborators by
  username; they get full edit rights, only the owner can rename/delete)
- Favourites, 5-star ratings (with a Popular page sorted by average rating),
  and recently-played tracking
- Mood detection two ways, both logged to a per-user mood history:
  - Webcam (`/cam/`): browser captures one frame via `getUserMedia`, sent to
    the server for a single DeepFace analysis — no native windows, works
    headless/deployed
  - Text (`/mood-text/`): type how you're feeling, classified by a
    HuggingFace emotion model
  - `/mood-history/` visualizes it: per-mood totals, a 30-day heatmap, and a
    camera-vs-text source breakdown
- User-submitted song uploads, held in a `Pending` review queue until an
  admin approves them via Django admin (bulk approve/reject actions)
- A shared, persistent audio player (play/pause, seek, volume, queue,
  shuffle) whose accent color shifts to match the mood of whatever's playing
- Spotify integration (`/spotify/`), OAuth-connected per user:
  - Search Spotify's catalog and play full tracks in-app via the Web
    Playback SDK (requires Premium on the connected account)
  - Import your Liked Songs or any of your Spotify playlists into a
    MoodyTunes playlist
  - Export a MoodyTunes playlist back to a real Spotify playlist (local
    songs are matched by name + artist search)
  - Mood-based picks (`/spotify/recommendations/`): curated per-mood search
    queries, since Spotify retired the Recommendations/Audio Features
    endpoints for new apps in Nov 2024 — see Notes below
- Django admin for managing songs, ratings, and playlists

## Tech stack

- Django 4.1, SQLite (dev database)
- OpenCV + DeepFace + TensorFlow/Keras (webcam emotion detection)
- transformers + PyTorch (CPU) (text emotion detection —
  `j-hartmann/emotion-english-distilroberta-base`)
- django-crispy-forms (auth forms)
- Vanilla JS + a small custom CSS design system (`static/musicapp/css/theme.css`)
  — no frontend framework, no Bootstrap/jQuery

## Setup

Requires **Python 3.10** (TensorFlow 2.11 does not support 3.11+).

```bash
# create and activate a virtual environment with uv
uv venv --python 3.10 .venv
source .venv/Scripts/activate   # Windows Git Bash
# .venv\Scripts\activate        # Windows cmd/PowerShell

# install dependencies
uv pip install -r requirements.txt
# torch needs the CPU-only wheel index (this file's torch line only pins the
# version, not the index):
uv pip install torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu

# apply migrations
python manage.py migrate

# create an admin user (optional)
python manage.py createsuperuser

# run the dev server
python manage.py runserver
```

Then visit http://127.0.0.1:8000/.

## Notes

- `DEBUG = True` and a hardcoded `SECRET_KEY` are set in `moodytunes/settings.py`
  for local development only — do not deploy as-is.
- `/mood-text/` runs its classifier in a **separate subprocess** per request,
  not in-process — this server already loads DeepFace/TensorFlow at startup
  (`musicapp/views.py`), and on Windows having both TensorFlow and PyTorch
  loaded in the same process causes a native DLL init failure. The tradeoff:
  every `/mood-text/` submission pays the ~20-25s cost of importing
  torch/transformers fresh (mostly Python import overhead, not model size or
  network — confirmed even with the model already cached locally), since nothing
  is cached across requests. First use also downloads the model (~300MB) from
  HuggingFace on top of that.
- Spotify API credentials go in `.env` (see `.env` — gitignored):
  `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`. Create
  an app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
  and add the redirect URI there.
  - New apps sit in **Development Mode**: only Spotify accounts you
    explicitly allowlist in the dashboard (up to 25) can connect until you
    request extended quota.
  - In-app playback (Web Playback SDK) requires **Spotify Premium** on the
    connected account; free accounts can still search, import, and export.
  - Deployed (non-`localhost`) use needs an HTTPS redirect URI — the SDK and
    OAuth flow both require it.
  - If you already connected an account before this integration grew import/
    export, disconnect and reconnect once — those need scopes
    (`playlist-read-private`, `playlist-modify-private`, `user-library-read`,
    etc.) the original connection didn't request.
  - Spotify killed the Recommendations and Audio Features endpoints for any
    app created after 2024-11-27, with no path back for new apps
    ([announcement](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)).
    Mood-based picks here use curated search queries instead of
    valence/energy scoring as a result.
