"""Stamp definitions for the Bildfilter Stempel-Wanderung (Klasse 1f).

The order of STAMPS is the order students collect them.
Each stamp owns exactly two colour indices in `color_ids`. Indices
match the reveal_NN.png masks from generate_reveal_masks.py, which
clusters the canvas's regions into 20 k-means groups — so all 20
palette indices are guaranteed to have regions.

The pairings below match each cluster small-with-big so every stamp
reveals roughly similar total pixel area, with the biggest reveal
saved for the final stamp ("Auf dem Gipfel").

If the design or canvas image changes, re-run the generator. The
cluster IDs may shift; verify the per-cluster pixel counts in the
generator's output and re-tune these pairings if needed.
"""

STAMPS = [
    {
        "id": "erstes-bild",
        "station": 1,
        "title": "Erstes Bild",
        "subtitle": "Pixel sehen das Licht",
        "requirement": (
            "Bild mit lade_bild() in eine Liste laden, Hoehe und Breite "
            "ausgeben."
        ),
        "code": "px100",
        "chapter": "Schritt 0",
        "color_ids": [5, 9],
    },
    {
        "id": "kein-rot",
        "station": 2,
        "title": "Kein Rot",
        "subtitle": "Eine cyanfarbene Welt",
        "requirement": (
            "Setze den Rot-Wert aller Pixel auf 0 und speichere das Ergebnis."
        ),
        "code": "nored",
        "chapter": "Schritt 1",
        "color_ids": [1, 11],
    },
    {
        "id": "invert",
        "station": 3,
        "title": "Spiegelwelt",
        "subtitle": "Aus hell wird dunkel",
        "requirement": (
            "Funktion invertieren(bild) - jeder Farbwert wird zu 255 - Wert."
        ),
        "code": "neg255",
        "chapter": "Schritt 1",
        "color_ids": [2, 16],
    },
    {
        "id": "graustufen",
        "station": 4,
        "title": "Graustufen",
        "subtitle": "Farbe ade",
        "requirement": (
            "Funktion graustufen(bild) - Mittelwert grau = (R+G+B) // 3, "
            "neuer Pixel = (grau, grau, grau)."
        ),
        "code": "avg3",
        "chapter": "Schritt 2",
        "color_ids": [7, 19],
    },
    {
        "id": "helligkeit",
        "station": 5,
        "title": "Heller, dunkler",
        "subtitle": "Mit Clamping",
        "requirement": (
            "Funktion helligkeit(bild, h) - addiere h auf jeden Kanal, "
            "klemme auf [0, 255]."
        ),
        "code": "lux50",
        "chapter": "Schritt 2",
        "color_ids": [17, 14],
    },
    {
        "id": "schwellwert",
        "station": 6,
        "title": "Schwarz-Weiss",
        "subtitle": "Alles oder nichts",
        "requirement": (
            "Funktion schwellwert(bild, t) - Pixel ueber t werden weiss, "
            "alles andere schwarz."
        ),
        "code": "binary",
        "chapter": "Schritt 3",
        "color_ids": [12, 13],
    },
    {
        "id": "nachbarn",
        "station": 7,
        "title": "Nachbarn mischen",
        "subtitle": "Weichzeichnen",
        "requirement": (
            "Funktion box_blur(bild) - 3x3-Nachbarschaft jedes Pixels "
            "mitteln."
        ),
        "code": "mix9",
        "chapter": "Schritt 4",
        "color_ids": [10, 15],
    },
    {
        "id": "spiegelei",
        "station": 8,
        "title": "Spiegelei",
        "subtitle": "Links wird rechts",
        "requirement": (
            "Funktion spiegeln(bild) - Bild horizontal spiegeln."
        ),
        "code": "flip",
        "chapter": "Schritt 5",
        "color_ids": [3, 4],
    },
    {
        "id": "eigener",
        "station": 9,
        "title": "Eigener Filter",
        "subtitle": "Deine Erfindung",
        "requirement": (
            "Erfinde und implementiere einen eigenen Filter (z.B. "
            "Posterisierung, Verpixelung, einfache Kantenerkennung)."
        ),
        "code": "myfx",
        "chapter": "Schritt 6",
        "color_ids": [18, 6],
    },
    {
        "id": "gipfel",
        "station": 10,
        "title": "Auf dem Gipfel",
        "subtitle": "Abgabe komplett",
        "requirement": (
            "Code, drei Vorher/Nachher-Beispielbilder und kurzer "
            "Bericht abgegeben."
        ),
        "code": "summit",
        "chapter": "Schritt 7",
        "color_ids": [20, 8],
    },
]


def get_stamp_by_id(stamp_id):
    for s in STAMPS:
        if s["id"] == stamp_id:
            return s
    return None


def get_stamp_by_code(code):
    code = (code or "").lower().strip()
    for s in STAMPS:
        if s["code"].lower() == code:
            return s
    return None


# ============================================================
# Video tutorials (manim renders)
# Each tutorial is linked to one or more stamp IDs so the
# dashboard can show a "Tutorial ansehen" link on the relevant
# cards.
# ============================================================

TUTORIALS = [
    {
        "id": "pixel-filter",
        "title": "Vorlage 1: Pixel für Pixel",
        "subtitle": "Beispiel: kein_rot",
        "video": "PixelFilter.mp4",
        "duration": "0:37",
        "description": (
            "Wie man jeden Pixel einzeln umrechnet. Ideal für alle Filter, "
            "bei denen der neue Pixel nur vom gleichen Pixel im "
            "Originalbild abhängt."
        ),
        "stamps": ["kein-rot", "invert", "graustufen", "helligkeit",
                   "schwellwert"],
    },
    {
        "id": "positions-filter",
        "title": "Vorlage 2: Position frei wählen",
        "subtitle": "Beispiel: Bild horizontal spiegeln",
        "video": "PositionsFilter.mp4",
        "duration": "0:48",
        "description": (
            "Erst ein leeres Bild anlegen, dann jeden Pixel an eine "
            "gewünschte Position schreiben. Ideal für Spiegeln, Drehen, "
            "Verpixeln."
        ),
        "stamps": ["spiegelei"],
    },
    {
        "id": "box-blur",
        "title": "Box-Blur: 3×3 Nachbarschaft",
        "subtitle": ("Vom Aufschreiben aller 9 Pixel zur doppelten "
                     "for-Schleife"),
        "video": "BoxBlur.mp4",
        "duration": "1:00",
        "description": (
            "Wie man den Durchschnitt aller 9 Pixel im 3×3-Fenster "
            "berechnet und das Bild weichzeichnet."
        ),
        "stamps": ["nachbarn"],
    },
]


def tutorial_for_stamp(stamp_id):
    """Return the first tutorial whose stamps list contains stamp_id."""
    for t in TUTORIALS:
        if stamp_id in t.get("stamps", []):
            return t
    return None
