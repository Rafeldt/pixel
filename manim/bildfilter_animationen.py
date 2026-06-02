"""Manim animations for the Bildfilter project (1f).

Covers the key code patterns used in vorlagen.ipynb and the 10 stations
of bildfilter_projekt.ipynb:

  - PixelFilter      Vorlage 1: pro Pixel umrechnen      (Beispiel kein_rot)
  - PositionsFilter  Vorlage 2: Position frei waehlen    (Beispiel spiegeln)
  - BoxBlur          3x3 Nachbarschaft mitteln           (Station 7)
  - VideoPipeline    Frame fuer Frame filtern            (bearbeite_video)

Render examples (manim community 0.20.x):
    manim -ql bildfilter_animationen.py PixelFilter
    manim -qh bildfilter_animationen.py BoxBlur
"""
from manim import *
import colorsys
import numpy as np

# =====================================================================
# Style
# =====================================================================
MNG_BLUE       = "#0076BD"
MNG_BLUE_DARK  = "#003C64"
MNG_BLUE_LIGHT = "#99C8E5"
CINNABAR       = "#B1382E"
PAPER          = "#FAF6EE"
INK            = "#2A2118"
INK_SOFT       = "#6B5F4F"

config.background_color = PAPER

# Sample 4x6 image (rows x cols)
SAMPLE_IMG = [
    ["#FFD89B", "#FFD89B", "#FFC93C", "#FFC93C", "#FFD89B", "#FFD89B"],
    ["#FFD89B", "#FFE8C8", "#FFD580", "#FFD580", "#FFD89B", "#FFD89B"],
    ["#9AAEC8", "#9AAEC8", "#BDC8DE", "#BDC8DE", "#6E83A3", "#6E83A3"],
    ["#5C7B4F", "#5C7B4F", "#6E8B5A", "#6E8B5A", "#4A7BA0", "#4A7BA0"],
]


def build_gradient_sample(rows=4, cols=6, hue_from=25, hue_to=240,
                         sat_from=0.95, sat_to=0.20, lightness=0.55):
    """Build a sample image with:
       * a hue gradient from top (`hue_from`) to bottom (`hue_to`), and
       * a saturation gradient from left (`sat_from`) to right (`sat_to`).
       No identical pixels — used for the mirroring scene so the swap is
       unambiguous. Hues are HSL degrees.
    """
    img = []
    for y in range(rows):
        denom_y = max(1, rows - 1)
        hue = hue_from + (y / denom_y) * (hue_to - hue_from)
        row = []
        for x in range(cols):
            denom_x = max(1, cols - 1)
            sat = sat_from + (x / denom_x) * (sat_to - sat_from)
            r, g, b = colorsys.hls_to_rgb(hue / 360.0, lightness, sat)
            row.append(f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}")
        img.append(row)
    return img


# =====================================================================
# Helpers
# =====================================================================

def make_pixel_grid(colors, square_size=0.55, stroke_color=WHITE,
                    stroke_width=2):
    rows = len(colors)
    cols = len(colors[0])
    grid = VGroup()
    cells = []
    for y in range(rows):
        row = []
        for x in range(cols):
            sq = Square(side_length=square_size)
            sq.set_fill(colors[y][x], opacity=1)
            sq.set_stroke(stroke_color, width=stroke_width)
            sq.move_to([
                (x - (cols - 1) / 2) * square_size,
                -(y - (rows - 1) / 2) * square_size,
                0,
            ])
            grid.add(sq)
            row.append(sq)
        cells.append(row)
    grid.cells = cells
    grid.n_rows = rows
    grid.n_cols = cols
    return grid


def empty_grid_like(grid, fill=BLACK):
    rows, cols = grid.n_rows, grid.n_cols
    return make_pixel_grid([[fill] * cols for _ in range(rows)])


def title_text(text, color=MNG_BLUE_DARK):
    return Text(text, color=color, font_size=40, weight=BOLD)


def label(text, color=INK, size=22):
    return Text(text, color=color, font_size=size)


def code_line(text, color=INK):
    return Text(text, color=color, font="JetBrains Mono", font_size=22)


# Approx width of one monospace character (JetBrains Mono) at font_size=1
_MONO_CHAR_W = 0.0078


def mono(text, color=INK, size=18):
    """Monospace Text with leading-space indentation preserved.

    manim's Text strips/collapses leading whitespace and renders NBSP at
    zero width with some fonts, so we strip the leading spaces ourselves
    and apply a manual horizontal shift proportional to the indent level.
    The shifted-text object remembers its left-of-the-indent anchor at
    `.left_anchor` for aligned_edge layout.
    """
    stripped = text.lstrip(" ")
    indent = len(text) - len(stripped)
    t = Text(stripped, color=color, font="JetBrains Mono", font_size=size)
    if indent:
        t.shift(RIGHT * indent * _MONO_CHAR_W * size)
    return t


def code_block(lines, color=INK, size=18, line_buff=0.12):
    """A VGroup of monospace Text lines with proper indentation.

    Lines are arranged DOWN with aligned_edge=LEFT, then each line is
    shifted right by its indent so the visual indentation is preserved.
    Empty strings render as invisible placeholders so they still
    occupy a row (creating a blank visual gap).
    """
    items = []
    indents = []
    for line in lines:
        stripped = line.lstrip(" ")
        indents.append(len(line) - len(stripped))
        if stripped:
            items.append(Text(stripped, color=color,
                              font="JetBrains Mono", font_size=size))
        else:
            # Invisible placeholder of normal line height — keeps the
            # vertical gap intact under arrange().
            ph = Text("x", color=color, font="JetBrains Mono",
                      font_size=size)
            ph.set_opacity(0)
            items.append(ph)
    grp = VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=line_buff)
    for t, ind in zip(items, indents):
        if ind:
            t.shift(RIGHT * ind * _MONO_CHAR_W * size)
    return grp


# =====================================================================
# Scene 1 — Pixel-für-Pixel (Vorlage 1)
# =====================================================================

class PixelFilter(Scene):
    """Vorlage 1: jeder neue Pixel haengt nur vom GLEICHEN Eingangspixel ab.
    Beispiel: kein_rot."""

    def construct(self):
        # --- Title and subtitle -------------------------------------
        t = title_text("Vorlage 1: Pixel für Pixel").to_edge(UP, buff=0.4)
        sub = label("Beispiel: kein_rot, der Rotwert wird 0",
                    color=INK_SOFT, size=22).next_to(t, DOWN, buff=0.2)
        self.play(Write(t), run_time=1.2)
        self.play(FadeIn(sub, shift=DOWN * 0.2), run_time=0.8)
        self.wait(1.5)

        # --- Build the two grids ------------------------------------
        original = make_pixel_grid(SAMPLE_IMG, square_size=0.55)
        new = empty_grid_like(original, fill="#222222")
        original.shift(LEFT * 3.4 + DOWN * 0.2)
        new.shift(RIGHT * 3.4 + DOWN * 0.2)

        lbl_in = label("bild (Original)", color=MNG_BLUE)\
            .next_to(original, UP, buff=0.25)
        lbl_out = label("neues_bild", color=CINNABAR)\
            .next_to(new, UP, buff=0.25)

        self.play(FadeIn(original, shift=UP * 0.2),
                  FadeIn(lbl_in, shift=UP * 0.2), run_time=1.0)
        self.wait(0.6)
        self.play(FadeIn(new, shift=UP * 0.2),
                  FadeIn(lbl_out, shift=UP * 0.2), run_time=1.0)
        self.wait(1.0)

        # --- Reading cursor walks the original ----------------------
        cursor = Square(side_length=0.62, stroke_color=CINNABAR,
                        stroke_width=5, fill_opacity=0)
        cursor.move_to(original.cells[0][0].get_center())
        pixel_label = label("Pixel = (r, g, b)  ➜  (0, g, b)",
                            color=INK, size=22).to_edge(DOWN, buff=0.7)
        self.play(Create(cursor), FadeIn(pixel_label, shift=UP * 0.2),
                  run_time=1.0)
        self.wait(1.2)

        def show_pixel(y, x, slow=False):
            c = SAMPLE_IMG[y][x]
            new_color = "#" + "00" + c[3:]
            if slow:
                self.play(
                    cursor.animate.move_to(
                        original.cells[y][x].get_center()),
                    run_time=0.9,
                )
                self.wait(0.25)
                self.play(
                    new.cells[y][x].animate.set_fill(new_color, opacity=1),
                    run_time=0.7,
                )
                self.wait(0.25)
            else:
                self.play(
                    cursor.animate.move_to(
                        original.cells[y][x].get_center()),
                    new.cells[y][x].animate.set_fill(new_color, opacity=1),
                    run_time=0.45,
                )

        # First 4 pixels: slow, with pauses
        for (y, x) in [(0, 0), (0, 1), (0, 2), (0, 3)]:
            show_pixel(y, x, slow=True)

        # Remaining pixels: medium pace
        remaining = [(y, x) for y in range(original.n_rows)
                     for x in range(original.n_cols)
                     if (y, x) not in [(0, 0), (0, 1), (0, 2), (0, 3)]]
        for (y, x) in remaining:
            show_pixel(y, x, slow=False)

        self.wait(0.8)
        self.play(FadeOut(cursor), FadeOut(pixel_label), run_time=0.8)
        self.wait(0.4)

        # --- Full kein_rot code (matches vorlagen.ipynb) -------------
        # Shift grids up to make room.
        self.play(
            original.animate.shift(UP * 1.0).scale(0.8),
            lbl_in.animate.shift(UP * 1.0).scale(0.85),
            new.animate.shift(UP * 1.0).scale(0.8),
            lbl_out.animate.shift(UP * 1.0).scale(0.85),
            run_time=1.0,
        )

        block = code_block([
            "def kein_rot(bild):",
            "    hoehe = len(bild)",
            "    breite = len(bild[0])",
            "    neues_bild = []",
            "    for y in range(hoehe):",
            "        neue_zeile = []",
            "        for x in range(breite):",
            "            r, g, b = bild[y][x]",
            "            neue_zeile.append((0, g, b))",
            "        neues_bild.append(neue_zeile)",
            "    return neues_bild",
        ], size=16, line_buff=0.08).to_edge(DOWN, buff=0.4)
        block[0].set_color(MNG_BLUE_DARK)
        block[8].set_color(CINNABAR)

        self.play(Write(block), run_time=3.0)
        self.wait(4.0)


# =====================================================================
# Scene 2 — Position-first (Vorlage 2)
# =====================================================================

class PositionsFilter(Scene):
    """Vorlage 2: leeres Bild anlegen, dann jeden Pixel an eine
    moeglicherweise andere Position schreiben. Beispiel: horizontal
    spiegeln."""

    def construct(self):
        t = title_text("Vorlage 2: Position frei wählen")\
            .to_edge(UP, buff=0.4)
        sub = label("Beispiel: Bild horizontal spiegeln",
                    color=INK_SOFT, size=22).next_to(t, DOWN, buff=0.2)
        self.play(Write(t), run_time=1.2)
        self.play(FadeIn(sub, shift=DOWN * 0.2), run_time=0.8)
        self.wait(1.5)

        # Hue gradient top→bottom, saturation gradient left→right.
        # Every pixel unique — makes the horizontal swap unambiguous.
        mirror_img = build_gradient_sample(rows=4, cols=6)
        original = make_pixel_grid(mirror_img, square_size=0.55)
        new = empty_grid_like(original, fill="#222222")
        original.shift(LEFT * 3.4 + DOWN * 0.2)
        new.shift(RIGHT * 3.4 + DOWN * 0.2)

        lbl_in = label("bild", color=MNG_BLUE)\
            .next_to(original, UP, buff=0.25)
        lbl_out = label("neues_bild", color=CINNABAR)\
            .next_to(new, UP, buff=0.25)

        # Move grids up a bit so code fits below them.
        original.shift(UP * 1.1).scale(0.78)
        new.shift(UP * 1.1).scale(0.78)
        lbl_in.next_to(original, UP, buff=0.2).scale(0.9)
        lbl_out.next_to(new, UP, buff=0.2).scale(0.9)

        # --- Step 1: empty image ------------------------------------
        # Code panel centered horizontally below the grids (safe x range)
        note1 = label("Schritt 1: leeres Bild anlegen",
                      color=MNG_BLUE_DARK, size=24)
        note1.move_to([0, -1.0, 0])
        self.play(FadeIn(original, shift=UP * 0.2),
                  FadeIn(lbl_in, shift=UP * 0.2), run_time=1.0)
        self.wait(0.6)
        self.play(FadeIn(new, shift=UP * 0.2),
                  FadeIn(lbl_out, shift=UP * 0.2), run_time=1.0)
        self.wait(0.4)
        self.play(Write(note1), run_time=1.0)

        code1 = code_block([
            "neues_bild = []",
            "for y in range(hoehe):",
            "    zeile = []",
            "    for x in range(breite):",
            "        zeile.append((0, 0, 0))",
            "    neues_bild.append(zeile)",
        ], size=18, line_buff=0.10)
        code1.next_to(note1, DOWN, buff=0.3)
        self.play(Write(code1), run_time=2.5)
        self.wait(2.5)

        # --- Step 2: per pixel, draw an arrow to the mirrored x -----
        note2 = label("Schritt 2: Pixel platzieren (gespiegelt)",
                      color=MNG_BLUE_DARK, size=24)
        note2.move_to(note1)

        code2 = code_block([
            "for y in range(hoehe):",
            "    for x in range(breite):",
            "        neuer_pixel = bild[y][x]",
            "        neues_bild[y][breite - 1 - x] \\",
            "            = neuer_pixel",
        ], size=18, line_buff=0.10)
        code2[3].set_color(CINNABAR)
        code2[4].set_color(CINNABAR)
        code2.next_to(note2, DOWN, buff=0.3)

        self.play(
            FadeOut(note1),
            FadeOut(code1),
            run_time=0.8,
        )
        self.play(FadeIn(note2), Write(code2), run_time=2.0)
        self.wait(1.5)

        cols = original.n_cols

        def show_mirror(y, x, slow=False):
            src = original.cells[y][x]
            dst = new.cells[y][cols - 1 - x]
            arrow = CurvedArrow(
                src.get_center(),
                dst.get_center(),
                color=CINNABAR,
                stroke_width=3,
                angle=-PI / 4,
            )
            if slow:
                self.play(Create(arrow), run_time=0.9)
                self.wait(0.25)
                self.play(
                    dst.animate.set_fill(mirror_img[y][x], opacity=1),
                    run_time=0.7,
                )
                self.wait(0.2)
                self.play(FadeOut(arrow), run_time=0.4)
            else:
                self.play(Create(arrow), run_time=0.4)
                self.play(
                    dst.animate.set_fill(mirror_img[y][x], opacity=1),
                    run_time=0.4,
                )
                self.play(FadeOut(arrow), run_time=0.25)

        # First 3 pixels: slow
        for (y, x) in [(0, 0), (0, 1), (0, 2)]:
            show_mirror(y, x, slow=True)

        # Remaining: medium
        remaining = [(y, x) for y in range(original.n_rows)
                     for x in range(original.n_cols)
                     if (y, x) not in [(0, 0), (0, 1), (0, 2)]]
        for (y, x) in remaining:
            show_mirror(y, x, slow=False)

        self.wait(2.0)


# =====================================================================
# Scene 3 — Box-Blur (Nachbarn mischen)
# =====================================================================

class BoxBlur(Scene):
    """Box-Blur über RGB-Pixel:
      Phase 1: zwei Pixel von Hand aufgelistet, mit summe_r / _g / _b.
      Phase 2: dasselbe mit doppelter for-Schleife über [-1, 0, 1]."""

    def construct(self):
        t = title_text("Nachbarn mischen: Box-Blur").to_edge(UP, buff=0.4)
        self.play(Write(t), run_time=1.2)
        self.wait(1.0)

        # --- RGB grid (random colors with R, G, B in [80, 220]) -----
        rng = np.random.default_rng(7)
        rgb_vals = rng.integers(80, 220, size=(5, 5, 3))
        rgb_hex = [
            ["#{:02x}{:02x}{:02x}".format(*rgb_vals[y, x])
             for x in range(5)]
            for y in range(5)
        ]
        grid = make_pixel_grid(rgb_hex, square_size=0.9)
        grid.shift(LEFT * 3.3 + DOWN * 0.3)
        self.play(FadeIn(grid), run_time=1.2)
        self.wait(1.0)

        cy, cx = 2, 2
        center_box = Square(side_length=0.93, stroke_color=CINNABAR,
                            stroke_width=6, fill_opacity=0)
        center_box.move_to(grid.cells[cy][cx].get_center())
        center_label = Text("bild[y][x]", font="JetBrains Mono",
                            font_size=20, color=CINNABAR)
        center_label.next_to(grid, DOWN, buff=0.4)
        self.play(Create(center_box), Write(center_label), run_time=1.2)
        self.wait(1.5)

        # --- Compute the averaged centre pixel ----------------------
        nb = rgb_vals[cy - 1:cy + 2, cx - 1:cx + 2]
        avg_r = int(nb[:, :, 0].mean())
        avg_g = int(nb[:, :, 1].mean())
        avg_b = int(nb[:, :, 2].mean())
        neu_hex = "#{:02x}{:02x}{:02x}".format(avg_r, avg_g, avg_b)

        # --- PHASE 1: explicit example (first two pixels) -----------
        phase_label = label("Phase 1: jeden Pixel von Hand",
                            color=MNG_BLUE_DARK, size=24)
        phase_label.to_edge(UP, buff=1.2).shift(RIGHT * 3.2)
        self.play(FadeIn(phase_label, shift=LEFT * 0.3), run_time=1.0)
        self.wait(0.8)

        explicit_block = code_block([
            "r, g, b = bild[y-1][x-1]",
            "summe_r = r",
            "summe_g = g",
            "summe_b = b",
            "",
            "r, g, b = bild[y-1][x]",
            "summe_r += r",
            "summe_g += g",
            "summe_b += b",
            "",
            "# ... das gleiche für 7 weitere Pixel",
            "",
            "neu = (summe_r // 9,",
            "       summe_g // 9,",
            "       summe_b // 9)",
        ], size=15, line_buff=0.06)
        explicit_block.next_to(phase_label, DOWN, buff=0.30,
                               aligned_edge=LEFT)
        self.play(FadeIn(explicit_block, shift=UP * 0.2), run_time=1.5)
        self.wait(1.0)

        # First two neighbours: slow, in sync with the visible code blocks
        neighbors = [
            (cy - 1, cx - 1), (cy - 1, cx), (cy - 1, cx + 1),
            (cy,     cx - 1), (cy,     cx), (cy,     cx + 1),
            (cy + 1, cx - 1), (cy + 1, cx), (cy + 1, cx + 1),
        ]
        code_blocks = [
            list(range(0, 4)),   # first pixel: lines 0-3
            list(range(5, 9)),   # second pixel: lines 5-8
        ]
        for i in range(2):
            ny, nx = neighbors[i]
            cell = grid.cells[ny][nx]
            self.play(
                cell.animate.set_stroke(CINNABAR, width=5),
                *[explicit_block[j].animate.set_color(INK)
                  for j in code_blocks[i]],
                run_time=0.7,
            )
            self.wait(0.5)
            self.play(cell.animate.set_stroke(WHITE, width=2),
                      run_time=0.25)

        # Remaining 7 cells: quick sweep while the "..." line is highlighted
        ellipsis_line = explicit_block[10]
        self.play(ellipsis_line.animate.set_color(CINNABAR), run_time=0.4)
        for i in range(2, 9):
            ny, nx = neighbors[i]
            cell = grid.cells[ny][nx]
            self.play(
                cell.animate.set_stroke(CINNABAR, width=5),
                run_time=0.30,
            )
            self.play(cell.animate.set_stroke(WHITE, width=2),
                      run_time=0.20)
        self.play(ellipsis_line.animate.set_color(INK_SOFT), run_time=0.4)

        # Highlight the result lines + show the new colour right inside
        # the centre cell (the box-blur output) without leaving the
        # screen.
        original_centre_color = rgb_hex[cy][cx]
        self.play(
            explicit_block[12].animate.set_color(MNG_BLUE_DARK),
            explicit_block[13].animate.set_color(MNG_BLUE_DARK),
            explicit_block[14].animate.set_color(MNG_BLUE_DARK),
            grid.cells[cy][cx].animate.set_fill(neu_hex, opacity=1),
            run_time=1.0,
        )
        self.wait(2.5)

        # --- Transition ---------------------------------------------
        transition = label("Geht das kürzer?",
                           color=CINNABAR, size=28)
        transition.to_edge(DOWN, buff=0.6)
        self.play(Write(transition), run_time=1.2)
        self.wait(2.0)

        self.play(
            FadeOut(phase_label),
            FadeOut(explicit_block),
            FadeOut(transition),
            # Reset the centre cell so Phase 2 demonstrates it again.
            grid.cells[cy][cx].animate.set_fill(original_centre_color,
                                                opacity=1),
            run_time=1.0,
        )
        self.wait(0.5)

        # --- PHASE 2: double for-loop -------------------------------
        phase2_label = label("Phase 2: doppelte for-Schleife",
                             color=MNG_BLUE_DARK, size=24)
        phase2_label.to_edge(UP, buff=1.2).shift(RIGHT * 3.2)
        self.play(FadeIn(phase2_label, shift=LEFT * 0.3), run_time=1.0)
        self.wait(0.5)

        loop_block = code_block([
            "summe_r = 0",
            "summe_g = 0",
            "summe_b = 0",
            "",
            "für dz in [-1, 0, 1]:",
            "    für ds in [-1, 0, 1]:",
            "        r, g, b = bild[y+dz][x+ds]",
            "        summe_r += r",
            "        summe_g += g",
            "        summe_b += b",
            "",
            "neu = (summe_r // 9,",
            "       summe_g // 9,",
            "       summe_b // 9)",
        ], size=15, line_buff=0.08)
        loop_block.next_to(phase2_label, DOWN, buff=0.30, aligned_edge=LEFT)
        self.play(FadeIn(loop_block, shift=UP * 0.2), run_time=1.5)
        self.wait(2.0)

        # Live tracker
        dz_tracker = Text("dz = ?", font="JetBrains Mono",
                          font_size=20, color=CINNABAR)
        ds_tracker = Text("ds = ?", font="JetBrains Mono",
                          font_size=20, color=CINNABAR)
        tracker = VGroup(dz_tracker, ds_tracker)\
            .arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        tracker.next_to(loop_block, DOWN, buff=0.35, aligned_edge=LEFT)
        self.play(FadeIn(tracker), run_time=0.8)
        self.wait(0.6)

        def fmt(name, val):
            sign = " " if val >= 0 else ""
            return f"{name} = {sign}{val}"

        for dz in [-1, 0, 1]:
            new_dz = Text(fmt("dz", dz), font="JetBrains Mono",
                          font_size=20, color=CINNABAR)
            new_dz.move_to(dz_tracker, aligned_edge=LEFT)
            self.play(Transform(dz_tracker, new_dz), run_time=0.5)
            self.wait(0.2)
            for ds in [-1, 0, 1]:
                new_ds = Text(fmt("ds", ds), font="JetBrains Mono",
                              font_size=20, color=CINNABAR)
                new_ds.move_to(ds_tracker, aligned_edge=LEFT)
                ny, nx = cy + dz, cx + ds
                cell = grid.cells[ny][nx]
                self.play(
                    Transform(ds_tracker, new_ds),
                    cell.animate.set_stroke(CINNABAR, width=5),
                    run_time=0.55,
                )
                self.wait(0.3)
                self.play(
                    cell.animate.set_stroke(WHITE, width=2),
                    run_time=0.2,
                )

        self.wait(0.8)

        # Same result: animate the centre cell to the blurred colour.
        self.play(
            grid.cells[cy][cx].animate.set_fill(neu_hex, opacity=1),
            run_time=1.0,
        )
        self.wait(1.5)

        msg = label("Gleiches Ergebnis, viel weniger Code.",
                    color=CINNABAR, size=26)
        msg.to_edge(DOWN, buff=0.4)
        self.play(Write(msg), run_time=1.5)
        self.wait(3.5)


# =====================================================================
# Scene 4 — Video pipeline
# =====================================================================

class VideoPipeline(Scene):
    """bearbeite_video: load, split into frames, filter each, reassemble."""

    def construct(self):
        t = title_text("Video filtern: Frame für Frame")\
            .to_edge(UP, buff=0.4)
        self.play(Write(t), run_time=1.2)
        self.wait(1.2)

        # --- Filmstrips ----------------------------------------------
        in_label = label("Eingabevideo", color=MNG_BLUE, size=24)
        out_label = label("Gefiltertes Video", color=CINNABAR, size=24)

        def make_filmstrip(palette, n=5, frame_size=1.2):
            strip = VGroup()
            for i in range(n):
                f = Rectangle(width=frame_size, height=frame_size * 0.7)
                f.set_fill(palette[i % len(palette)], opacity=1)
                f.set_stroke(INK, width=2)
                perf_top = VGroup(*[
                    Square(side_length=0.08).set_fill(INK, opacity=1)
                                            .set_stroke(width=0)
                    for _ in range(4)
                ]).arrange(RIGHT, buff=0.18)
                perf_top.scale(0.6).next_to(f, UP, buff=0.05)
                perf_bot = perf_top.copy().next_to(f, DOWN, buff=0.05)
                cell = VGroup(f, perf_top, perf_bot)
                strip.add(cell)
            strip.arrange(RIGHT, buff=0.08)
            return strip

        in_strip = make_filmstrip(["#FFD89B", "#FFC93C", "#9AAEC8",
                                   "#6E83A3", "#5C7B4F"])
        in_strip.shift(UP * 1.7)
        in_label.next_to(in_strip, UP, buff=0.25)
        self.play(FadeIn(in_strip, shift=DOWN * 0.2),
                  Write(in_label), run_time=1.4)
        self.wait(1.5)

        # --- Filter box in the middle --------------------------------
        filter_box = RoundedRectangle(
            width=3.0, height=1.3, corner_radius=0.15,
            stroke_color=CINNABAR, stroke_width=4,
        ).set_fill(MNG_BLUE_LIGHT, opacity=0.25)
        filter_label = Text("filter_funktion", font="JetBrains Mono",
                            font_size=22, color=MNG_BLUE_DARK)
        filter_label.move_to(filter_box)
        filter_group = VGroup(filter_box, filter_label)
        filter_group.move_to(ORIGIN + DOWN * 0.3)
        self.play(FadeIn(filter_group, shift=UP * 0.2), run_time=1.2)
        self.wait(1.0)

        # --- Output filmstrip (empty) --------------------------------
        out_strip = make_filmstrip(["#222222"] * 5).shift(DOWN * 2.4)
        out_label.next_to(out_strip, DOWN, buff=0.25)
        self.play(FadeIn(out_strip), Write(out_label), run_time=1.2)
        self.wait(1.5)

        # --- Each frame travels through filter -----------------------
        in_palette = ["#FFD89B", "#FFC93C", "#9AAEC8", "#6E83A3", "#5C7B4F"]
        out_palette = ["#" + "00" + c[3:] for c in in_palette]

        for i in range(5):
            in_cell = in_strip[i]
            out_cell = out_strip[i]

            traveler = in_cell.copy()
            self.play(
                traveler.animate.move_to(filter_box.get_center()),
                run_time=0.9,
            )
            traveler[0].set_fill(out_palette[i], opacity=1)
            self.play(filter_box.animate.set_stroke(width=7), run_time=0.2)
            self.play(filter_box.animate.set_stroke(width=4), run_time=0.2)
            self.play(
                traveler.animate.move_to(out_cell.get_center()),
                out_cell[0].animate.set_fill(out_palette[i], opacity=1),
                run_time=0.9,
            )
            self.remove(traveler)
            self.wait(0.3)

        self.wait(1.2)
        msg = label("Jedes Frame wird einzeln gefiltert.",
                    color=INK_SOFT, size=22)
        msg.to_edge(DOWN, buff=0.15)
        # If out_label is at buff 0.25 from out_strip bottom, msg should
        # not overlap; check by placing msg below out_label.
        msg.next_to(out_label, DOWN, buff=0.15)
        self.play(Write(msg), run_time=1.5)
        self.wait(3.5)
