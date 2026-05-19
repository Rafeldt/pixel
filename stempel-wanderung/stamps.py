"""Stamp definitions for the Bildfilter Stempel-Wanderung (Klasse 1f).

The order of STAMPS is the order students collect them.
Each stamp owns two color indices in `color_ids`. Those color indices
match the reveal_NN.png masks produced by generate_reveal_masks.py.

The assignment below pairs each big colour with a small one so each
stamp adds roughly similar visible area. Re-run generate_reveal_masks.py
if the design image changes, then adjust color_ids if a new colour
order falls out of the quantiser.
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
        "color_ids": [16, 8],
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
        "color_ids": [9, 12],
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
        "color_ids": [19, 3],
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
        "color_ids": [10, 13],
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
        "color_ids": [4, 1],
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
        "color_ids": [14, 7],
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
        "color_ids": [20, 18],
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
        "color_ids": [2, 6],
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
        "color_ids": [17, 5],
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
        "color_ids": [15, 11],
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
