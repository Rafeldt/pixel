# Bildfilter — Stempel-Wanderung

A small Flask web app that gamifies the image-filter project as a 15-station
"stamp hike" inspired by Japanese mountain stamp rallies. Each stamp fills in
one region of a Mt. Fuji color-by-number picture.

## Setup

```powershell
cd EF_FS26_bildfilter_projekt\stempel-wanderung
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000` in a browser.

## Configuration

Two environment variables you'll probably want to set in class:

```powershell
$env:APP_SECRET = "some-long-random-string"
$env:TEACHER_PASSWORD = "your-teacher-password"
python app.py
```

Defaults are `dev-secret-change-me` and `lehrer` — fine for trying it out,
not fine for actual use.

## How it works

- Students enter a username + 4-digit PIN. First login registers the
  account; subsequent logins verify the PIN.
- Each stamp has a short code (e.g. `shape42`, `nored`, `sigma1`).
- The teacher hands out codes in person only after verifying the work —
  the code is the gate, not the honor system.
- Each claimed stamp fills in one region of the Mt. Fuji picture on the
  student's dashboard.
- The teacher view at `/teacher` shows a progress table for all students
  plus the full code reference.

## Data

SQLite database at `data/progress.db`. Created on first run.
To wipe and restart: delete the file.

## Running on the school network

By default the app listens on `127.0.0.1` (localhost only). To let students
on the same network reach it from their laptops, change the last line of
`app.py` to:

```python
app.run(host="0.0.0.0", port=5000)
```

Then students point their browser at your laptop's LAN IP, e.g.
`http://192.168.1.42:5000`.

## Files

- `app.py` — Flask routes
- `stamps.py` — stamp definitions (id, title, requirement, code, color region)
- `templates/` — Jinja templates including the Mt. Fuji SVG
- `static/style.css` — paper-and-cinnabar styling
- `data/progress.db` — SQLite database (created at runtime)
