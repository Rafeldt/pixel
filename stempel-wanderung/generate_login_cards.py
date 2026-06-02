"""Generate a printable login-cards PDF from credentials.csv.

Each card shows only the username, password, and the site URL.

Run import_students.py first to produce credentials.csv.
"""
import csv
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
CREDENTIALS_CSV = HERE / "credentials.csv"
OUTPUT_PDF = HERE / "login_cards.pdf"

SITE_URL = "pixel.rafeldt.ch"

COLS = 2
ROWS = 4
MARGIN_X = 15 * mm
MARGIN_Y = 15 * mm
SPACING = 4 * mm

MNG_BLUE = (0 / 255, 118 / 255, 189 / 255)
CINNABAR = (177 / 255, 56 / 255, 46 / 255)


def main() -> None:
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

        c.setStrokeColorRGB(*MNG_BLUE)
        c.setLineWidth(0.8)
        c.roundRect(x, y, card_w, card_h, 4 * mm, stroke=1, fill=0)

        # URL at top
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(*MNG_BLUE)
        c.drawCentredString(x + card_w / 2, y + card_h - 12 * mm, SITE_URL)

        # Username
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(x + 8 * mm, y + card_h - 24 * mm, "Benutzername")
        c.setFont("Courier-Bold", 16)
        c.setFillColorRGB(*MNG_BLUE)
        c.drawString(x + 8 * mm, y + card_h - 31 * mm, student["username"])

        # Password
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        c.drawString(x + 8 * mm, y + card_h - 41 * mm, "Passwort")
        c.setFont("Courier-Bold", 16)
        c.setFillColorRGB(*CINNABAR)
        c.drawString(x + 8 * mm, y + card_h - 48 * mm, student["password"])

    c.save()
    print(f"Created {OUTPUT_PDF.name} with {len(students)} cards "
          f"on {(len(students) + COLS*ROWS - 1) // (COLS*ROWS)} pages.")


if __name__ == "__main__":
    main()
