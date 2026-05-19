"""Generate per-color reveal masks for the paint-by-numbers website.

Quantizes design-preview.jpg into 20 colors, then writes one transparent
PNG per color showing only the pixels belonging to that color cluster.
The resulting masks go into stempel-wanderung/static/reveal_NN.png
(NN = 01..20).

Run once after changing the design image:
    python generate_reveal_masks.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).parent
DESIGN = HERE / "design-preview.jpg"
OUT_DIR = HERE / "stempel-wanderung" / "static"

N_COLORS = 20


def main():
    design = Image.open(DESIGN).convert("RGB")

    quantized = design.quantize(
        colors=N_COLORS,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    palette = quantized.getpalette()
    colors = [
        (palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2])
        for i in range(N_COLORS)
    ]
    indices = np.array(quantized)
    h, w = indices.shape

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sizes = []
    for i in range(N_COLORS):
        mask = indices == i
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[mask, 0] = colors[i][0]
        rgba[mask, 1] = colors[i][1]
        rgba[mask, 2] = colors[i][2]
        rgba[mask, 3] = 255
        out_path = OUT_DIR / f"reveal_{i + 1:02d}.png"
        Image.fromarray(rgba, "RGBA").save(out_path, optimize=True)
        sizes.append((i + 1, colors[i], int(mask.sum()), out_path.stat().st_size))

    print(f"Generated {N_COLORS} reveal masks in {OUT_DIR}")
    print(f"{'#':>3}  {'Color':>15}  {'Pixels':>10}  {'File size':>10}")
    for n, c, px, sz in sizes:
        print(f"{n:>3}  rgb{c!s:>13}  {px:>10}  {sz / 1024:>8.1f} KB")


if __name__ == "__main__":
    main()
