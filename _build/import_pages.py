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
from datetime import date, timedelta
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

HEB = "\u05d0-\u05ea"
def _near(a, b, text, gap=60):
    """Two whole words within `gap` characters of each other on one line, in either order."""
    pat = lambda x, y: rf"(?<![{HEB}]){x}(?![{HEB}])[^\n|]{{0,{gap}}}?(?<![{HEB}]){y}(?![{HEB}])"
    return re.search(pat(a, b), text) or re.search(pat(b, a), text)

def page_kind(text):
    """What a page is, by the words of its masthead: the main cover (a), a supplement's cover
    (b/c/d/t/k), an inside page of the paper, or None when the text does not say. The text
    layer of older PDFs stores Hebrew words backwards, so both readings are searched."""
    head = re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text[:900])
    flat = re.sub(r"\s+", " ", head)
    both = flat + " | " + " ".join(w[::-1] for w in flat.split())
    if re.search(r"VOL\.?\s*\d+", flat): return "a"
    if _near("אידישע", "צייט", both): return "b"
    if _near("חסידישע", "צייט", both): return "c"
    if _near("יום טוב", "צייט", both) or _near("יו\"ט", "צייט", both): return "d"
    if _near("תורה", "צייט", both, 3): return "t"
    if _near("קהלה", "צייט", both, 3): return "k"
    # a running head with a page number ("• 17 •", "- 17 -"), once dates and VOL/NO are out of the way
    bare = re.sub(r"VOL\.?\s*\d+(\s*[·•.\-]\s*NO\.?\s*\d+)?|\d{1,2}\s*[-–—]\s*\d{1,2}|'\d\d", " ", flat[:500], flags=re.I)
    if re.search(r"FRIDAY|פרייטאג|גאטיירפ", both) and re.search(r"(?:^|\s)[-•·]\s*\d{1,3}\s*[-•·](?:\s|$)|(?:^|\s)\d{1,2}\s*[•·](?:\s|$)", bare):
        return "inside"
    return None

def trim(im, pad=6):
    """Cut the white page margin away, as the PDF importer does."""
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
    if box:
        im = im.crop((max(box[0]-pad, 0), max(box[1]-pad, 0), min(box[2]+pad, im.width), min(box[3]+pad, im.height)))
    return im

def render(im, out_big, out_small, zoom_src=None, out_zoom=None, turn=0):
    if turn: im = im.rotate(turn, expand=True)
    im = trim(im)
    if im.width > 900: im = im.resize((900, round(900 * im.height / im.width)), Image.LANCZOS)
    im.save(out_big, quality=84, optimize=True, progressive=True)
    if out_small:
        im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).save(out_small, quality=76, optimize=True)
    if zoom_src and out_zoom and os.path.exists(zoom_src):      # the sharper copy for zooming in
        z = Image.open(zoom_src)
        if turn: z = z.rotate(turn, expand=True)
        z = trim(z, pad=round(6 * z.width / max(im.width, 1)))
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
        m = re.search(r"\(\s*(\d{1,3})\s*-\s*\d{1,3}|pages?\s+(\d{1,3})\s*-", name, re.I)
        if m and int(m.group(1) or m.group(2)) > 1: return "inside"   # a file that starts inside the paper
        k = page_kind(text)                      # what the page says about itself comes first
        if k == "inside": return k
        if k and it.get("kind") in ("g", "s") and k == "a": k = "d"   # a GEN/SP1 special is never the main paper
        if k: return k
        if it.get("thumb") and it.get("kind") in ("a", "b", "c", "d"): return it["kind"]   # no text layer: go by the file name
        sec = ic.section_of(text, name)
        if it.get("kind") in ("g", "s") and sec == "a": sec = "d"
        return sec
    # what each page says about itself: its section, and its date when the text layer or the OCR
    # of a thumbnail gives one
    def volno(issue):
        m = re.match(r"Vol\.? *(\d+)/0*(\d+)$", issue or "")
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)
    def name_date(name):
        """The edition date in a production file name such as 20171006_XDI_TZE_PG001.pdf."""
        m = re.match(r"(\d{4})(\d{2})(\d{2})[_-]XDI_", name)
        if not m: return None
        try: return ic.to_friday(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError: return None
    manual = {"dates": {}, "rotate": {}, "skip": [], "section": {}}
    if os.path.exists(os.path.join(folder, "manual.json")):      # dates read by eye, pages to turn
        manual.update(json.load(open(os.path.join(folder, "manual.json"), encoding="utf-8")))
    pre = {}
    for tag, name, it, text, jpg in items:
        sec = manual["section"].get(it["path"]) or section(it, text, name)     # a section settled by eye wins
        vol, no = volno(it.get("issue"))
        if it.get("thumb"): d = name_date(name) or (ocr_date(text, vol, no) if vol else None)
        else: d = ic.date_of(text) or name_date(name)
        if it.get("issue") in manual["dates"]: d = date.fromisoformat(manual["dates"][it["issue"]])   # the issue's date, settled by eye
        pre[tag] = (sec, d, vol, no)
    # The weekly grid of each volume: anchored by editions already in the archive and by main
    # covers whose text layer carries a date, filled in with the OCR readings of the thumbnails.
    # Offset = date - 7 days * number: constant along a run of weekly issues, 7 days more after a
    # skipped week. The offsets of a volume are fitted as one non-decreasing step function, so a
    # misread digit is outvoted by the issues around it while a real skipped week is kept.
    def offset(d, no): return d - timedelta(weeks=no)
    known = {}                                   # (vol, no) -> [(offset, weight)]
    for k, ed in data.items():
        if ed.get("vol") and ed.get("no"):
            known.setdefault((ed["vol"], ed["no"]), []).append((offset(date.fromisoformat(k), ed["no"]), 2.5))
    for tag, name, it, text, jpg in items:
        sec, d, vol, no = pre[tag]
        if sec != "a" or not d or not vol: continue
        within = it["path"][len(it["issue"]):].lstrip("/")
        if re.match(r"\d{1,2}/", within): continue          # a copy of another issue filed here
        known.setdefault((vol, no), []).append((offset(d, no), 2 if name_date(name) else 1 if it.get("thumb") else 3))
    def fit(vol):
        """The offset of every issue number of a volume, as the non-decreasing step function that
        best fits the evidence: each reading votes for its offset with its weight, and every
        skipped week (a step of 7 days) costs one vote. Returns {no: date}."""
        ev = {m: lst for (v, m), lst in known.items() if v == vol}
        if not ev: return {}
        offsets = sorted({o for lst in ev.values() for o, w in lst})
        lo, hi = min(ev), max(ev)
        INF = float("inf")
        cost = lambda n, o: -sum(w for oo, w in ev.get(n, []) if oo == o)
        best = [cost(lo, o) for o in offsets]; back = []
        for n in range(lo + 1, hi + 1):
            cur, bk = [], []
            for j, o in enumerate(offsets):
                c, arg = INF, None
                for i in range(j + 1):
                    v = best[i] + (o - offsets[i]).days / 7
                    if v < c: c, arg = v, i
                cur.append(c + cost(n, o)); bk.append(arg)
            best, back = cur, back + [bk]
        j = min(range(len(offsets)), key=lambda j: best[j])
        path = {hi: offsets[j]}
        for n in range(hi, lo, -1):
            j = back[n - lo - 1][j]; path[n - 1] = offsets[j]
        return {n: path[n] + timedelta(weeks=n) for n in path}
    fitted = {}
    settled = {}
    copies = set()
    for tag, name, it, text, jpg in items:
        sec, d, vol, no = pre[tag]
        if sec != "a" or not vol: continue
        if vol not in fitted: fitted[vol] = fit(vol)
        sd = fitted[vol].get(no)
        mvol, mno = ic.volno_of(text)
        if d and mno and mno != no and (not mvol or mvol == vol) and fitted[vol].get(mno) == d:
            # the masthead names another number, and its date fits that number: a copy of that
            # issue filed in this folder; it stays with its own date (and is then a duplicate)
            print(f"copy  {it['path']}: the page is no. {mno} of {d}, filed under {no}: left out")
            copies.add(tag); continue
        if it.get("issue") in manual["dates"]: continue
        if it.get("thumb") or not d:
            if sd and sd != d:
                print(f"grid  {it['path']}: {'read as ' + str(d) + ', ' if d else ''}the volume's weekly grid puts it at {sd}")
            elif not sd and d:
                print(f"ocr   {it['path']}: {d} read off the page, nothing to compare with")
            if sd: settled[tag] = sd
        elif sd and abs((sd - d).days) > 10:
            # a text layer can carry a stray date (an advertisement's, a template's): the grid wins
            print(f"grid  {it['path']}: the text says {d}, the volume's weekly grid puts it at {sd}: taking the grid")
            settled[tag] = sd
    # main covers first (dated ones before the rest), then the supplements, which follow their issue folder
    def order(x):
        tag, name, it, text, jpg = x
        sec, d, vol, no = pre[tag]
        return (2 if sec != "a" else 0 if (d and not it.get("thumb")) else 1, name)
    items.sort(key=order)
    rows, added = [], 0
    issue_date = {}        # issue folder -> the date on its main cover
    for tag, name, it, text, jpg in items:
        if only and tag not in only: continue
        sec, d, vol, no = pre[tag]
        if sec == "inside":
            rows.append((tag, name, "inside", "", "")); print(f"skip  {it['path']}: an inside page, not a cover"); continue
        if tag in copies:
            rows.append((tag, name, "copy", "", sec)); continue
        if it["path"] in manual["skip"]:
            rows.append((tag, name, "skip", "", sec)); continue
        if main_only and sec != "a":
            rows.append((tag, name, "notmain", "", sec)); continue
        issue = it.get("issue")
        if tag in settled: d = settled[tag]
        if sec != "a" and issue not in issue_date and vol and fitted.get(vol, {}).get(no):
            d = d if d and abs((d - fitted[vol][no]).days) <= 10 else fitted[vol][no]     # no dated main cover: the grid places the supplement
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
        if not ed.get("no"):
            mvol, mno = ic.volno_of(text)            # the masthead's VOL/NO line, else the issue folder
            if mvol and not it.get("thumb"): ed["vol"], ed["no"] = mvol, mno
            elif sec == "a" and vol: ed["vol"], ed["no"] = vol, no
        p = ic.parsha_of(text)
        if p and not ed.get("parsha"): ed["parsha"] = p
        if sec in ed["covers"]:
            held = ed.get("source", {}).get(sec, "")
            if it.get("thumb") or not held.startswith("thumb:"):
                rows.append((tag, name, "dup", key, sec)); continue
            print(f"page  {it['path']}: the real page replaces the thumbnail of {key} {sec}")
        big = f"covers/archive/{key}-{sec}.jpg"; small = f"covers/wall/{sec}-{key}.jpg"
        render(Image.open(jpg), os.path.join(ic.ROOT, big), None if no_wall else os.path.join(ic.ROOT, small),
               zoom_src=jpg if it.get("thumb") else os.path.join(folder, tag + "-zoom.jpg"),
               out_zoom=os.path.join(ic.ROOT, f"covers/zoom/{key}-{sec}.jpg"), turn=manual["rotate"].get(it["path"], 0))
        ed["covers"][sec] = big
        ed.setdefault("texts", {})[sec] = ic.cover_text(text)
        ed.setdefault("source", {})[sec] = ("thumb:" if it.get("thumb") else "pdf:") + it["path"]
        if no_wall: ed["nowall"] = True
        ic.KNOWN_FRIDAYS.add(key)
        rows.append((tag, name, "added", key, sec))
        added += 1
        print(f"added {name}: {key} section {sec}" + (f" ({it['issue']})" if it.get("issue") else "") + (f" {p}" if p else ""), flush=True)
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
