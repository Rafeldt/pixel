# Bildfilter — Stempel-Wanderung

A 1f image-filter programming project for MNG Rämibühl Informatik, plus a
Flask web app that gamifies the project as a "stamp hike". Each student gets
a login card; the teacher awards stamps in person; each stamp reveals two
colours of a Mt-Fuji paint-by-numbers picture.

## Repo layout

```
chapters/                  LaTeX chapters (Projekt, Bewertung, Lernpfad, Stempel-Wanderung)
code/
  bildfilter_projekt.ipynb Student starter notebook
generate_reveal_masks.py   Quantises design-preview.jpg into 20 reveal-mask PNGs
render_gallery.py          Builds the anonymised /gallery from ./submissions/
1_mt_fuji.jpg              Source photo
design-preview.jpg         Finished painted version (used to build masks)
paint-by-numbers-canvas.pdf  The canvas students "fill in"
references.bib             biblatex sources
skript.tex / skript.pdf    Main LaTeX document
stempel-wanderung/         The Flask web app
deploy/                    Server deployment templates (systemd, Traefik)
submissions/               Raw student work (git-ignored: PII)
```

## Projekt-Galerie (`/gallery`)

`render_gallery.py` reads every student notebook from `./submissions/`
(git-ignored — student PII), runs each student's filter functions on seven
shared, colour-rich test images (Fuji + Wikimedia photos, see
`test_images/CREDITS.md`), and writes anonymised WebP results into
`stempel-wanderung/static/gallery/` (committed, served at the login-gated
`/gallery`). Paired teammates count as one project; Station 9 (the *eigener
Filter*) is reproduced from each group's own invocation.

```powershell
python render_gallery.py        # re-render after submissions change
```

Students appear as "Projekt 01..NN"; the private number→name map is written to
`gallery_mapping.csv` (git-ignored) for the teacher only.

The gallery page has three interactive parts:

- **Default "Eigene Filter" view** — each group's custom filter on every example
  picture. "Alle Stationen anzeigen" reveals the standard station filters.
- **Abstimmung** — each logged-in student distributes 100 points over their
  favourite projects; only the teacher sees the totals.
- **Upload** — a student uploads one picture and the server runs every group's
  eigener filter on it (shared in the gallery). This is the only place student
  code runs live: the Flask app imports `render_gallery` and uses the notebooks
  under `submissions/`. Those are **not** in git; deploy a trimmed copy
  (notebooks + chroma-key assets only) to the server out-of-band, e.g.

  ```bash
  scp -r _deploy_submissions/* root@server:/opt/pixel/submissions/
  ```

  (build `_deploy_submissions/` locally; it is git-ignored.) Without it the
  static gallery still works and uploads are simply disabled.

## Compile the skript

XeLaTeX, twice for cross-references:

```powershell
xelatex skript.tex
xelatex skript.tex
```

The skript depends on `../preamble/*.tex` from the sibling MNG skript folder.

## Run the web app locally

```powershell
cd stempel-wanderung
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python import_students.py ..\Auswahl_Person__19-05-2026.csv   # seed roster
python generate_login_cards.py                                # print this PDF
python app.py
```

Open <http://127.0.0.1:5000>. Teacher view at `/teacher`
(password from `$env:TEACHER_PASSWORD`, default `lehrer`).

## Regenerate reveal masks

If the design image changes:

```powershell
python generate_reveal_masks.py
```

Then update `stamps.py` if the colour-cluster order shifted (see comments
in `stamps.py`).

## Deploy

See [`deploy/README.md`](deploy/README.md) for the production playbook
(Gunicorn + systemd, behind TLJH-managed Traefik).
