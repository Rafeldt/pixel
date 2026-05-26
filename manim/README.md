# Manim-Animationen — Bildfilter

Erklärende Animationen für die Codemuster aus `code/vorlagen.ipynb` und
`code/bildfilter_projekt.ipynb`.

## Szenen

| Szene | Erklärt | Bezug |
|---|---|---|
| `PixelFilter` | Vorlage 1: jeden Pixel einzeln umrechnen | `kein_rot`, Stationen 2–6 |
| `PositionsFilter` | Vorlage 2: leeres Bild, dann Pixel platzieren | Station 8 (Spiegeln) |
| `BoxBlur` | 3×3-Nachbarschaft mitteln | Station 7 (Nachbarn mischen) |
| `VideoPipeline` | Frame für Frame filtern | `bearbeite_video` |

## Voraussetzungen

```bash
pip install manim
# Auf einem frischen Linux-System ausserdem:
apt install ffmpeg libcairo2-dev libpango1.0-dev
```

Auf dem Hetzner-Server ist die manim-venv bereits unter
`/opt/kuersli/.venv/` eingerichtet.

## Rendern

Preview-Qualität (480p15, schnell zum Iterieren):

```bash
manim -ql bildfilter_animationen.py PixelFilter
```

Hohe Qualität (1080p60, Klassenkontext):

```bash
manim -qh bildfilter_animationen.py PixelFilter
```

Alle vier Szenen am Stück:

```bash
manim -qh bildfilter_animationen.py
```

Die fertigen MP4s landen unter
`media/videos/bildfilter_animationen/1080p60/<SzenenName>.mp4`.

## Server-Render (parallel)

Auf dem Hetzner-Server kann ich alle vier Szenen parallel rendern
(matching the kuersli render workflow):

```bash
ssh offerte '
cd /opt/kuersli
source .venv/bin/activate
cd /tmp/manim_bildfilter
ls -1 *.py | xargs -n1 -P 4 -I{} manim -qh {} 
'
```

(Für `kuersli`-style isolation: jede Szene rendert in ihr eigenes
`--media_dir "/tmp/manim_..._XXXXXX"` und das fertige MP4 wird danach
nach `media/videos/.../1080p60/` verschoben.)
