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
    if re.search(r"section[ _]a|saction[ _]a|_aa|a\.pdf$", n): return "a"
    if re.search(r"section[ _]c|_cc|_c\.pdf$|c\.pdf$", n): return "c"
    if re.search(r"section[ _]d|_dd|_d\.pdf$|d\.pdf$", n): return "d"
    if re.search(r"section[ _]b|_bb|_b\.pdf$|b\.pdf$", n): return "b"
    if re.search(r"VOL\s*\d+", text): return "a"
    if "חסידישע" in text: return "c"
    if "יום טוב" in text: return "d"
    return "b"

def to_friday(d):
    # editions are dated by their Friday: Wednesday/Thursday belong to the coming Friday,
    # a Saturday or Sunday date to the Friday just before
    w = d.weekday()
    if w <= 4: return d + timedelta(days=4 - w)
    return d - timedelta(days=w - 4)

HEB_VAL = {"א":1,"ב":2,"ג":3,"ד":4,"ה":5,"ו":6,"ז":7,"ח":8,"ט":9,"י":10,"כ":20,"ך":20,"ל":30,"מ":40,"ם":40,
           "נ":50,"ן":50,"ס":60,"ע":70,"פ":80,"ף":80,"צ":90,"ץ":90,"ק":100,"ר":200,"ש":300,"ת":400}
HEB_MONTHS = {"תשרי":7,"חשון":8,"מרחשון":8,"חשוון":8,"כסלו":9,"כסליו":9,"טבת":10,"שבט":11,"אדר":12,"אדר א":12,"אדר ב":13,
              "ניסן":1,"אייר":2,"סיון":3,"סיוון":3,"תמוז":4,"אב":5,"מנחם אב":5,"אלול":6}

def gematria(word):
    return sum(HEB_VAL.get(ch, 0) for ch in word)

def hebrew_year_of(text):
    """5785 for תשפ״ה / תשפ"ה / תשפ''ה."""
    m = re.search(r"\b(ת[\u05d0-\u05ea]{1,2})[\"״'′]{1,2}([\u05d0-\u05ea])\b", text)
    if not m: return None
    y = 5000 + gematria(m.group(1) + m.group(2))
    return y if 5780 <= y <= 5795 else None

def hebrew_date_of(text, hyear):
    """A Hebrew date such as י״ט חשון, converted through the calendar (needs pyluach)."""
    if not hyear: return None
    try: from pyluach import dates as hdates
    except ImportError: return None
    m = re.search(r"([\u05d0-\u05ea]{1,2})[\"״'′]?([\u05d0-\u05ea])?\s+(מנחם אב|אדר [אב]|מרחשון|חשוון|תשרי|חשון|כסלו|כסליו|טבת|שבט|אדר|ניסן|אייר|סיון|סיוון|תמוז|אב|אלול)", text)
    if not m: return None
    day = gematria(m.group(1) + (m.group(2) or ""))
    if not 1 <= day <= 30: return None
    try: return hdates.HebrewDate(hyear, HEB_MONTHS[m.group(3)], day).to_pydate()
    except Exception: return None

KNOWN_FRIDAYS = set()   # edition dates already known (from main-section covers); filled by main()

def guess_year(mon, day):
    """A cover date without a year: the paper is dated Wednesday to Friday, so only some
    years fit; prefer a year in which that Friday is already a known edition."""
    fits = []
    for y in range(2022, date.today().year + 1):
        try: d = date(y, mon, day)
        except ValueError: continue
        if d.weekday() <= 4 and d <= date.today() + timedelta(days=7): fits.append(d)
    if not fits: return None
    known = [d for d in fits if to_friday(d).isoformat() in KNOWN_FRIDAYS]
    pick = (known or fits)[-1]
    return pick.year

def civil_year(hyear, mon, day):
    """The civil year in which the given month/day falls during Hebrew year hyear."""
    try: from pyluach import dates as hdates
    except ImportError: return hyear - 3760
    for y in (hyear - 3761, hyear - 3760):
        try:
            if hdates.HebrewDate.from_pydate(date(y, mon, day)).year == hyear: return y
        except ValueError: pass
    return hyear - 3760

def decode_glyphs(text):
    """Some older covers were set in fonts whose text layer stores glyph codes instead of
    characters: Latin text comes out shifted by 29 (DECEMBER -> '(&(0%(5) and Hebrew letters
    land in the Latin-1 range (0xAA-0xC9). Undo both."""
    out = []
    for ch in text:
        c = ord(ch)
        if ch in "\n\t \"": out.append(ch)                 # real whitespace and gershayim stay
        elif 0x01 <= c <= 0x3D: out.append(chr(c + 29))
        elif 0xAA <= c <= 0xC9: out.append(chr(c + 33 + 0x500))
        else: out.append(ch)
    return "".join(out)

def looks_garbled(text):
    return len(re.findall(r"[\xAA-\xC9]", text)) > 20 and len(re.findall(r"[\u05d0-\u05ea]", text)) < 20

def date_of(text):
    d = _date_of(text)
    if d: return d
    dec = decode_glyphs(text)
    d = _date_of(dec)
    if d: return d
    return _date_of("\n".join(line[::-1] for line in dec.splitlines()))

def _date_of(text):
    # "MAY 13-15, '26"  /  "October 23, '26"  /  "Oct 30" (+ Hebrew year)  /  "י״ט חשון תשפ״ז"
    hyear = hebrew_year_of(text)
    cands = []
    MONTH_WORDS = ("jan","january","feb","february","mar","march","apr","april","may","jun","june","jul","july",
                   "aug","august","sep","sept","september","oct","october","nov","november","dec","december")
    # "OCT. 30 - NOV. 1, '24": a range may cross into the next month; the edition is dated by its end
    for m in re.finditer(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:\s*-\s*(?:([A-Za-z]{3,9})\.?\s+)?(\d{1,2}))?(?:,?\s*'(\d{2}))?", text):
        word = m.group(1).lower()
        if word not in MONTH_WORDS: continue
        mon = MONTHS[word[:3]]
        if m.group(4):
            day = int(m.group(4))
            if m.group(3):
                w2 = m.group(3).lower()
                if w2 not in MONTH_WORDS: continue
                mon = MONTHS[w2[:3]]
        else:
            day = int(m.group(2))
        if m.group(5): year = 2000 + int(m.group(5))
        elif hyear: year = civil_year(hyear, mon, day)
        else:
            year = guess_year(mon, day)
            if year is None: continue
        try: d = date(year, mon, day)
        except ValueError: continue
        # the paper is dated Wednesday to Friday; "FRIDAY," right before the date is the masthead box
        score = (2 if d.weekday() in (2, 3, 4) else 0) + (1 if m.group(5) or hyear else 0) \
                + (2 if re.search(r"FRIDAY,?\s*$", text[max(0, m.start()-12):m.start()], re.I) else 0)
        cands.append((score, -m.start(), d))
    if cands:
        cands.sort(reverse=True)
        return to_friday(cands[0][2])
    hd = hebrew_date_of(text, hyear)
    return to_friday(hd) if hd else None

def volno_of(text):
    m = re.search(r"VOL\.?\s*(\d+)[^0-9]{1,8}NO\.?\s*(\d+)", text, re.I)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

def parsha_of(text):
    m = re.search(r"(פ'|פרשת)\s*([א-ת]+(?:\s[א-ת]+)?)", text)
    return f"פ' {m.group(2).strip()}" if m else None

def cover_text(text):
    """A compact, searchable version of a cover's text: distinct words, Hebrew and Latin,
    in reading order, without punctuation. Glyph-coded covers are decoded first."""
    if looks_garbled(text) or not re.search(r"[\u05d0-\u05ea]{2,}", text):
        dec = decode_glyphs(text)
        text = dec + "\n" + "\n".join(line[::-1] for line in dec.splitlines())
    text = re.sub(r"[\u0591-\u05c7]", "", text)                      # nikkud and cantillation
    words, seen = [], set()
    for w in re.findall(r"[\u05d0-\u05eaA-Za-z][\u05d0-\u05eaA-Za-z'\"״׳\-]*", text):
        w = w.strip("'\"״׳-")
        key = w.lower().replace("״", "").replace("\"", "").replace("׳", "").replace("'", "")
        if len(key) < 2 or key in seen: continue
        seen.add(key); words.append(w)
    return " ".join(words[:220])

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
    im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).save(out_small, quality=76, optimize=True)

def main(paths):
    data = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {}
    KNOWN_FRIDAYS.update(data.keys())
    # main-section covers carry full dates: import them first so they anchor the others
    paths = sorted(paths, key=lambda f: 0 if section_of(text_of(f), os.path.basename(f)) == "a" else 1)
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
        ed.setdefault("texts", {})[sec] = cover_text(text)
        KNOWN_FRIDAYS.add(key)
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
        ed["hyear"] = hdates.HebrewDate.from_pydate(shabbos).hebrew_date_string().split()[-1]   # the year of that Shabbos (Rosh Hashana editions belong to the new year)
    keys = sorted(data)
    for i, key in enumerate(keys):
        ed = data[key]
        if ed.get("vol"): continue
        prv = data[keys[i-1]] if i > 0 else None
        nxt = data[keys[i+1]] if i + 1 < len(keys) else None
        if prv and nxt and prv.get("vol") == nxt.get("vol") and prv.get("no") and nxt.get("no") == prv["no"] + 2:
            ed["vol"], ed["no"] = prv["vol"], prv["no"] + 1
        elif prv and prv.get("vol") and prv.get("no") and (not nxt or not nxt.get("vol")):
            ed["vol"], ed["no"] = prv["vol"], prv["no"] + 1

if __name__ == "__main__":
    main(sys.argv[1:])
