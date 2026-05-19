"""Generate per-color reveal masks for the paint-by-numbers website.

Pipeline:
  1. Identify outline NETWORK on canvas.png (single largest 8-connected
     component of dark pixels). Number labels are smaller separate
     blobs and ride along inside their surrounding region.
  2. Connected-component label "everything that isn't the outline" to
     get the 200+ paint regions.
  3. For each region, take the AVERAGE colour of design-preview.jpg
     under its pixels — that's the region's true paint colour.
  4. K-means cluster those region colours into exactly N_COLORS groups.
     Each cluster centroid becomes one entry in the palette; every
     cluster has at least one region.
  5. Expand regions into the anti-aliased outline ring (between soft
     edge and deep-ink core) so reveals sit snug against the canvas
     line and paint over any number label they enclose.
  6. Write one RGBA reveal_NN.png per cluster.

This avoids the JPEG-compression artefact that made the previous
quantiser produce duplicate shades nobody used.

Run once after changing the design or canvas image:
    python generate_reveal_masks.py
"""
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.cluster.vq import kmeans2

HERE = Path(__file__).parent
DESIGN = HERE / "design-preview.jpg"
OUT_DIR = HERE / "stempel-wanderung" / "static"
CANVAS = OUT_DIR / "canvas.png"

N_COLORS = 20
OUTLINE_DETECT_THRESHOLD = 240
TRUE_LINE_THRESHOLD = 180
MIN_REGION_PIXELS = 8

EIGHT_CONN = np.ones((3, 3), dtype=bool)


def main():
    design_arr = np.array(Image.open(DESIGN).convert("RGB"))
    h, w, _ = design_arr.shape

    # ---- Outline network -------------------------------------------
    canvas_l = np.array(Image.open(CANVAS).convert("L").resize((w, h)))
    is_dark = canvas_l < OUTLINE_DETECT_THRESHOLD
    dark_labels, n_dark = ndimage.label(is_dark, structure=EIGHT_CONN)
    if n_dark == 0:
        raise SystemExit("No dark pixels in canvas — wrong image?")
    dark_sizes = ndimage.sum(is_dark, dark_labels, range(1, n_dark + 1))
    biggest_idx = int(dark_sizes.argmax()) + 1
    outline_network = dark_labels == biggest_idx
    true_line = canvas_l < TRUE_LINE_THRESHOLD
    print(f"Canvas: outline network {int(outline_network.sum())} px, "
          f"true line {int(true_line.sum())} px.")

    # ---- Region labels ---------------------------------------------
    interior = ~outline_network
    labels, n_components = ndimage.label(interior, structure=EIGHT_CONN)
    print(f"  {n_components} region components.")

    # ---- Compute each region's average design colour ---------------
    region_ids = []
    region_avg = []
    region_sizes = ndimage.sum(
        labels > 0, labels, range(1, n_components + 1)
    )
    for region_id in range(1, n_components + 1):
        size = region_sizes[region_id - 1]
        if size < MIN_REGION_PIXELS:
            continue
        mask = labels == region_id
        avg = design_arr[mask].mean(axis=0)
        region_ids.append(region_id)
        region_avg.append(avg)
    region_avg = np.asarray(region_avg, dtype=np.float64)
    print(f"  {len(region_ids)} regions large enough to colour.")

    # ---- K-means cluster region colours into N_COLORS groups -------
    centroids, cluster_labels = kmeans2(
        region_avg,
        k=N_COLORS,
        minit="++",
        seed=42,
    )
    palette = [
        (int(round(c[0])), int(round(c[1])), int(round(c[2])))
        for c in centroids
    ]
    region_color = dict(zip(region_ids, [int(c) for c in cluster_labels]))

    # ---- Expand labels into anti-aliased ring (snug against line) --
    aa_ring = outline_network & ~true_line
    fillable = aa_ring & (labels == 0)
    if fillable.any():
        _, idx = ndimage.distance_transform_edt(
            labels == 0, return_indices=True
        )
        labels = labels.copy()
        labels[fillable] = labels[idx[0][fillable], idx[1][fillable]]

    # ---- Write reveal masks ----------------------------------------
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
