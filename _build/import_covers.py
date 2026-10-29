#!/usr/bin/env python3
"""Import cover PDFs into the archive.

    python3 _build/import_covers.py path/to/*.pdf

For each PDF this reads the first page's text to find the section
(main / Yiddishe Tzeit / Chassidishe Tzeit), the edition date, the volume
and number, and the parsha; renders the first page as a JPEG into
covers/archive/ (and a small copy into covers/wall/ for the drifting
background); and records everything in _build/editions.json.
Run _build/build.py afterwards to regenerate the pages.
"""
import glob, json, os, re, subprocess, sys, tempfile
from datetime import date, timedelta
from PIL import Image, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "covers", "archive")
WALL = os.path.join(ROOT, "covers", "wall")
DATA = os.path.join(ROOT, "_build", "editions.json")
os.makedirs(ARCHIVE, exist_ok=True); os.makedirs(WALL, exist_ok=True)

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

def text_of(pdf):
    return subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, "-"],
                          capture_output=True, text=True).stdout

def section_of(text, name):
    n = name.lower()
    if re.search(r"section_a|saction_a|_aa|a\.pdf$", n): return "a"
    if re.search(r"section_c|_cc|_c\.pdf$|c\.pdf$", n): return "c"
    if re.search(r"section_b|_bb|_b\.pdf$|b\.pdf$", n): return "b"
    if re.search(r"VOL\s*\d+", text): return "a"
    if "חסידישע" in text: return "c"
    return "b"

def to_friday(d):
    # editions are dated by their Friday; a Wednesday/Thursday date belongs to that week's Friday
    return d + timedelta(days=(4 - d.weekday()) % 7) if d.weekday() <= 4 else d

def date_of(text):
    # "MAY 13-15, '26"  /  "October 23, '26"  /  "Oct 30"  — take the first real month name
    best = None
    for m in re.finditer(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?(?:,?\s*'(\d{2}))?", text):
        mon = MONTHS.get(m.group(1)[:3].lower())
        if not mon or m.group(1).lower() not in ("jan","january","feb","february","mar","march","apr","april","may","jun","june","jul","july","aug","august","sep","sept","september","oct","october","nov","november","dec","december"):
            continue
        day = int(m.group(3) or m.group(2))
        year = 2000 + int(m.group(4)) if m.group(4) else 2026
        try: d = to_friday(date(year, mon, day))
        except ValueError: continue
        if m.group(4): return d          # a dated match with a year wins outright
        best = best or d
    return best

def volno_of(text):
    m = re.search(r"VOL\.?\s*(\d+)[^0-9]{1,8}NO\.?\s*(\d+)", text, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

def parsha_of(text):
    m = re.search(r"(פ'|פרשת)\s*([א-ת]+(?:\s[א-ת]+)?)", text)
    return f"פ' {m.group(2).strip()}" if m else None

def render(pdf, out_big, out_small):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-jpeg", "-jpegopt", "quality=90",
                        pdf, os.path.join(td, "p")], check=True)
        im = Image.open(glob.glob(os.path.join(td, "p*.jpg"))[0]).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
    if box:
        pad = 6
        im = im.crop((max(box[0]-pad, 0), max(box[1]-pad, 0), min(box[2]+pad, im.width), min(box[3]+pad, im.height)))
    if im.width > 900: im = im.resize((900, round(900 * im.height / im.width)), Image.LANCZOS)
    im.save(out_big, quality=84, optimize=True, progressive=True)
    im.resize((380, round(380 * im.height / im.width)), Image.LANCZOS).save(out_small, quality=82, optimize=True)

def main(paths):
    data = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {}
    for pdf in paths:
        name = os.path.basename(pdf)
        text = text_of(pdf)
        sec = section_of(text, name)
        d = date_of(text)
        if not d:
            print(f"skip  {name}: no date found"); continue
        key = d.isoformat()
        ed = data.setdefault(key, {"date": key, "vol": None, "no": None, "parsha": None, "covers": {}})
        vol, no = volno_of(text)
        if vol: ed["vol"], ed["no"] = vol, no
        p = parsha_of(text)
        if p and not ed["parsha"]: ed["parsha"] = p
        big = f"covers/archive/{key}-{sec}.jpg"; small = f"covers/wall/{sec}-{key}.jpg"
        if sec in ed["covers"]:
            print(f"dup   {name}: {key} {sec} already present"); continue
        render(pdf, os.path.join(ROOT, big), os.path.join(ROOT, small))
        ed["covers"][sec] = big
        print(f"added {name}: {key} section {sec}" + (f" vol {vol} no {no}" if vol else "") + (f" {p}" if p else ""))
    enrich(data)
    json.dump(dict(sorted(data.items())), open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(data)} editions in {os.path.relpath(DATA, ROOT)}")

def enrich(data):
    """Fill in the parsha (or yom tov) and the Hebrew date from the calendar."""
    try:
        from pyluach import dates as hdates, parshios
    except ImportError:
        print("pyluach not installed: pip install pyluach"); return
    for key, ed in data.items():
        y, m, d = map(int, key.split("-"))
        friday = date(y, m, d); shabbos = friday + timedelta(days=1)
        hs = hdates.HebrewDate.from_pydate(shabbos)
        if not ed.get("parsha"):
            p = parshios.getparsha_string(hs, israel=False, hebrew=True)
            ed["parsha"] = f"פ' {p}" if p else (hs.holiday(hebrew=True) or None)
        ed["hdate"] = hdates.HebrewDate.from_pydate(friday).hebrew_date_string()

if __name__ == "__main__":
    main(sys.argv[1:])
