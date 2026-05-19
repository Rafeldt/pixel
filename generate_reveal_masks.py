"""Generate per-color reveal masks for the paint-by-numbers website.

Algorithm:
  1. Quantise design-preview.jpg into 20 colors (the palette).
  2. Detect the outline NETWORK on canvas.png by taking all "dark"
     pixels (brightness < OUTLINE_DETECT_THRESHOLD) and finding the
     single largest 8-connected component. Number labels are smaller
     dark blobs that are NOT in this component.
  3. Label region interiors as connected components of "everything that
     isn't the outline network". Because number-label pixels aren't
     part of the outline network, they end up labeled together with the
     region they sit inside.
  4. Expand each region into the anti-aliased ring of the outline (the
     band between the soft outline edge and the deep ink core).
     Reveals therefore touch the visible line without leaving a gap.
  5. The deepest ink pixels (brightness < TRUE_LINE_THRESHOLD) stay
     unpainted — that's the line you actually see.
  6. For each region, the most-common quantised design colour decides
     which palette index paints it.
  7. Write one RGBA reveal_NN.png per palette index.

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
# Detect the outline network as the biggest 8-connected component
# of pixels below this brightness. Threshold high enough to include
# anti-aliased edges so the network stays one continuous component.
OUTLINE_DETECT_THRESHOLD = 240
# The actual visible line (deep ink) is below this brightness.
# Pixels below this stay unpainted; pixels between this and the
# detect threshold get painted by the surrounding region.
TRUE_LINE_THRESHOLD = 180
# Skip labeled components smaller than this (segmentation noise).
MIN_REGION_PIXELS = 8

EIGHT_CONN = np.ones((3, 3), dtype=bool)


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

    # ---- Read canvas + find the outline network --------------------
    canvas_l = np.array(Image.open(CANVAS).convert("L").resize((w, h)))

    is_dark = canvas_l < OUTLINE_DETECT_THRESHOLD
    dark_labels, n_dark = ndimage.label(is_dark, structure=EIGHT_CONN)
    if n_dark == 0:
        raise SystemExit("No dark pixels in canvas — wrong image?")
    dark_sizes = ndimage.sum(is_dark, dark_labels, range(1, n_dark + 1))
    biggest_idx = int(dark_sizes.argmax()) + 1
    outline_network = dark_labels == biggest_idx
    true_line = canvas_l < TRUE_LINE_THRESHOLD

    print(f"Canvas: outline network {int(outline_network.sum())} px "
          f"(biggest of {n_dark} dark components), "
          f"true line {int(true_line.sum())} px.")

    # ---- Label region interiors (numbers ride along) ----------------
    interior = ~outline_network
    labels, n_components = ndimage.label(interior, structure=EIGHT_CONN)
    print(f"  {n_components} region components.")

    # ---- Expand labels into the anti-aliased ring -------------------
    # Anti-aliased ring = pixels that are in the outline network but
    # not the true visible line. We want regions to extend over these.
    aa_ring = outline_network & ~true_line
    fillable = aa_ring & (labels == 0)
    n_filled = int(fillable.sum())
    if n_filled > 0:
        _, indices = ndimage.distance_transform_edt(
            labels == 0, return_indices=True
        )
        labels = labels.copy()
        labels[fillable] = labels[
            indices[0][fillable],
            indices[1][fillable],
        ]
    print(f"  expanded labels into {n_filled} anti-aliased px.")

    # ---- For each region, pick the most common palette index --------
    region_color = {}
    region_sizes = ndimage.sum(
        labels > 0, labels, range(1, n_components + 1)
    )
    for region_id in range(1, n_components + 1):
        if region_sizes[region_id - 1] < MIN_REGION_PIXELS:
            continue
        region_pixels = labels == region_id
        counts = np.bincount(
            design_indices[region_pixels], minlength=N_COLORS
        )
        region_color[region_id] = int(counts.argmax())

    print(f"  {len(region_color)} regions large enough to colour.")

    # ---- Build the 20 reveal masks ----------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    color_to_regions = Counter()
    for c in region_color.values():
        color_to_regions[c] += 1

    print(f"{'#':>3}  {'Color':>15}  {'Regions':>8}  {'Pixels':>10}  {'KB':>6}")
    for color_id in range(N_COLORS):
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
