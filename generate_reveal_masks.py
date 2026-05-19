"""Generate per-color reveal masks for the paint-by-numbers website.

Algorithm (region-based, paint-by-numbers exact):
  1. Quantise design-preview.jpg into 20 colors (the palette).
  2. Identify region interiors in canvas.png via threshold + connected
     components — each numbered region becomes one connected blob.
  3. For each region, look up the most common quantised color among the
     pixels of design-preview.jpg under that region. That tells us which
     of the 20 colors the region should be painted with.
  4. Group regions by colour index. Each group becomes one reveal mask
     (RGBA PNG, opaque only on the pixels of regions that get that colour).

The result: reveals fill canvas regions EXACTLY, leaving outlines and
number labels untouched.

Run once after changing the design or canvas image:
    python generate_reveal_masks.py
"""
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).parent
DESIGN = HERE / "design-preview.jpg"
OUT_DIR = HERE / "stempel-wanderung" / "static"
CANVAS = OUT_DIR / "canvas.png"

N_COLORS = 20
# Canvas pixels DARKER than this are outline/number ink. Anti-aliasing
# means edges fade gradually; pick a threshold that catches the faded
# outer pixels of each stroke so dilation can close small gaps.
OUTLINE_THRESHOLD = 240
# Iterations of binary dilation on the outline mask before flood-fill.
# Each iteration grows the outline by one pixel in every direction,
# closing thin gaps that would otherwise leak between regions.
OUTLINE_DILATION = 1
# Skip connected components smaller than this many pixels.
MIN_REGION_PIXELS = 8


def main():
    # ---- Palette: quantise design-preview to 20 colors ---------------
    design = Image.open(DESIGN).convert("RGB")
    quantized = design.quantize(
        colors=N_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    palette_bytes = quantized.getpalette()
    palette = [
        (palette_bytes[i * 3],
         palette_bytes[i * 3 + 1],
         palette_bytes[i * 3 + 2])
        for i in range(N_COLORS)
    ]
    design_indices = np.array(quantized)
    h, w = design_indices.shape

    # ---- Regions: dilate outlines to close gaps, then label ----------
    canvas_l = np.array(Image.open(CANVAS).convert("L").resize((w, h)))
    is_outline = canvas_l < OUTLINE_THRESHOLD
    if OUTLINE_DILATION > 0:
        is_outline = ndimage.binary_dilation(
            is_outline, iterations=OUTLINE_DILATION
        )
    interior = ~is_outline
    labels, n_components = ndimage.label(interior)
    print(f"Canvas: {n_components} raw connected components "
          f"(outline dilated by {OUTLINE_DILATION}px).")

    # ---- For each region, pick the most common palette index ---------
    region_color = {}  # region_id -> palette index 0..19
    region_sizes = ndimage.sum(interior, labels, range(1, n_components + 1))
    for region_id in range(1, n_components + 1):
        if region_sizes[region_id - 1] < MIN_REGION_PIXELS:
            continue
        region_pixels = labels == region_id
        # Most common quantised colour under this region
        counts = np.bincount(
            design_indices[region_pixels], minlength=N_COLORS
        )
        region_color[region_id] = int(counts.argmax())

    print(f"  {len(region_color)} regions large enough to colour.")

    # ---- Build the 20 reveal masks ----------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    color_to_regions = Counter()
    for region_id, color_id in region_color.items():
        color_to_regions[color_id] += 1

    print(f"{'#':>3}  {'Color':>15}  {'Regions':>8}  {'Pixels':>10}  {'KB':>6}")
    for color_id in range(N_COLORS):
        # Build a binary mask of all regions assigned to this color
        mask = np.zeros((h, w), dtype=bool)
        for region_id, c in region_color.items():
            if c == color_id:
                mask |= labels == region_id

        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        r, g, b = palette[color_id]
        rgba[mask, 0] = r
        rgba[mask, 1] = g
        rgba[mask, 2] = b
        rgba[mask, 3] = 255

        out_path = OUT_DIR / f"reveal_{color_id + 1:02d}.png"
        Image.fromarray(rgba, "RGBA").save(out_path, optimize=True)
        sz = out_path.stat().st_size / 1024
        print(f"{color_id + 1:>3}  rgb{palette[color_id]!s:>13}  "
              f"{color_to_regions[color_id]:>8}  {int(mask.sum()):>10}  "
              f"{sz:>6.1f}")


if __name__ == "__main__":
    main()
