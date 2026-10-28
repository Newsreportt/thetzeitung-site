# Adds covers to the scrolling wall. Usage: python3 _build/add_covers.py NAME file.pdf [file2.jpg ...]
# Each PDF's first page (or each image) becomes covers/wall/NAME-N.jpg, then run build.py.
import os, sys, subprocess, tempfile
from PIL import Image, ImageChops
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "covers", "wall")
name, files = sys.argv[1], sys.argv[2:]
n = 0
for f in files:
    if f.lower().endswith(".pdf"):
        tmp = tempfile.mkdtemp()
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "70", "-jpeg", f, os.path.join(tmp, "p")], check=True)
        src = os.path.join(tmp, sorted(os.listdir(tmp))[0])
    else:
        src = f
    im = Image.open(src).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
    if box: im = im.crop(box)
    w, h = im.size
    n += 1
    im.resize((380, round(380 * h / w)), Image.LANCZOS).save(os.path.join(OUT, f"{name}-{n}.jpg"), quality=80, optimize=True)
    print("added", f"{name}-{n}.jpg")
