#!/usr/bin/env python3
"""Import covers that arrive as first-page renders: <tag>.jpg + <tag>.txt pairs (the page as a
JPEG and its text layer), an optional sharper <tag>-zoom.jpg for zooming in, plus listing.json
with the original file names.

    python3 _build/import_pages.py path/to/out [--no-wall] [--main-only] [--report report.tsv]

Same reading as the PDF importer (section, date, volume/number, parsha from the text; the file
name helps with the section), but the picture is already rendered. --no-wall keeps the covers out
of the drifting background on the home page. Run _build/build.py afterwards.
"""
import json, os, re, subprocess, sys, tempfile
from datetime import timedelta
from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_covers as ic

def ocr_masthead(jpg):
    """The text of the top of a page, read by tesseract (the date line and VOL/NO of a main
    cover, the title of a supplement). Only used for thumbnails, which have no text layer."""
    im = Image.open(jpg).convert("L")
    crops = [(im.crop((0, 0, im.width, int(im.height * 0.30))), 3, None),                        # the whole masthead
             (im.crop((int(im.width * 0.68), 0, im.width, int(im.height * 0.22))), 4, 140)]      # the date box at the top right
    out = []
    for band, scale, thr in crops:
        band = band.resize((band.width * scale, band.height * scale), Image.LANCZOS)
        if thr: band = band.point(lambda v: 255 if v > thr else 0)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            band.save(f.name)
            for psm, lang in ((3, "eng+heb"), (11, "eng"), (6, "eng")):
                try:
                    r = subprocess.run(["tesseract", f.name, "-", "-l", lang, "--psm", str(psm)],
                                       capture_output=True, text=True, timeout=180)
                    out.append(r.stdout)
                except Exception:
                    out.append("")
            os.unlink(f.name)
    text = "\n".join(out)
    text = re.sub(r"[|]", "", text)
    text = re.sub(r"(?<=\d)[,.]\s*[\u2018\u2019'`´\u00b0]\s*(\d\d)\b", r", '\1", text)        # 12, ’14 -> 12, '14
    text = re.sub(r"\b(\d{1,2})\s*[\u2018\u2019'`´\u00b0]\s*(\d\d)\b", r"\1, '\2", text)
    return text

MONTH_WORDS = ("jan","january","feb","february","mar","march","apr","april","may","jun","june","jul","july",
               "aug","august","sep","sept","september","oct","october","nov","november","dec","december")

def volume_window(vol):
    """First and last civil day of a volume's Hebrew year (volume 1 was 5748)."""
    from pyluach import dates as hdates
    h = 5747 + vol
    return hdates.HebrewDate(h, 7, 1).to_pydate(), hdates.HebrewDate(h + 1, 7, 1).to_pydate() - timedelta(days=1)

def ocr_date(text, vol, no=None):
    """The month and day read off a masthead by OCR, placed in the civil year of the volume
    (OCR often garbles the two-digit year, never the volume folder). Around Rosh Hashana both
    years fit; the issue number says which end of the volume the paper belongs to."""
    from datetime import date
    lo, hi = volume_window(vol)
    expected = lo + timedelta(weeks=(no or 26) - 1)
    best = None
    for m in re.finditer(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})\b", text):
        word = m.group(1).lower()
        if word not in MONTH_WORDS: continue
        mon, day = ic.MONTHS[word[:3]], int(m.group(2))
        for y in range(lo.year, hi.year + 1):
            try: d = date(y, mon, day)
            except ValueError: continue
            if lo - timedelta(days=7) <= d <= hi + timedelta(days=7):
                score = (2 if re.search(r"FRIDAY,?\s*$", text[max(0, m.start() - 12):m.start()], re.I) else 0) \
                        + (1 if d.weekday() in (2, 3, 4) else 0)
                cand = (score, -abs((d - expected).days), ic.to_friday(d))
                if not best or cand[:2] > best[:2]: best = cand
    return best[2] if best else None

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
        if it.get("thumb"):
            # Drive's thumbnail of the first page: no text layer, so the masthead is read by OCR
            jpg = os.path.join(folder, tag + ".thumb.jpg"); txt = os.path.join(folder, tag + ".thumb.txt")
            if not os.path.exists(jpg): continue
            if not os.path.exists(txt):
                open(txt, "w", encoding="utf-8").write(ocr_masthead(jpg))
        else:
            txt = os.path.join(folder, tag + ".txt"); jpg = os.path.join(folder, tag + ".jpg")
            if not os.path.exists(jpg): continue
        text = open(txt, encoding="utf-8", errors="replace").read() if os.path.exists(txt) else ""
        items.append((tag, name, it, ic.normalize_text(text), jpg))
    def section(it, text, name):
        if it.get("thumb") and it.get("kind") in ("a", "b", "c", "d"): return it["kind"]   # no text layer: go by the file name
        sec = ic.section_of(text, name)
        if it.get("kind") in ("g", "s") and sec == "a": sec = "d"     # a GEN/SP1 special is never the main paper
        return sec
    # main-section covers carry full dates: they go first and anchor the others
    items.sort(key=lambda x: (0 if section(x[2], x[3], x[1]) == "a" else 1, 1 if x[2].get("thumb") else 0, x[1]))
    rows, added = [], 0
    issue_date = {}        # issue folder -> the date on its main cover
    def week_guess(issue):
        """The Friday of an issue whose masthead could not be read, counted in weeks from the
        dated issues of the same volume; None when a skipped week in between makes it unsure."""
        m = re.match(r"(.*?)/0*(\d+)$", issue or "")
        if not m: return None
        vol, n = m.group(1), int(m.group(2))
        known = {}
        for iss, dt in issue_date.items():
            m2 = re.match(r"(.*?)/0*(\d+)$", iss)
            if m2 and m2.group(1) == vol: known[int(m2.group(2))] = dt
        if not known: return None
        below = [k for k in known if k < n]; above = [k for k in known if k > n]
        lo = max(below) if below else None; hi = min(above) if above else None
        if lo is not None and hi is not None:
            if (known[hi] - known[lo]).days == 7 * (hi - lo): return known[lo] + timedelta(weeks=n - lo)
            return None                                   # a week was skipped somewhere in between
        if lo is not None and n - lo <= 2: return known[lo] + timedelta(weeks=n - lo)
        if hi is not None and hi - n <= 2: return known[hi] - timedelta(weeks=hi - n)
        return None
    for tag, name, it, text, jpg in items:
        if only and tag not in only: continue
        sec = section(it, text, name)
        if main_only and sec != "a":
            rows.append((tag, name, "notmain", "", sec)); continue
        issue = it.get("issue")
        mv = re.match(r"Vol\.? *(\d+)/0*(\d+)$", issue or "")
        d = ocr_date(text, int(mv.group(1)), int(mv.group(2))) if it.get("thumb") and mv else ic.date_of(text)
        if it.get("thumb"):
            # OCR misreads a digit now and then; counting weeks from the dated issues is surer
            guess = week_guess(issue)
            if guess and d != guess:
                if d: print(f"count {it['path']}: OCR read {d}, counting weeks gives {guess}; taking the count")
                else: print(f"count {it['path']}: {guess} by counting weeks")
                d = guess
            elif d and not guess:
                print(f"ocr   {it['path']}: {d} read off the thumbnail, nothing to count from: check it")
            if sec == "a" and d and issue: issue_date.setdefault(issue, d)
        if sec == "a" and d and issue and issue not in issue_date:
            within = it["path"][len(issue):].lstrip("/")
            if not re.match(r"\d{1,2}/", within): issue_date[issue] = d     # not a copy of another issue filed here
        elif sec != "a" and issue in issue_date and d != issue_date[issue]:
            # a supplement is dated by the issue it was filed with; its own masthead date can carry a typo
            if d: print(f"note  {it['path']}: says {d}, filed with the {issue_date[issue]} edition")
            d = issue_date[issue]
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
               zoom_src=jpg if it.get("thumb") else os.path.join(folder, tag + "-zoom.jpg"),
               out_zoom=os.path.join(ic.ROOT, f"covers/zoom/{key}-{sec}.jpg"))
        ed["covers"][sec] = big
        ed.setdefault("texts", {})[sec] = ic.cover_text(text)
        ed.setdefault("source", {})[sec] = ("thumb:" if it.get("thumb") else "pdf:") + it["path"]
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
