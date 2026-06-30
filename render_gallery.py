#!/usr/bin/env python3
"""Render the Bildfilter gallery for pixel.rafeldt.ch.

LOCAL build tool — not run on the server. It reads the student notebooks from
``./submissions/`` (which is git-ignored: student PII), extracts each student's
filter functions, runs them on a handful of shared low-resolution, colour-rich
test images, and writes the results into
``stempel-wanderung/static/gallery/`` (which IS committed and deployed).

Students are anonymised as "Projekt NN". The name<->number map is written to
``gallery_mapping.csv`` (git-ignored) for the teacher's private reference and
is NEVER part of the deployed app or the manifest.

Run from this folder:

    python render_gallery.py
"""
from __future__ import annotations

import ast
import colorsys
import contextlib
import csv
import inspect
import io
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
SUBM = ROOT / "submissions"
GALLERY = ROOT / "stempel-wanderung" / "static" / "gallery"
SOURCES = GALLERY / "sources"
MAPPING_CSV = ROOT / "gallery_mapping.csv"

WIDTH = 480            # target LONGEST side for the test images (well below 1000)
SEED = 20260630        # fixes both the anonymised numbering and any randomness

# Students who worked as a pair count as ONE project. The representative folder
# is kept; a teammate's separate submission folder (if any) is dropped so the
# team's work isn't duplicated. Names are only used in the private mapping CSV,
# never in the deployed (anonymised) gallery.
TEAMS = {
    "jakob": ["jakob", "lasse"],   # Jakob & Lasse worked together
    "miya": ["miya", "siqi"],      # Miya & Siqi worked together (Siqi has no own folder)
}
DROP_FOLDERS = {"lasse"}           # teammate folders represented by another folder

# Short German description of each group's Station-9 (eigener) filter, keyed by
# submission folder (stable across the anonymised Projekt-NN renumbering).
EIGENER_DESC = {
    "kira": "Benachbarte Pixel paarweise vertauscht",
    "nias": "Strudel-Verzerrung (Swirl)",
    "jakob": "Invertiert, weichgezeichnet & Farbkanäle getauscht",
    "miron": "Invertiert und mit Sinuswellen verschoben",
    "tore": "Halbtransparentes Wasserzeichen überlagert",
    "vivienne": "Kästchen-Mosaik mit abwechselnder Invertierung",
    "jelena": "Pink-violette Farbverschiebung",
    "konstantin": "Gespiegelt und mit Sinuswellen verzerrt",
    "jacqueline": "Aufgehellt und auf wenige Farben posterisiert",
    "marta": "RGB-Glitch (Farbkanäle horizontal verschoben)",
    "jascha": "Stärkste Farbe pro Pixel verstärkt",
    "ella": "Sepiabild im Kamera-Rahmen (Greenscreen)",
    "giulia": "Weichgezeichnet mit Sepia-Ton",
    "rose": "Vignette (Ränder abgedunkelt)",
    "nicolas": "CRT-Monitor-Effekt (Subpixel-Raster)",
    "loriana": "Verkleinert und grell pink-weiss eingefärbt",
    "fiona": "Zeilenweise nach Rotwert sortierte Pixel",
    "sofia": "Gekippt und violett eingefärbt",
    "mika": "Sinuswellen mit Spiegelung",
    "miya": "Kantenerkennung (Umrisse)",
    "michael": "Weichgezeichnet, auf 125 Farben reduziert & verrauscht (Fuzzy)",
}


# --------------------------------------------------------------- pixel helpers
def _c(v) -> int:
    """Coerce a colour channel to a valid 0..255 int (students emit floats /
    out-of-range values, e.g. brightness without clamping)."""
    v = int(v)
    return 0 if v < 0 else 255 if v > 255 else v


def to_grid(img: Image.Image):
    """PIL image -> nested list bild[y][x] = (r, g, b)  (student convention)."""
    img = img.convert("RGB")
    w, h = img.size
    px = img.load()
    return [[px[x, y] for x in range(w)] for y in range(h)]


def from_grid(grid) -> Image.Image:
    """Nested list -> PIL image. Defensive: clamps/ints every channel so a
    quirky student result still saves instead of crashing."""
    h = len(grid)
    w = len(grid[0])
    img = Image.new("RGB", (w, h))
    out = img.load()
    for y in range(h):
        row = grid[y]
        for x in range(w):
            p = row[x]
            out[x, y] = (_c(p[0]), _c(p[1]), _c(p[2]))
    return img


def copy_grid(grid):
    """Cheap protective copy (pixels are immutable tuples, rows are not)."""
    return [row[:] for row in grid]


EXT = "webp"          # photographic filter output -> WebP (small, lossless-ish)


def save_img(img: Image.Image, path) -> None:
    """Save a filter output. WebP keeps photos ~8x smaller than PNG while
    staying crisp on flat regions (threshold, posterize, pixel boxes)."""
    img.save(str(path), "WEBP", quality=88, method=4)


# ---------------------------------------------------------------- test images
def make_palette(width: int = WIDTH) -> Image.Image:
    """A grid of saturated colour tiles: many distinct colours, flat regions,
    a top->bottom brightness ramp, asymmetric L/R (so mirroring is visible).
    Ideal for kein_rot / graustufen / schwellwert / invertieren."""
    cols, rows = 12, 9
    cw = width // cols
    w, ch = cw * cols, cw
    h = ch * rows
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for r in range(rows):
        for c in range(cols):
            hue = ((c * 1.0 + r * 0.45) / cols) % 1.0
            val = 0.30 + 0.70 * (r / (rows - 1))
            rr, gg, bb = colorsys.hsv_to_rgb(hue, 0.88, val)
            d.rectangle([c * cw, r * ch, (c + 1) * cw - 1, (r + 1) * ch - 1],
                        fill=(int(rr * 255), int(gg * 255), int(bb * 255)))
    return img


def fit(img: Image.Image, maxside: int = WIDTH) -> Image.Image:
    """Downscale so the longer side is at most `maxside` (keeps aspect)."""
    img = img.convert("RGB")
    w, h = img.size
    s = maxside / max(w, h)
    if s < 1:
        img = img.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return img


def load_fit(path: Path, maxside: int = WIDTH) -> Image.Image:
    return fit(Image.open(path), maxside)


# Each source: id, German label, source file. Real, colour-rich photos at a
# resolution well below 1000 px. Fuji is the project's own asset; the other
# three are free Wikimedia Commons images (see test_images/CREDITS.md).
SOURCE_SPECS = [
    ("fuji", "Foto Fuji", ROOT / "1_mt_fuji.jpg"),
    ("blumen", "Tulpen", ROOT / "test_images" / "flowers.jpg"),
    ("papagei", "Papagei", ROOT / "test_images" / "parrot.jpg"),
    ("bergsee", "Bergsee", ROOT / "test_images" / "landscape.jpg"),
    ("pfau", "Pfau", ROOT / "test_images" / "peacock.jpg"),
    ("schmetterling", "Schmetterling", ROOT / "test_images" / "butterfly.jpg"),
    ("fruechte", "Früchte", ROOT / "test_images" / "fruits.jpg"),
]

CREDITS = [
    "Foto Fuji: MNG-Projektbild",
    "Tulpen: John O'Neill, CC BY-SA 3.0 (Wikimedia Commons)",
    "Papagei: Quartl, CC BY-SA 3.0 (Wikimedia Commons)",
    "Bergsee (Moraine Lake): Gorgo, gemeinfrei (Wikimedia Commons)",
    "Pfau: BS Thurner Hof, CC BY-SA 3.0 (Wikimedia Commons)",
    "Schmetterling: Kenneth Dwain Harrelson, CC BY-SA 3.0 (Wikimedia Commons)",
    "Früchte: Ionutzmovie, CC BY 3.0 (Wikimedia Commons)",
]


def build_sources() -> list[dict]:
    """Create the shared test images. Returns manifest entries (with grids)."""
    SOURCES.mkdir(parents=True, exist_ok=True)
    out = []
    for sid, label, path in SOURCE_SPECS:
        if not path.exists():
            print(f"  !! missing source image: {path}", file=sys.stderr)
            continue
        img = load_fit(path)
        save_img(img, SOURCES / f"{sid}.{EXT}")
        out.append({"id": sid, "label": label, "file": f"sources/{sid}.{EXT}",
                    "grid": to_grid(img), "size": list(img.size)})
    return out


# -------------------------------------------------------------------- filters
# Each filter: id, German label, station, accepted function names, how to call.
FILTER_SPECS = [
    dict(id="kein_rot", label="Kein Rot", station=2,
         names=["kein_rot", "keinrot", "kein_rot_filter"],
         call=lambda f, g: f(g)),
    dict(id="invertieren", label="Invertiert", station=3,
         names=["invertieren", "invertiere", "invert", "invertierung"],
         call=lambda f, g: f(g)),
    dict(id="graustufen", label="Graustufen", station=4,
         names=["graustufen", "graustufe", "grauwert", "grayscale", "graustufen_filter"],
         call=lambda f, g: f(g)),
    dict(id="helligkeit", label="Heller (+50)", station=5,
         names=["helligkeit", "heller", "helligkeit_filter"],
         call=lambda f, g: f(g, 50)),
    dict(id="schwellwert", label="Schwellwert", station=6,
         names=["schwellwert", "schwellenwert", "schwelle", "threshold"],
         call=lambda f, g: f(g, 128)),
    dict(id="box_blur", label="Weichzeichnen", station=7,
         names=["box_blur", "boxblur", "blur", "weichzeichnen", "weichzeichner"],
         call=lambda f, g: f(g)),
    dict(id="spiegeln", label="Gespiegelt", station=8,
         names=["spiegeln", "spiegle", "spiegelung", "horizontal_spiegeln", "spiegel"],
         call=lambda f, g: f(g)),
]

# Station 9 ("eigener Filter") is handled separately: it is wildly varied
# (renamed functions, composite pipelines, extra args, interactive widgets,
# extra image assets) so instead of guessing a function we *replay the
# student's actual Station-9 result expression* on the test image. See
# find_eigener_spec() / run_eigener().
EIGENER = dict(id="eigener", label="Eigener Filter", station=9)


def strip_magics(src: str) -> str:
    """Drop IPython magics / shell escapes so cells still parse."""
    keep = []
    for line in src.splitlines():
        s = line.lstrip()
        if s.startswith("%") or s.startswith("!") or s.startswith("get_ipython"):
            continue
        keep.append(line)
    return "\n".join(keep)


def candidate_notebooks(folder: Path):
    """All plausible filter notebooks in a submission folder, best-named first.
    Recurses (handles work nested in 'Untitled Folder/' etc.) and skips the
    blank 'vorlagen.ipynb' template."""
    cands = [p for p in folder.rglob("*.ipynb")
             if "vorlagen" not in p.name.lower()
             and ".ipynb_checkpoints" not in str(p)]

    def name_score(p):
        nm = p.name.lower()
        s = 0
        if nm == "bildfilter_projekt.ipynb":
            s += 100
        if "bildfilter" in nm:
            s += 40
        if "projekt" in nm or "code" in nm:
            s += 10
        s -= len(p.relative_to(folder).parts)        # prefer shallower
        return s

    cands.sort(key=name_score, reverse=True)
    return cands


def safe_parse(src: str):
    """ast.parse, but tolerant of a broken tail: if a cell has un-commented
    prose or a typo on some line (students do this a lot), keep the parseable
    prefix by truncating at the offending line and retrying."""
    for _ in range(40):
        try:
            return ast.parse(src)
        except SyntaxError as e:
            lineno = e.lineno or 1
            lines = src.splitlines()
            if lineno <= 1 or lineno > len(lines):
                return None
            src = "\n".join(lines[:lineno - 1])
            if not src.strip():
                return None
    return None


def _is_literal(node) -> bool:
    """True for a constant / container-of-constants (safe to exec at import
    time), e.g. a module-level cache `colors_done = {}` or `amplitude = 10`."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return (all(k is None or _is_literal(k) for k in node.keys)
                and all(_is_literal(v) for v in node.values))
    return False


def extract_namespace(nb_path: Path) -> dict:
    """Build a namespace from a notebook by exec-ing its top-level function/class
    defs, imports and simple literal assignments, one node at a time so a single
    failing import (e.g. ipywidgets) or broken statement never drops the rest."""
    nb = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))
    ns: dict = {"Image": Image, "math": math}
    KEEP = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.Import, ast.ImportFrom)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = strip_magics("".join(cell.get("source", [])))
        tree = safe_parse(src)
        if tree is None:
            continue
        for node in tree.body:
            if not (isinstance(node, KEEP) or
                    (isinstance(node, ast.Assign) and _is_literal(node.value))):
                continue
            try:
                exec(compile(ast.Module(body=[node], type_ignores=[]),
                             str(nb_path), "exec"), ns)
            except Exception:
                continue
    return ns


def find_callable(ns: dict, names):
    for n in names:
        fn = ns.get(n)
        if callable(fn):
            return fn
    return None


def run_filter(spec, fn, grid):
    """Run one filter, returning a PIL image or None on any failure."""
    g = copy_grid(grid)
    # 'eigener' filters that need extra args (e.g. a second image) are skipped.
    if spec["id"] == "eigener":
        try:
            sig = inspect.signature(fn)
            required = [p for p in sig.parameters.values()
                        if p.default is p.empty
                        and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(required) > 1:
                return None
        except (ValueError, TypeError):
            pass
    try:
        result = spec["call"](fn, g)
    except TypeError:
        try:
            result = fn(g)                # fall back to single-arg call
        except Exception:
            return None
    except Exception:
        return None
    if not result:
        return None
    try:
        return from_grid(result)
    except Exception:
        return None


# ----------------------------------------------------- eigener Filter (St. 9)
# Station 9 is the most varied: renamed functions, composite pipelines, extra
# args, interactive widgets, cross-cell intermediate variables, even extra
# image assets. Rather than guess a function we reproduce the student's *own*
# Station-9 invocation. Two tiers: (1) eval the expression saved to a
# "station9..." path; (2) if that needs cross-cell state, exec the whole
# notebook with patched I/O and capture the grid it saves.
EIG_PATH_RE = re.compile(r'(station[_\s-]*9|mein[_\s-]*filter|meinfilter|eigen)', re.I)
ABGABE_RE = re.compile(r'abgabe', re.I)
STD_SAVE_RE = re.compile(r'station[_\s-]*[2-8]\b', re.I)
# Filenames that denote an OVERLAY asset (frame / watermark / mask) rather than
# the subject photo: overlays load the student's real file (so chroma-keying
# works); every other photo is replaced by the shared test image.
ASSET_RE = re.compile(r'rahmen|frame|kamera|camera|watermark|wasserzeichen|'
                      r'overlay|sticker|logo|maske|mask', re.I)

EIGENER_OVERRIDES = {
    "marta": dict(expr="rgb_glitch(bild, 8)"),        # interactive widget, no save
    "nicolas": dict(expr="box_crt(bild)"),            # invocation left commented out
    # Ella's green-screen collage runs per source image: each example picture is
    # sepia-toned, shrunk and composited into her real Nikon frame (loaded as a
    # chroma-key asset). No override needed — the frame matches ASSET_RE.
    # her final filter lives in a separate notebook and 10x-upscales each pixel
    # into an alternating-invert box. base_width = how many input pixels we feed
    # = number of boxes across: higher -> finer/less boxy (the picture shows
    # through when zoomed; it blends toward grey only at tiny thumbnail size).
    "vivienne": dict(nb="eigener_filter_code", base_width=44),
    # his "fuzzy" filter (blur -> 125-colour quantise -> noise) is broken only by
    # a typo: box_blur checks bounds with undefined ny/nx (meant new_y/new_x).
    # Patch in his own box_blur with just that typo fixed so it runs. Smaller
    # base because his blur averages a 16x16 window per pixel.
    "michael": dict(
        expr="fuzzy_filter(bild, 16, 64, 0, 50)",
        base_width=240,
        patch=(
            "def box_blur(bild, blockgroesse):\n"
            "    hoehe = len(bild)\n"
            "    breite = len(bild[0])\n"
            "    neues_bild = [[(0, 0, 0)] * breite for _ in range(hoehe)]\n"
            "    for y in range(hoehe):\n"
            "        for x in range(breite):\n"
            "            summe_r = summe_g = summe_b = anzahl = 0\n"
            "            for box_y in range(blockgroesse):\n"
            "                for box_x in range(blockgroesse):\n"
            "                    new_y = y + box_y - int(blockgroesse / 2)\n"
            "                    new_x = x + box_x - int(blockgroesse / 2)\n"
            "                    if 0 <= new_y < hoehe and 0 <= new_x < breite:\n"
            "                        r, g, b = bild[new_y][new_x]\n"
            "                        summe_r += r; summe_g += g; summe_b += b\n"
            "                        anzahl += 1\n"
            "            neues_bild[y][x] = (summe_r // anzahl, summe_g // anzahl,\n"
            "                                summe_b // anzahl)\n"
            "    return neues_bild\n"
        ),
    ),
}


def downscale_grid(grid, width):
    img = from_grid(grid)
    w, h = img.size
    return to_grid(img.resize((width, max(1, round(h * width / w))), Image.NEAREST))


def _basename(p):
    return os.path.basename(str(p)).strip().lower()


def find_eigener_expr(nb_path: Path):
    """Fast path: source of the expression saved to a 'station9...' path."""
    nb = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))
    cells = ["".join(c.get("source", [])) for c in nb.get("cells", [])
             if c.get("cell_type") == "code"]
    best = None
    for raw in cells:
        src = strip_magics(raw)
        tree = safe_parse(src)
        if tree is None:
            continue
        assigns = {n.targets[0].id: n.value for n in tree.body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name)}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "speichere_bild" and len(node.args) >= 2):
                continue
            path = node.args[1]
            if not (isinstance(path, ast.Constant) and isinstance(path.value, str)):
                continue
            pv = path.value
            if ABGABE_RE.search(pv) or not EIG_PATH_RE.search(pv):
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Name) and arg.id in assigns:
                arg = assigns[arg.id]
            expr_src = ast.get_source_segment(src, arg)
            if not expr_src:
                continue
            rank = 3 if re.search(r'station[_\s-]*9|eigen', pv, re.I) else \
                2 if re.search(r'mein', pv, re.I) else 1
            if best is None or rank > best[0]:
                best = (rank, expr_src)
    return best[1] if best else None


def _asset_grid(folder: Path, filename: str, width=WIDTH):
    """Load a real asset image from the submission folder (recursive basename
    match), downscaled with NEAREST so exact colours (pure-green chroma key)
    survive."""
    target = _basename(filename)
    match = next((p for p in folder.rglob("*")
                  if p.is_file() and _basename(p.name) == target), None)
    if match is None:
        return None
    try:
        img = Image.open(match).convert("RGB")
    except Exception:
        return None
    w, h = img.size
    img = img.resize((width, max(1, round(h * width / w))), Image.NEAREST)
    return to_grid(img)


def _make_loader(base_grid, folder: Path):
    """Patched lade_bild: overlay assets -> the student's real file; any other
    photo -> the shared test image (base_grid)."""
    cache = {}

    def loader(path):
        bn = _basename(path)
        if ASSET_RE.search(bn):
            if bn not in cache:
                g = _asset_grid(folder, path)
                cache[bn] = g if g is not None else base_grid
            return copy_grid(cache[bn])
        return copy_grid(base_grid)

    return loader


def _eigener_image(grid):
    if not grid:
        return None
    try:
        return from_grid(grid)
    except Exception:
        return None


def eval_eigener(ns: dict, expr: str, base_grid, folder: Path):
    local = dict(ns)
    local["bild"] = copy_grid(base_grid)
    local["lade_bild"] = _make_loader(base_grid, folder)
    local["speichere_bild"] = lambda *a, **k: None
    random.seed(SEED)          # deterministic for filters that add random noise
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return _eigener_image(eval(compile(expr, "<eigener>", "eval"), local))
    except Exception:
        return None


def exec_capture_eigener(nb_path: Path, base_grid, folder: Path, extra_expr=None):
    """Exec a notebook's top-level statements (node by node, resilient) with
    lade_bild/speichere_bild patched, and capture the grid saved to a
    'station9...' path. Handles composites, extra args and cross-cell
    intermediate variables that the fast expr-eval can't reach."""
    nb = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))
    captured = {}
    ns = {"Image": Image, "math": math, "bild": copy_grid(base_grid),
          "lade_bild": _make_loader(base_grid, folder),
          "speichere_bild": lambda g, p="": captured.setdefault(str(p), g)}
    # The student's own lade_bild/speichere_bild (defined in cell 0) must NOT
    # replace our patched capture hooks, or nothing is captured and files get
    # written to disk. Skip those redefinitions.
    PROTECTED = {"lade_bild", "speichere_bild"}
    devnull = io.StringIO()
    failed = set()       # names whose latest assignment raised (tainted/stale)

    def is_stale_save(node):
        # speichere_bild(<tainted-name>, ...) would save a stale leftover value
        return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "speichere_bild"
                and node.value.args
                and isinstance(node.value.args[0], ast.Name)
                and node.value.args[0].id in failed)

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        tree = safe_parse(strip_magics("".join(cell.get("source", []))))
        if tree is None:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name in PROTECTED:
                continue
            if is_stale_save(node):
                continue
            targets = [t.id for t in getattr(node, "targets", [])
                       if isinstance(t, ast.Name)] if isinstance(node, ast.Assign) else []
            try:
                with contextlib.redirect_stdout(devnull):
                    exec(compile(ast.Module(body=[node], type_ignores=[]),
                                 str(nb_path), "exec"), ns)
                failed.difference_update(targets)        # assignment succeeded
            except Exception:
                failed.update(targets)                   # assignment is stale
                continue
    cand = [(p, g) for p, g in captured.items()
            if EIG_PATH_RE.search(p) and not ABGABE_RE.search(p)
            and not STD_SAVE_RE.search(p)]
    cand.sort(key=lambda pg: (0 if re.search(r'station[_\s-]*9|eigen', pg[0], re.I)
                              else 1 if re.search(r'mein', pg[0], re.I) else 2))
    for _p, g in cand:
        img = _eigener_image(g)
        if img is not None:
            return img
    if extra_expr:
        try:
            return _eigener_image(eval(compile(extra_expr, "<eig>", "eval"), ns))
        except Exception:
            return None
    return None


def render_eigener(folder: Path, chosen_nb: Path, ns_chosen: dict, base_grid):
    """Eigener-filter image for one base image: fast expr-eval first, then
    exec-capture across the folder's candidate notebooks."""
    override = EIGENER_OVERRIDES.get(folder.name, {})
    expr = override.get("expr") or find_eigener_expr(chosen_nb)
    if expr:
        if override.get("patch"):
            # Repair an obvious typo in the student's own helper so their
            # intended filter runs. Patch the SAME namespace the functions close
            # over (their __globals__), not a copy, or the fix is invisible to
            # them. Safe here: the standard filters are already rendered.
            try:
                exec(override["patch"], ns_chosen)
            except Exception:
                pass
        img = eval_eigener(ns_chosen, expr, base_grid, folder)
        if img is not None:
            return img
    extra = override.get("expr")
    prefer = override.get("nb")
    seq = [chosen_nb] + [n for n in candidate_notebooks(folder) if n != chosen_nb]
    if prefer:                       # a notebook the student points to explicitly
        seq.sort(key=lambda n: 0 if prefer.lower() in n.name.lower() else 1)
    seen = []
    for nb in seq:
        if nb in seen:
            continue
        seen.append(nb)
        img = exec_capture_eigener(nb, base_grid, folder, extra)
        if img is not None:
            return img
    return None


# ----------------------------------------------- server API (live uploads)
# These let the Flask app reuse this engine to run each project's eigener
# filter on a student-uploaded image, without ever serialising student code.
def project_order():
    """Submission folders in the committed Projekt-NN order (same seeded
    shuffle as the build), with paired-teammate folders dropped."""
    students = sorted([d for d in SUBM.iterdir() if d.is_dir()
                       and d.name.lower() not in DROP_FOLDERS],
                      key=lambda d: d.name.lower())
    random.seed(SEED)
    random.shuffle(students)
    return students


def load_projects():
    """Build each project's filter namespace once (call at server start).
    Returns [{'id','folder','nb','ns'}] in the deployed gallery order."""
    out = []
    for i, folder in enumerate(project_order(), 1):
        chosen = choose_notebook(folder)
        if chosen is None or chosen[3] == 0:
            continue
        nb, ns, _fns, _ = chosen
        out.append({"id": f"projekt-{i:02d}", "folder": folder, "nb": nb, "ns": ns})
    return out


def project_eigener_image(project, base_grid):
    """Run ONE project's eigener filter on an arbitrary base grid (an upload),
    always treating the base as the subject (ignores the 'own_image' build
    mode). Returns a PIL image or None."""
    folder, nb, ns = project["folder"], project["nb"], project["ns"]
    override = EIGENER_OVERRIDES.get(folder.name, {})
    cache = ns.get("colors_done")
    if isinstance(cache, dict):
        cache.clear()                 # avoid unbounded growth across uploads
    bw = override.get("base_width")
    base = downscale_grid(base_grid, bw) if bw else base_grid
    return render_eigener(folder, nb, ns, base)


def _probe_grid():
    """Tiny colourful grid used to score how many filters a notebook implements."""
    img = make_palette(48).crop((0, 0, 24, 18))
    return to_grid(img)


_PROBE = _probe_grid()


def evaluate(nb_path: Path):
    """Return (namespace, fns_by_filter, n_working) for a candidate notebook.
    n_working counts how many filters actually produce an image on the probe,
    so a blank template (def ... pass) scores 0 and loses to the real notebook."""
    ns = extract_namespace(nb_path)
    fns = {spec["id"]: find_callable(ns, spec["names"]) for spec in FILTER_SPECS}
    working = 0
    for spec in FILTER_SPECS:
        fn = fns.get(spec["id"])
        if fn is not None and run_filter(spec, fn, _PROBE) is not None:
            working += 1
    return ns, fns, working


def choose_notebook(folder: Path):
    """Pick the candidate notebook with the most working filters."""
    best = None
    for nb in candidate_notebooks(folder):
        ns, fns, n = evaluate(nb)
        if best is None or n > best[3]:
            best = (nb, ns, fns, n)
        if n >= len(FILTER_SPECS):
            break
    return best          # (nb_path, ns, fns, n_working) or None


# ------------------------------------------------------------------------ main
def main() -> int:
    if not SUBM.is_dir():
        print(f"!! {SUBM} not found", file=sys.stderr)
        return 1

    # Wipe previously rendered output so stale images never survive a re-run.
    if GALLERY.exists():
        import shutil
        for child in GALLERY.iterdir():
            for attempt in range(5):       # OneDrive can briefly lock files
                try:
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                    break
                except PermissionError:
                    time.sleep(0.4)

    sources = build_sources()
    print(f"Test images: {', '.join(s['id'] + ' ' + 'x'.join(map(str, s['size'])) for s in sources)}")

    students = sorted([d for d in SUBM.iterdir() if d.is_dir()
                       and d.name.lower() not in DROP_FOLDERS],
                      key=lambda d: d.name.lower())
    order = students[:]
    random.seed(SEED)
    random.shuffle(order)                  # decouple Projekt-NN from alphabetical

    manifest = {
        "width": WIDTH,
        "sources": [{k: s[k] for k in ("id", "label", "file", "size")} for s in sources],
        "filters": [{k: f[k] for k in ("id", "label", "station")}
                    for f in FILTER_SPECS + [EIGENER]],
        "credits": CREDITS,
        "projects": [],
    }
    mapping_rows = []
    t0 = time.time()

    for i, folder in enumerate(order, 1):
        pid = f"projekt-{i:02d}"
        label = f"Projekt {i:02d}"
        chosen = choose_notebook(folder)
        proj = {"id": pid, "label": label, "outputs": {}, "n_filters": 0,
                "desc": EIGENER_DESC.get(folder.name, "")}
        if chosen is None or chosen[3] == 0:
            where = chosen[0].name if chosen else "-"
            print(f"  {pid}: NO WORKING NOTEBOOK ({folder.name}, tried {where})")
            manifest["projects"].append(proj)
            mapping_rows.append([pid, " & ".join(TEAMS.get(folder.name, [folder.name])),
                                 "", 0])
            continue

        nb, ns, fns, _ = chosen
        out_dir = GALLERY / pid
        out_dir.mkdir(parents=True, exist_ok=True)

        ok_filters = set()
        for s in sources:
            done = []
            for spec in FILTER_SPECS:
                fn = fns.get(spec["id"])
                if fn is None:
                    continue
                img = run_filter(spec, fn, s["grid"])
                if img is None:
                    continue
                save_img(img, out_dir / f"{s['id']}__{spec['id']}.{EXT}")
                done.append(spec["id"])
                ok_filters.add(spec["id"])
            proj["outputs"][s["id"]] = done

        # ---- Station 9: eigener Filter — reproduce the student's invocation
        override = EIGENER_OVERRIDES.get(folder.name, {})
        if override.get("own_image"):
            # collage filters (e.g. green-screen frame) only make sense on the
            # student's own photo: render once, reuse across the source tabs.
            own = folder / override["own_image"]
            base = None
            if own.exists():
                try:
                    base = to_grid(load_fit(own))
                except Exception:
                    base = None
            img = render_eigener(folder, nb, ns, base) if base else None
            if img is not None:
                for s in sources:
                    save_img(img, out_dir / f"{s['id']}__eigener.{EXT}")
                    proj["outputs"][s["id"]].append("eigener")
                ok_filters.add("eigener")
                proj["eigener_own"] = True
        else:
            bw = override.get("base_width")
            for s in sources:
                base = downscale_grid(s["grid"], bw) if bw else s["grid"]
                img = render_eigener(folder, nb, ns, base)
                if img is not None:
                    save_img(img, out_dir / f"{s['id']}__eigener.{EXT}")
                    proj["outputs"][s["id"]].append("eigener")
                    ok_filters.add("eigener")

        proj["n_filters"] = len(ok_filters)
        manifest["projects"].append(proj)
        team = " & ".join(TEAMS.get(folder.name, [folder.name]))
        mapping_rows.append([pid, team, nb.relative_to(folder).as_posix(),
                             len(ok_filters)])
        eig = "JA " if "eigener" in ok_filters else "-- "
        print(f"  {pid}: {len(ok_filters)}/8  eigener={eig} <- "
              f"{folder.name}/{nb.name}")

    (GALLERY / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with MAPPING_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["projekt", "name", "notebook", "n_filters"])
        w.writerows(mapping_rows)

    n_proj = len(manifest["projects"])
    total_imgs = sum(len(v) for p in manifest["projects"] for v in p["outputs"].values())
    print(f"\nDone in {time.time()-t0:.1f}s: {n_proj} projects, "
          f"{total_imgs} filtered images across {len(sources)} test images.")
    print(f"Manifest -> {GALLERY/'manifest.json'}")
    print(f"Private name map -> {MAPPING_CSV} (git-ignored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
