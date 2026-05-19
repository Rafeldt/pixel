"""Generate a printable login-cards PDF from credentials.csv.

Usage:
    python generate_login_cards.py            # default URL
    python generate_login_cards.py http://10.0.0.5:5000

Run import_students.py first to produce credentials.csv.
"""
import csv
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
CREDENTIALS_CSV = HERE / "credentials.csv"
OUTPUT_PDF = HERE / "login_cards.pdf"

# Card layout: 2 columns x 4 rows = 8 cards per A4 page
COLS = 2
ROWS = 4
MARGIN_X = 15 * mm
MARGIN_Y = 15 * mm
SPACING = 4 * mm

# MNG Blau ZH (matches the website + the skripts)
MNG_BLUE = (0 / 255, 118 / 255, 189 / 255)
CINNABAR = (177 / 255, 56 / 255, 46 / 255)


def main(default_url: str) -> None:
    if not CREDENTIALS_CSV.exists():
        print(f"ERROR: {CREDENTIALS_CSV.name} not found. "
              f"Run import_students.py first.")
        sys.exit(1)

    with CREDENTIALS_CSV.open(encoding="utf-8", newline="") as f:
        students = list(csv.DictReader(f))

    page_w, page_h = A4
    card_w = (page_w - 2 * MARGIN_X - (COLS - 1) * SPACING) / COLS
    card_h = (page_h - 2 * MARGIN_Y - (ROWS - 1) * SPACING) / ROWS

    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A4)
    c.setTitle("Bildfilter Stempel-Wanderung - Login Cards")

    for idx, student in enumerate(students):
        pos = idx % (COLS * ROWS)
        if pos == 0 and idx > 0:
            c.showPage()

        col = pos % COLS
        row = pos // COLS

        x = MARGIN_X + col * (card_w + SPACING)
        y = page_h - MARGIN_Y - (row + 1) * card_h - row * SPACING

        # --- Card frame ---
        c.setStrokeColorRGB(*MNG_BLUE)
        c.setLineWidth(0.8)
        c.roundRect(x, y, card_w, card_h, 4 * mm, stroke=1, fill=0)

        # --- Top accent bar ---
        c.setFillColorRGB(*MNG_BLUE)
        c.rect(x, y + card_h - 18 * mm, card_w, 18 * mm, stroke=0, fill=1)

        # --- Title (in accent bar) ---
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x + 6 * mm, y + card_h - 9 * mm,
                     "Bildfilter — Stempel-Wanderung")
        c.setFont("Helvetica", 9)
        c.drawString(x + 6 * mm, y + card_h - 14.5 * mm,
                     "Klasse 1f  ·  Informatik")

        # --- Student name ---
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 6 * mm, y + card_h - 26 * mm,
                     student["display_name"])

        # --- Credentials block ---
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(x + 6 * mm, y + card_h - 36 * mm, "Benutzername")
        c.drawString(x + 6 * mm, y + card_h - 49 * mm, "Passwort")

        c.setFont("Courier-Bold", 16)
        c.setFillColorRGB(*MNG_BLUE)
        c.drawString(x + 6 * mm, y + card_h - 42 * mm, student["username"])
        c.setFillColorRGB(*CINNABAR)
        c.drawString(x + 6 * mm, y + card_h - 55 * mm, student["password"])

        # --- URL footer ---
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(x + 6 * mm, y + 5 * mm, f"Adresse: {default_url}")

    c.save()
    print(f"Created {OUTPUT_PDF.name} with {len(students)} cards "
          f"on {(len(students) + COLS*ROWS - 1) // (COLS*ROWS)} pages.")
    print(f"   URL printed on cards: {default_url}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
    main(url)
