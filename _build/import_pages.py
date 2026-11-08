#!/usr/bin/env python3
"""Import covers that arrive as first-page renders: <tag>.jpg + <tag>.txt pairs (the page as a
JPEG and its text layer), an optional sharper <tag>-zoom.jpg for zooming in, plus listing.json
with the original file names.

    python3 _build/import_pages.py path/to/out [--no-wall] [--main-only] [--report report.tsv]

Same reading as the PDF importer (section, date, volume/number, parsha from the text; the file
name helps with the section), but the picture is already rendered. --no-wall keeps the covers out
of the drifting background on the home page. Run _build/build.py afterwards.
"""
import json, os, re, sys
from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_covers as ic

def trim(im, pad=6):
    """Cut the white page margin away, as the PDF importer does."""
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
    if box:
        im = im.crop((max(box[0]-pad, 0), max(box[1]-pad, 0), min(box[2]+pad, im.width), min(box[3]+pad, im.height)))
    return im

def render(im, out_big, out_small, zoom_src=None, out_zoom=None):
    im = trim(im)
    if im.width > 900: im = im.resize((900, round(900 * im.height / im.width)), Image.LANCZOS)
    im.save(out_big, quality=84, optimize=True, progressive=True)
    if out_small:
        im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).save(out_small, quality=76, optimize=True)
    if zoom_src and out_zoom and os.path.exists(zoom_src):      # the sharper copy for zooming in
        z = trim(Image.open(zoom_src), pad=round(6 * Image.open(zoom_src).width / max(im.width, 1)))
        if z.width > ic.ZOOM_W: z = z.resize((ic.ZOOM_W, round(ic.ZOOM_W * z.height / z.width)), Image.LANCZOS)
        os.makedirs(os.path.dirname(out_zoom), exist_ok=True)
        z.save(out_zoom, quality=80, optimize=True, progressive=True)

def main(folder, no_wall=False, report=None, only=None, main_only=False):
    data = json.load(open(ic.DATA, encoding="utf-8")) if os.path.exists(ic.DATA) else {}
    ic.KNOWN_FRIDAYS.update(data.keys())
    listing = json.load(open(os.path.join(folder, "listing.json"), encoding="utf-8"))
    items = []
    for it in listing:
        tag, name = it["tag"], os.path.basename(it["path"])
        txt = os.path.join(folder, tag + ".txt"); jpg = os.path.join(folder, tag + ".jpg")
        if not os.path.exists(jpg): continue
        text = open(txt, encoding="utf-8", errors="replace").read() if os.path.exists(txt) else ""
        items.append((tag, name, it, ic.normalize_text(text), jpg))
    # main-section covers carry full dates: they go first and anchor the others
    items.sort(key=lambda x: (0 if ic.section_of(x[3], x[1]) == "a" else 1, x[1]))
    rows, added = [], 0
    for tag, name, it, text, jpg in items:
        if only and tag not in only: continue
        sec = ic.section_of(text, name)
        if main_only and sec != "a":
            rows.append((tag, name, "notmain", "", sec)); continue
        d = ic.date_of(text)
        if not d:
            rows.append((tag, name, "nodate", "", sec)); print(f"skip  {name}: no date found"); continue
        key = d.isoformat()
        ed = data.setdefault(key, {"date": key, "vol": None, "no": None, "parsha": None, "covers": {}})
        vol, no = ic.volno_of(text)
        if vol and not ed.get("no"): ed["vol"], ed["no"] = vol, no
        p = ic.parsha_of(text)
        if p and not ed.get("parsha"): ed["parsha"] = p
        if sec in ed["covers"]:
            rows.append((tag, name, "dup", key, sec)); continue
        big = f"covers/archive/{key}-{sec}.jpg"; small = f"covers/wall/{sec}-{key}.jpg"
        render(Image.open(jpg), os.path.join(ic.ROOT, big), None if no_wall else os.path.join(ic.ROOT, small),
               zoom_src=os.path.join(folder, tag + "-zoom.jpg"), out_zoom=os.path.join(ic.ROOT, f"covers/zoom/{key}-{sec}.jpg"))
        ed["covers"][sec] = big
        ed.setdefault("texts", {})[sec] = ic.cover_text(text)
        ed.setdefault("source", {})[sec] = f"pdf:{it['path']}"
        if no_wall: ed["nowall"] = True
        ic.KNOWN_FRIDAYS.add(key)
        rows.append((tag, name, "added", key, sec))
        added += 1
        print(f"added {name}: {key} section {sec}" + (f" vol {vol} no {no}" if vol else "") + (f" {p}" if p else ""), flush=True)
    ic.enrich(data)
    json.dump(dict(sorted(data.items())), open(ic.DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            for r in rows: f.write("\t".join(r) + "\n")
    from collections import Counter
    print(Counter(r[2] for r in rows)); print(f"{added} covers added; {len(data)} editions")

if __name__ == "__main__":
    args = sys.argv[1:]
    no_wall = "--no-wall" in args
    if no_wall: args.remove("--no-wall")
    main_only = "--main-only" in args          # only pages that carry the masthead's VOL/NO line
    if main_only: args.remove("--main-only")
    report = None
    if "--report" in args:
        i = args.index("--report"); report = args[i + 1]; del args[i:i + 2]
    main(args[0], no_wall=no_wall, report=report, main_only=main_only)
