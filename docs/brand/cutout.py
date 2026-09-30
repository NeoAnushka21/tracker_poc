"""Cut the Tandurust emblem out of the Gemini PNG (checkerboard painted in, alpha 255 everywhere).

The background is grey/white (no colour); the emblem is strongly coloured. Alpha comes from how
colourful a pixel is; edge pixels are un-mixed from the grey behind them.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SRC = r'C:/Users/anushka.mhatre/Downloads/Gemini_Generated_Image_blxlvfblxlvfblxl.png'
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

rgb = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32)
sat = rgb.max(axis=2) - rgb.min(axis=2)
print('colourfulness percentiles 50/90/95/99:', np.percentile(sat, [50, 90, 95, 99]).round(1))

LOW, HIGH = 14.0, 70.0
alpha = np.clip((sat - LOW) / (HIGH - LOW), 0, 1)

# Background grey behind each pixel: the checker squares are ~205 or ~245; estimate from the pixel's
# own lightest channel is unreliable inside the logo, so use a blurred map of the pure-grey pixels.
def box_blur(a, r):
    """Mean over a (2r+1)^2 window (summed-area table)."""
    pad = np.pad(a, r + 1, mode='edge').cumsum(0).cumsum(1)
    k = 2 * r + 1
    return (pad[k:, k:] - pad[:-k, k:] - pad[k:, :-k] + pad[:-k, :-k])[:a.shape[0], :a.shape[1]] / (k * k)

isgrey = (sat < 8).astype(np.float64)
greyv = np.where(sat < 8, rgb.mean(axis=2), 0).astype(np.float64)
wb, bgb = box_blur(isgrey, 12), box_blur(greyv, 12)
g = np.where(wb > 0.05, bgb / np.maximum(wb, 1e-3), 225.0)[..., None].astype(np.float32)

a3 = alpha[..., None]
col = np.clip((rgb - (1 - a3) * g) / np.maximum(a3, 0.05), 0, 255)
rgba = np.dstack([col, alpha * 255]).astype(np.uint8)

ys, xs = np.where(alpha > 0.5)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
print('emblem bbox', x0, x1, y0, y1, 'size', x1 - x0, y1 - y0)
# Square crop centred on the emblem with a small margin (the watermark sits far outside it).
side = int(max(x1 - x0, y1 - y0) * 1.06)
cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
img = Image.fromarray(rgba, 'RGBA').crop(box)
img.save(OUT / 'emblem-full.png')
for size in (512, 192, 180, 64, 32):
    img.resize((size, size), Image.LANCZOS).save(OUT / f'emblem-{size}.png', optimize=True)
# Previews on light, dark and the app's mid grey, to check the edges.
for name, colour in (('light', (250, 250, 250)), ('dark', (18, 18, 18)), ('green', (231, 246, 239))):
    tiles = []
    for size in (512, 64, 32):
        e = img.resize((size, size), Image.LANCZOS)
        tile = Image.new('RGBA', (size + 20, size + 20), colour + (255,))
        tile.alpha_composite(e, (10, 10))
        tiles.append(tile)
    W = sum(t.width for t in tiles) + 20 * len(tiles)
    H = max(t.height for t in tiles)
    sheet = Image.new('RGBA', (W, H), colour + (255,))
    x = 0
    for t in tiles:
        sheet.alpha_composite(t, (x, 0)); x += t.width + 20
    sheet.convert('RGB').save(OUT / f'preview-{name}.png')
print('done')
