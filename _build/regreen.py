#!/usr/bin/env python3
"""Bring the masthead green of covers that came as JPEGs (Mailchimp) in line with the covers
rendered from the print PDFs. Those JPEGs were converted from print colours without a profile,
so the masthead green came out a bright yellowish green (24,208,16) instead of the paper's
deep green (0,144,72). Pixels in that bright-green range are remapped, blends with white and
black included; everything else is left alone.

    python3 _build/regreen.py                 # all covers imported from Mailchimp
    python3 _build/regreen.py path/to.jpg ... # specific files (written in place)
"""
import json, os, sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = np.array([24, 208, 16]) / 255.0          # the bright green as it arrived
DST = np.array([0, 144, 72]) / 255.0           # the masthead green of the PDF renders
SRC_HUE = 117.0                                # degrees

def regreen(im):
    a = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2); mn = a.min(axis=2); delta = mx - mn + 1e-6
    # hue in degrees
    hue = np.where(mx == g, 60 * ((b - r) / delta) + 120,
          np.where(mx == r, (60 * ((g - b) / delta)) % 360, 60 * ((r - g) / delta) + 240))
    sat = delta / (mx + 1e-6)
    dh = np.abs(((hue - SRC_HUE) + 180) % 360 - 180)
    w_h = np.clip((28 - dh) / 13, 0, 1)        # full within 15 degrees, gone at 28
    w_s = np.clip((sat - 0.15) / 0.25, 0, 1)   # full from 40% saturation
    w_v = np.clip((mx - 0.25) / 0.15, 0, 1)    # leave near-black alone
    w = (w_h * w_s * w_v)[..., None]
    # how much "green ink" the pixel carries (blends with white), and how dark it is (blends with black)
    ink = np.clip((1 - r) / (1 - SRC[0]), 0, 1)[..., None]
    dark = np.clip(g / SRC[1], 0, 1)[..., None]
    new = (1 - ink) * 1.0 + ink * (DST * dark)
    out = a * (1 - w) + new * w
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))

def process(big, small=None):
    im = Image.open(big)
    fixed = regreen(im)
    fixed.save(big, quality=84, optimize=True, progressive=True)
    if small:
        fixed.resize((320, round(320 * fixed.height / fixed.width)), Image.LANCZOS).save(small, quality=76, optimize=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for p in sys.argv[1:]: process(p); print("regreened", p)
    else:
        data = json.load(open(os.path.join(ROOT, "_build", "editions.json"), encoding="utf-8"))
        n = 0
        for key, ed in sorted(data.items()):
            for sec, src in ed.get("source", {}).items():
                if not src.startswith("mailchimp:"): continue
                big = os.path.join(ROOT, ed["covers"][sec])
                small = os.path.join(ROOT, "covers", "wall", f"{sec}-{key}.jpg")
                process(big, small if os.path.exists(small) else None); n += 1
        print(f"{n} covers regreened")
