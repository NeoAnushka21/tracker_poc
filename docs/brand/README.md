# Tandurust brand files

| File | What it is |
|---|---|
| `tandurust-logo-original.jpg` | The owner's full logo (emblem, "TANDURUST" wordmark, tagline "AI MEAL & WELLNESS TRACKER"), 1024 × 559, on an off-white background. Reference only. |
| `tandurust-emblem-1024.png` | The emblem alone with a **transparent** background, 1024 × 1024. Master for every size used in the app. |
| `tandurust-emblem-256.png` | The same, 256 px, used at the top of the root README. |
| `cutout.py` | How the transparent emblem was made (see below). |

The app's copies live in `frontend/public/brand/`: `emblem-96.png` and `emblem-192.png` (the `AppLogo` component, sharp on high-density screens), `favicon-32.png` / `favicon-64.png` (browser tab), `apple-touch-icon.png` (180 px on the warm off-white, for phone home screens, which show transparent icons on black).

## How the transparent emblem was made (2026-10-01)

The owner's emblem came as a Gemini-generated PNG (2816 × 1536) with the transparency checkerboard **painted in**: every pixel is opaque. `cutout.py` separates it by colour: the checkerboard is grey (no colour), the emblem is strongly coloured, so opacity follows how colourful each pixel is, and edge pixels are un-mixed from the grey behind them. It then crops a square around the emblem (which also drops Gemini's small watermark) and writes the sizes. It needs Pillow and NumPy, which aren't app dependencies: install them somewhere temporary to rerun it. A real transparent PNG or SVG from the designer would replace all of this.

## Colours taken from the emblem

Deep green `#358449`, leaf green `#639c46`, yellow-green `#93b540`, amber `#f9b429`, orange `#f28b25`. The app theme (`frontend/src/styles.css`) uses a forest green `#2e7d32` for text and buttons (readable on white) and the green → yellow-green → amber gradient (`--brand-grad`) for decoration only.
