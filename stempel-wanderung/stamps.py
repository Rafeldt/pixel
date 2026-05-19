"""Stamp definitions for the Bildfilter Stempel-Wanderung (Klasse 1f).

The order of STAMPS is the order students collect them.
Each stamp owns one or two color indices in `color_ids`. Those indices
match the reveal_NN.png masks produced by generate_reveal_masks.py.

The current assignment was tuned to the output of generate_reveal_masks
on the current design-preview.jpg + canvas.png:
  - Early stamps (1-6) reveal a single small-to-medium colour.
  - Later stamps (7-10) reveal two colours each, ending with the
    biggest reveal at "Auf dem Gipfel".
Six palette indices (3, 8, 9, 12, 16, 19) have no canvas regions
under the current image pair, so they aren't referenced by any stamp.

If the design or canvas image changes, re-run the generator and
re-tune these pairings.
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
        "color_ids": [14],
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
        "color_ids": [7],
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
        "color_ids": [18],
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
        "color_ids": [20],
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
        "color_ids": [6],
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
        "color_ids": [2],
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
        "color_ids": [1, 17],
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
        "color_ids": [13, 15],
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
        "color_ids": [5],
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
        "color_ids": [4, 11],
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
