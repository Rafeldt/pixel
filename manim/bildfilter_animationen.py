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

Render all scenes at preview quality:
    manim -ql bildfilter_animationen.py
"""
from manim import *
import numpy as np

# =====================================================================
# Style: matches the MNG skript and pixel.rafeldt.ch aesthetic.
# =====================================================================
MNG_BLUE       = "#0076BD"
MNG_BLUE_DARK  = "#003C64"
MNG_BLUE_LIGHT = "#99C8E5"
CINNABAR       = "#B1382E"
PAPER          = "#FAF6EE"
INK            = "#2A2118"
INK_SOFT       = "#6B5F4F"

config.background_color = PAPER

# Sample 4x6 image (rows x cols): sky over a mountain ridge.
SAMPLE_IMG = [
    ["#FFD89B", "#FFD89B", "#FFC93C", "#FFC93C", "#FFD89B", "#FFD89B"],
    ["#FFD89B", "#FFE8C8", "#FFFFFF", "#FFFFFF", "#FFD89B", "#FFD89B"],
    ["#9AAEC8", "#9AAEC8", "#FFFFFF", "#FFFFFF", "#6E83A3", "#6E83A3"],
    ["#5C7B4F", "#5C7B4F", "#6E8B5A", "#6E8B5A", "#4A7BA0", "#4A7BA0"],
]


# =====================================================================
# Helpers
# =====================================================================

def make_pixel_grid(colors, square_size=0.55, stroke_color=WHITE, stroke_width=2):
    """Return a VGroup of coloured squares laid out as a 2D pixel grid.

    `colors[y][x]` is the colour of the pixel at row y, column x.
    The group is centred at the origin; access individual cells via
    group.cells[y][x].
    """
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
    """A same-shape grid with every cell painted `fill`."""
    rows, cols = grid.n_rows, grid.n_cols
    return make_pixel_grid([[fill] * cols for _ in range(rows)])


def title_text(text, color=MNG_BLUE_DARK):
    return Text(text, color=color, font_size=40, weight=BOLD)


def label(text, color=INK, size=22):
    return Text(text, color=color, font_size=size)


def code_line(text, color=INK):
    return Text(text, color=color, font="JetBrains Mono", font_size=22)


# =====================================================================
# Scene 1 — Pixel-für-Pixel (Vorlage 1)
# =====================================================================

class PixelFilter(Scene):
    """Vorlage 1: each new pixel depends only on the SAME pixel in the
    original image. Walked through with kein_rot as the example."""

    def construct(self):
        # --- Title --------------------------------------------------
        t = title_text("Vorlage 1: Pixel für Pixel").to_edge(UP)
        sub = label("Beispiel: kein_rot — der Rotwert wird 0",
                    color=INK_SOFT, size=22).next_to(t, DOWN, buff=0.15)
        self.play(Write(t), FadeIn(sub, shift=DOWN * 0.2))
        self.wait(0.5)

        # --- Build the two grids ------------------------------------
        original = make_pixel_grid(SAMPLE_IMG, square_size=0.55)
        new = empty_grid_like(original, fill="#222222")

        original.shift(LEFT * 3.5 + DOWN * 0.3)
        new.shift(RIGHT * 3.5 + DOWN * 0.3)

        lbl_in = label("bild (Original)", color=MNG_BLUE)\
            .next_to(original, UP, buff=0.2)
        lbl_out = label("neues_bild", color=CINNABAR)\
            .next_to(new, UP, buff=0.2)

        self.play(FadeIn(original, lbl_in), FadeIn(new, lbl_out))
        self.wait(0.4)

        # --- A "reading cursor" walks the original ------------------
        cursor = Square(side_length=0.62, stroke_color=CINNABAR,
                        stroke_width=5, fill_opacity=0)
        cursor.move_to(original.cells[0][0].get_center())

        # Pixel value readout
        pixel_label = label("(r, g, b)").to_edge(DOWN, buff=0.6)
        self.play(Create(cursor), FadeIn(pixel_label, shift=UP * 0.2))

        def pixel_color(y, x):
            return SAMPLE_IMG[y][x]

        def show_pixel(y, x, fast=False):
            """Animate: highlight (y,x), 'remove red', paint output."""
            c = pixel_color(y, x)
            new_color = "#" + "00" + c[3:]  # zero out the red byte
            if fast:
                self.play(
                    cursor.animate.move_to(original.cells[y][x].get_center()),
                    new.cells[y][x].animate.set_fill(new_color, opacity=1),
                    run_time=0.18,
                )
            else:
                self.play(
                    cursor.animate.move_to(original.cells[y][x].get_center()),
                    run_time=0.4,
                )
                self.play(
                    new.cells[y][x].animate.set_fill(new_color, opacity=1),
                    run_time=0.4,
                )

        # First three pixels: animated slowly with explanation
        for (y, x) in [(0, 0), (0, 1), (0, 2)]:
            show_pixel(y, x, fast=False)

        # The rest: fast sweep
        for y in range(original.n_rows):
            for x in range(original.n_cols):
                if (y, x) in [(0, 0), (0, 1), (0, 2)]:
                    continue
                show_pixel(y, x, fast=True)

        self.play(FadeOut(cursor), FadeOut(pixel_label))
        self.wait(0.5)

        # --- Show the pattern as pseudocode -------------------------
        block = VGroup(
            code_line("für jede Zeile y des Bildes:"),
            code_line("    für jede Spalte x:"),
            code_line("        r, g, b = bild[y][x]"),
            code_line("        neues_bild[y][x] = (0, g, b)"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.5)

        self.play(Write(block))
        self.wait(2.5)


# =====================================================================
# Scene 2 — Position-first (Vorlage 2)
# =====================================================================

class PositionsFilter(Scene):
    """Vorlage 2: build an empty new image, then write each input pixel
    to a (possibly different) output position. Demonstrated with a
    horizontal mirror."""

    def construct(self):
        t = title_text("Vorlage 2: Position frei wählen").to_edge(UP)
        sub = label("Beispiel: Bild horizontal spiegeln",
                    color=INK_SOFT, size=22).next_to(t, DOWN, buff=0.15)
        self.play(Write(t), FadeIn(sub, shift=DOWN * 0.2))
        self.wait(0.4)

        original = make_pixel_grid(SAMPLE_IMG, square_size=0.55)
        new = empty_grid_like(original, fill="#222222")
        original.shift(LEFT * 3.5 + DOWN * 0.3)
        new.shift(RIGHT * 3.5 + DOWN * 0.3)

        lbl_in = label("bild", color=MNG_BLUE).next_to(original, UP, buff=0.2)
        lbl_out = label("neues_bild", color=CINNABAR)\
            .next_to(new, UP, buff=0.2)
        note = label("Schritt 1: leeres Bild anlegen (alles schwarz)",
                     color=INK_SOFT, size=20).to_edge(DOWN, buff=0.6)

        self.play(FadeIn(original, lbl_in))
        self.play(FadeIn(new, lbl_out), Write(note))
        self.wait(0.6)

        # --- Step 2: per pixel, draw an arrow to the mirrored x -----
        self.play(FadeOut(note))
        note2 = label("Schritt 2: jeden Pixel an die "
                      "gespiegelte Stelle schreiben",
                      color=INK_SOFT, size=20).to_edge(DOWN, buff=0.6)
        self.play(FadeIn(note2))

        cols = original.n_cols

        def show_mirror(y, x, fast=False):
            src = original.cells[y][x]
            dst = new.cells[y][cols - 1 - x]
            arrow = CurvedArrow(
                src.get_center(),
                dst.get_center(),
                color=CINNABAR,
                stroke_width=3,
                angle=-PI / 4,
            )
            if fast:
                self.play(
                    Create(arrow),
                    dst.animate.set_fill(SAMPLE_IMG[y][x], opacity=1),
                    run_time=0.25,
                )
                self.play(FadeOut(arrow), run_time=0.1)
            else:
                self.play(Create(arrow), run_time=0.5)
                self.play(
                    dst.animate.set_fill(SAMPLE_IMG[y][x], opacity=1),
                    run_time=0.35,
                )
                self.play(FadeOut(arrow), run_time=0.25)

        # First two pixels: slow
        for (y, x) in [(0, 0), (0, 1)]:
            show_mirror(y, x, fast=False)

        # Rest: fast
        for y in range(original.n_rows):
            for x in range(original.n_cols):
                if (y, x) in [(0, 0), (0, 1)]:
                    continue
                show_mirror(y, x, fast=True)

        self.play(FadeOut(note2))

        block = VGroup(
            code_line("für jede Zeile y:"),
            code_line("    für jede Spalte x:"),
            code_line("        neues_bild[y][breite - 1 - x] = bild[y][x]"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.5)
        self.play(Write(block))
        self.wait(2.5)


# =====================================================================
# Scene 3 — Box-Blur (Nachbarn mischen)
# =====================================================================

class BoxBlur(Scene):
    """Box-Blur in zwei Phasen:
      Phase 1: alle 9 Pixel von Hand aufgelistet.
      Phase 2: dasselbe mit einer doppelten for-Schleife über [-1, 0, 1]."""

    def construct(self):
        t = title_text("Nachbarn mischen — Box-Blur").to_edge(UP)
        self.play(Write(t))
        self.wait(0.3)

        # --- Setup grid ------------------------------------------------
        rng = np.random.default_rng(7)
        vals = rng.integers(80, 220, size=(5, 5))
        gray = [[f"#{v:02x}{v:02x}{v:02x}" for v in row] for row in vals]
        grid = make_pixel_grid(gray, square_size=0.85)
        grid.shift(LEFT * 3.2 + DOWN * 0.2)

        nums = VGroup()
        for y in range(5):
            for x in range(5):
                col = WHITE if vals[y, x] < 140 else BLACK
                t_ = Text(str(int(vals[y, x])), font_size=18, color=col,
                          weight=BOLD)
                t_.move_to(grid.cells[y][x].get_center())
                nums.add(t_)
        self.play(FadeIn(grid), Write(nums))
        self.wait(0.2)

        # Central pixel coords
        cy, cx = 2, 2

        center_box = Square(side_length=0.88, stroke_color=CINNABAR,
                            stroke_width=6, fill_opacity=0)
        center_box.move_to(grid.cells[cy][cx].get_center())
        center_label = Text("bild[y][x]", font="JetBrains Mono",
                            font_size=18, color=CINNABAR)
        center_label.next_to(grid, DOWN, buff=0.35)
        self.play(Create(center_box), Write(center_label))
        self.wait(0.5)

        # --- PHASE 1: 9 explicit accesses ------------------------------
        phase_label = label("Phase 1: alle 9 Pixel von Hand",
                            color=MNG_BLUE_DARK, size=22)
        phase_label.to_edge(UP, buff=1.1).shift(RIGHT * 3.0)
        self.play(FadeIn(phase_label, shift=LEFT * 0.3))

        explicit_lines = [
            "summe  = bild[y-1][x-1]",
            "summe += bild[y-1][x]",
            "summe += bild[y-1][x+1]",
            "summe += bild[y][x-1]",
            "summe += bild[y][x]",
            "summe += bild[y][x+1]",
            "summe += bild[y+1][x-1]",
            "summe += bild[y+1][x]",
            "summe += bild[y+1][x+1]",
        ]
        explicit_block = VGroup(*[
            Text(c, font="JetBrains Mono", font_size=15, color=INK_SOFT)
            for c in explicit_lines
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        explicit_block.next_to(phase_label, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(FadeIn(explicit_block, shift=UP * 0.2))

        neighbors = [
            (cy - 1, cx - 1), (cy - 1, cx), (cy - 1, cx + 1),
            (cy,     cx - 1), (cy,     cx), (cy,     cx + 1),
            (cy + 1, cx - 1), (cy + 1, cx), (cy + 1, cx + 1),
        ]
        for i, (ny, nx) in enumerate(neighbors):
            cell = grid.cells[ny][nx]
            cline = explicit_block[i]
            self.play(
                cell.animate.set_stroke(CINNABAR, width=5),
                cline.animate.set_color(INK).set_opacity(1.0),
                run_time=0.28,
            )
            self.wait(0.08)
            self.play(
                cell.animate.set_stroke(WHITE, width=2),
                run_time=0.12,
            )

        # Show the average
        center_val = int(vals[cy - 1:cy + 2, cx - 1:cx + 2].mean())
        result_line = Text(f"neu = summe // 9 = {center_val}",
                           font="JetBrains Mono", font_size=18,
                           color=MNG_BLUE_DARK, weight=BOLD)
        result_line.next_to(explicit_block, DOWN, buff=0.25, aligned_edge=LEFT)
        self.play(Write(result_line))
        self.wait(1.5)

        # --- Transition ----------------------------------------------
        transition = label("Geht das kürzer?",
                           color=CINNABAR, size=26)
        transition.to_edge(DOWN, buff=0.6)
        self.play(Write(transition))
        self.wait(1.0)

        self.play(
            FadeOut(phase_label),
            FadeOut(explicit_block),
            FadeOut(result_line),
            FadeOut(transition),
        )

        # --- PHASE 2: double for-loop --------------------------------
        phase2_label = label("Phase 2: doppelte for-Schleife",
                             color=MNG_BLUE_DARK, size=22)
        phase2_label.to_edge(UP, buff=1.1).shift(RIGHT * 3.0)
        self.play(FadeIn(phase2_label, shift=LEFT * 0.3))

        loop_lines = [
            "summe = 0",
            "für dz in [-1, 0, 1]:",
            "    für ds in [-1, 0, 1]:",
            "        summe += bild[y+dz][x+ds]",
            "",
            "neu = summe // 9",
        ]
        loop_block = VGroup(*[
            Text(c if c else " ", font="JetBrains Mono",
                 font_size=18, color=INK)
            for c in loop_lines
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        loop_block.next_to(phase2_label, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(FadeIn(loop_block, shift=UP * 0.2))
        self.wait(0.3)

        # Live loop-state tracker under the loop block
        dz_tracker = Text("dz = ?", font="JetBrains Mono",
                          font_size=20, color=CINNABAR)
        ds_tracker = Text("ds = ?", font="JetBrains Mono",
                          font_size=20, color=CINNABAR)
        tracker = VGroup(dz_tracker, ds_tracker)\
            .arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        tracker.next_to(loop_block, DOWN, buff=0.4, aligned_edge=LEFT)
        self.play(FadeIn(tracker))

        for dz in [-1, 0, 1]:
            new_dz = Text(f"dz = {dz:+d}".replace("+", " ").replace(" -1", "-1")
                          if dz != 0 else "dz =  0",
                          font="JetBrains Mono", font_size=20, color=CINNABAR)
            new_dz.move_to(dz_tracker)
            self.play(Transform(dz_tracker, new_dz), run_time=0.25)
            for ds in [-1, 0, 1]:
                new_ds = Text(f"ds = {ds:+d}".replace("+", " ")
                              .replace(" -1", "-1")
                              if ds != 0 else "ds =  0",
                              font="JetBrains Mono", font_size=20,
                              color=CINNABAR)
                new_ds.move_to(ds_tracker)
                ny, nx = cy + dz, cx + ds
                cell = grid.cells[ny][nx]
                self.play(
                    Transform(ds_tracker, new_ds),
                    cell.animate.set_stroke(CINNABAR, width=5),
                    run_time=0.28,
                )
                self.wait(0.08)
                self.play(
                    cell.animate.set_stroke(WHITE, width=2),
                    run_time=0.12,
                )

        result_line2 = Text(f"neu = {center_val}",
                            font="JetBrains Mono", font_size=22,
                            color=MNG_BLUE_DARK, weight=BOLD)
        result_line2.next_to(tracker, DOWN, buff=0.3, aligned_edge=LEFT)
        self.play(Write(result_line2))
        self.wait(0.5)

        msg = label("Gleicher Wert, viel weniger Code.",
                    color=CINNABAR, size=24)
        msg.to_edge(DOWN, buff=0.3)
        self.play(Write(msg))
        self.wait(2.0)


# =====================================================================
# Scene 4 — Video pipeline
# =====================================================================

class VideoPipeline(Scene):
    """bearbeite_video: load → split into frames → filter each → reassemble."""

    def construct(self):
        t = title_text("Video filtern — Frame für Frame").to_edge(UP)
        self.play(Write(t))
        self.wait(0.3)

        # --- Input filmstrip ----------------------------------------
        in_label = label("Eingabevideo", color=MNG_BLUE, size=22)
        out_label = label("Gefiltertes Video", color=CINNABAR, size=22)

        def make_filmstrip(palette, n=5, frame_size=1.2):
            strip = VGroup()
            for i in range(n):
                f = Rectangle(width=frame_size, height=frame_size * 0.7)
                f.set_fill(palette[i % len(palette)], opacity=1)
                f.set_stroke(INK, width=2)
                # perforations
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
        in_strip.shift(UP * 1.6)
        in_label.next_to(in_strip, UP, buff=0.2)
        self.play(FadeIn(in_strip, shift=DOWN * 0.2), Write(in_label))
        self.wait(0.3)

        # --- Filter box in the middle -------------------------------
        filter_box = RoundedRectangle(
            width=3.0, height=1.3, corner_radius=0.15,
            stroke_color=CINNABAR, stroke_width=4,
        ).set_fill(MNG_BLUE_LIGHT, opacity=0.25)
        filter_label = Text("filter_funktion", font="JetBrains Mono",
                            font_size=22, color=MNG_BLUE_DARK)
        filter_label.move_to(filter_box)
        filter_group = VGroup(filter_box, filter_label)
        filter_group.move_to(ORIGIN + DOWN * 0.2)
        self.play(FadeIn(filter_group, shift=UP * 0.2))
        self.wait(0.3)

        # --- Output filmstrip (empty) -------------------------------
        out_strip = make_filmstrip(["#222222"] * 5).shift(DOWN * 2.0)
        out_label.next_to(out_strip, DOWN, buff=0.2)
        self.play(FadeIn(out_strip), Write(out_label))

        # --- Animate one frame at a time travelling through filter --
        # Map each input frame to its filtered colour (kein_rot ish: zero R)
        in_palette = ["#FFD89B", "#FFC93C", "#9AAEC8", "#6E83A3", "#5C7B4F"]
        # zero the R byte
        out_palette = ["#" + "00" + c[3:] for c in in_palette]

        for i in range(5):
            in_cell = in_strip[i]
            out_cell = out_strip[i]

            # Float a copy of the frame through the filter
            traveler = in_cell.copy()
            self.play(
                traveler.animate.move_to(filter_box.get_center()),
                run_time=0.45,
            )
            # Recolour inside the filter
            traveler[0].set_fill(out_palette[i], opacity=1)
            self.play(filter_box.animate.set_stroke(width=6), run_time=0.1)
            self.play(filter_box.animate.set_stroke(width=4), run_time=0.1)
            # Drop it into the output strip
            self.play(
                traveler.animate.move_to(out_cell.get_center()),
                out_cell[0].animate.set_fill(out_palette[i], opacity=1),
                run_time=0.45,
            )
            self.remove(traveler)

        self.wait(0.5)
        msg = label("60 Frames pro Sekunde · jedes Frame ein Bild",
                    color=INK_SOFT, size=22)
        msg.to_edge(DOWN, buff=0.4)
        self.play(Write(msg))
        self.wait(2.0)
