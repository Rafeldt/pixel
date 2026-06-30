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
import csv
import inspect
import json
import random
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
SUBM = ROOT / "submissions"
GALLERY = ROOT / "stempel-wanderung" / "static" / "gallery"
SOURCES = GALLERY / "sources"
MAPPING_CSV = ROOT / "gallery_mapping.csv"

WIDTH = 240            # low-res long side for the test images
SEED = 20260630        # fixes both the anonymised numbering and any randomness


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


def make_spectrum(width: int = WIDTH) -> Image.Image:
    """Smooth hue gradient (x) with a saturation/brightness ramp (y).
    A continuous rainbow — shows graustufen / schwellwert / blur gradients."""
    h = round(width * 0.62)
    img = Image.new("RGB", (width, h))
    px = img.load()
    for y in range(h):
        ty = y / (h - 1)
        for x in range(width):
            hue = x / (width - 1)
            sat = 0.35 + 0.65 * ty
            val = 1.0 - 0.55 * ty
            rr, gg, bb = colorsys.hsv_to_rgb(hue, sat, val)
            px[x, y] = (int(rr * 255), int(gg * 255), int(bb * 255))
    return img


def downscale(path: Path, width: int = WIDTH) -> Image.Image:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.resize((width, round(h * width / w)), Image.LANCZOS)


def build_sources() -> list[dict]:
    """Create the shared test images. Returns manifest entries (with grids)."""
    SOURCES.mkdir(parents=True, exist_ok=True)
    specs = []

    # 1) Real photo from the project (license-clean: our own asset).
    if (ROOT / "1_mt_fuji.jpg").exists():
        specs.append(("fuji", "Foto (Fuji)", downscale(ROOT / "1_mt_fuji.jpg")))
    # 2) Painted paint-by-numbers Fuji: flat, very saturated regions.
    if (ROOT / "design-preview.jpg").exists():
        specs.append(("gemalt", "Gemalt (Fuji)", downscale(ROOT / "design-preview.jpg")))
    # 3) Synthetic colour palette + 4) continuous spectrum.
    specs.append(("palette", "Farbpalette", make_palette()))
    specs.append(("spektrum", "Farbspektrum", make_spectrum()))

    out = []
    for sid, label, img in specs:
        rel = f"sources/{sid}.png"
        img.save(SOURCES / f"{sid}.png")
        out.append({"id": sid, "label": label, "file": rel,
                    "grid": to_grid(img),
                    "size": list(img.size)})
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
    dict(id="eigener", label="Eigener Filter", station=9,
         names=["mein_filter", "meinfilter", "eigener_filter", "eigenerfilter",
                "eigener", "mein_eigener_filter", "filter"],
         call=lambda f, g: f(g)),
]


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


def extract_namespace(nb_path: Path) -> dict:
    """Exec only the function/class defs + imports from a notebook, cell by
    cell, ignoring any cell that fails. Returns the populated namespace."""
    nb = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))
    ns: dict = {"Image": Image}
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = strip_magics("".join(cell.get("source", [])))
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        keep = [n for n in tree.body if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                ast.Import, ast.ImportFrom))]
        if not keep:
            continue
        mod = ast.Module(body=keep, type_ignores=[])
        try:
            exec(compile(mod, str(nb_path), "exec"), ns)
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
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    sources = build_sources()
    print(f"Test images: {', '.join(s['id'] + ' ' + 'x'.join(map(str, s['size'])) for s in sources)}")

    students = sorted([d for d in SUBM.iterdir() if d.is_dir()],
                      key=lambda d: d.name.lower())
    order = students[:]
    random.seed(SEED)
    random.shuffle(order)                  # decouple Projekt-NN from alphabetical

    manifest = {
        "width": WIDTH,
        "sources": [{k: s[k] for k in ("id", "label", "file", "size")} for s in sources],
        "filters": [{k: f[k] for k in ("id", "label", "station")} for f in FILTER_SPECS],
        "projects": [],
    }
    mapping_rows = []
    t0 = time.time()

    for i, folder in enumerate(order, 1):
        pid = f"projekt-{i:02d}"
        label = f"Projekt {i:02d}"
        chosen = choose_notebook(folder)
        proj = {"id": pid, "label": label, "outputs": {}, "n_filters": 0}
        if chosen is None or chosen[3] == 0:
            where = chosen[0].name if chosen else "-"
            print(f"  {pid}: NO WORKING NOTEBOOK ({folder.name}, tried {where})")
            manifest["projects"].append(proj)
            mapping_rows.append([pid, folder.name, "", 0])
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
                img.save(out_dir / f"{s['id']}__{spec['id']}.png")
                done.append(spec["id"])
                ok_filters.add(spec["id"])
            proj["outputs"][s["id"]] = done
        proj["n_filters"] = len(ok_filters)
        manifest["projects"].append(proj)
        mapping_rows.append([pid, folder.name, nb.relative_to(folder).as_posix(),
                             len(ok_filters)])
        print(f"  {pid}: {len(ok_filters)}/8 filters  <- {folder.name}/{nb.name}")

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
