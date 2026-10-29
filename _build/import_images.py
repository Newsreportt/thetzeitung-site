#!/usr/bin/env python3
"""Import cover images (JPEGs) into the archive.

    python3 _build/import_images.py manifest.tsv path/to/images/ [--decisions decisions.tsv] [--report report.tsv]

The manifest has one line per image: <file id> <tab> <ext> <tab> <original name> <tab> <upload date>.
Images are expected at path/to/images/<file id>.jpg. The edition date and the section come
from the original Mailchimp file name where it carries them
("2026-10-30,DI,TZE,001,R0.jpg" or "20181102_XDI_TZE_PG001.jpg"). Files the name cannot
settle are listed in the report as "check"; a decisions file (<file id> <tab> a|b|c|d|t|skip
[<tab> YYYY-MM-DD]) settles them on the next run. Covers already present in
_build/editions.json are left alone. Run _build/build.py afterwards.
"""
import json, os, re, subprocess, sys
from datetime import date
from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_covers import ROOT, ARCHIVE, WALL, DATA, to_friday, cover_text, enrich, volno_of

def ocr(im, psm=3):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        im.save(f.name)
        try:
            return subprocess.run(["tesseract", f.name, "-", "-l", "heb+eng", "--psm", str(psm)],
                                  capture_output=True, text=True, timeout=120).stdout
        finally:
            os.unlink(f.name)

def by_name(name, hint, siblings):
    """(date, section) from the Mailchimp file name; section is None when the picture
    has to be looked at. `siblings` holds the (code, page) pairs uploaded for the same date."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2}),[A-Z]+,([A-Z0-9]+),(\d+)", name)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        code, page = m.group(4), int(m.group(5))
        has_b = ("TZ1", 1) in siblings or any(c == "TZE" and 20 <= p <= 35 for c, p in siblings) \
                or ("TZE", 0) in siblings or ("TZ1", 0) in siblings
        if code == "TZE" and page == 1: return d, "a"
        if code == "TZ1" and page == 1: return d, "b"
        if code == "TZ1" and page == 0: return d, "b"          # a Yiddishe Tzeit cover filed as page 0
        if code == "TZE" and page == 0: return d, "b"
        if code == "TZE" and 20 <= page <= 35: return d, "b"   # Yiddishe Tzeit bound inside the paper
        if code == "TZ1" and 20 <= page <= 35: return d, "c"   # Chassidishe Tzeit inside the Yiddishe Tzeit
        if code == "TZ2" and page == 1: return d, "t"          # the Pesach Torah Tzeit
        if code == "TZ2" and 20 <= page <= 35: return d, "b"   # the Pesach Yiddishe Tzeit
        if code == "TZE" and page >= 36 and not has_b: return d, None   # back page, or the Yiddishe Tzeit: look
        return d, "skip"                                        # an inside page
    m = re.match(r"^(\d{4})(\d{2})(\d{2})[_-]XDI_([A-Z0-9]+)_PG(\d+)", name)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        code, page = m.group(4), int(m.group(5))
        if code == "TZE" and page == 1: return d, "a"
        if code == "TZE" and 10 < page < 60: return d, "b"
        if code == "TZE": return d, "skip"                      # the back page
        return d, None                                          # SP1 / GEN specials: look
    if hint:
        y, mo, da = map(int, hint.split("-"))
        return date(y, mo, da), None
    return None, None

def read_volno(im):
    """VOL. 32 · NO. 5 from the masthead box at the top right of a main cover."""
    box = im.crop((int(im.width * 0.55), 0, im.width, int(im.height * 0.22))).convert("L")
    box = box.resize((box.width * 3, box.height * 3), Image.LANCZOS)
    for psm in (11, 6, 4):
        text = ocr(box, psm=psm).replace("|", "").replace("\u00b7", " ")
        text = re.sub(r"V[O0]L", "VOL", text, flags=re.I)
        text = re.sub(r"N[O0]\.?\s*(\d)", r"NO. \1", text, flags=re.I)
        vol, no = volno_of(text)
        if vol and 25 <= vol <= 45 and no and 1 <= no <= 60: return vol, no
    return None, None

def render(im, out_big, out_small):
    im = im.convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((3, 3)))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
    if box and (box[2] - box[0]) > im.width * 0.8 and (box[3] - box[1]) > im.height * 0.8:
        pad = 4
        im = im.crop((max(box[0]-pad, 0), max(box[1]-pad, 0), min(box[2]+pad, im.width), min(box[3]+pad, im.height)))
    if im.width > 900: im = im.resize((900, round(900 * im.height / im.width)), Image.LANCZOS)
    im.save(out_big, quality=84, optimize=True, progressive=True)
    im.resize((320, round(320 * im.height / im.width)), Image.LANCZOS).save(out_small, quality=76, optimize=True)
    return im

def main(manifest, imgdir, decisions_path=None, report=None):
    data = json.load(open(DATA, encoding="utf-8")) if os.path.exists(DATA) else {}
    rows = [l.rstrip("\n").split("\t") for l in open(manifest, encoding="utf-8") if l.strip()]
    decided = {}
    if decisions_path and os.path.exists(decisions_path):
        for l in open(decisions_path, encoding="utf-8"):
            p = l.rstrip("\n").split("\t")
            if len(p) >= 2 and p[0] and not p[0].startswith("#"):
                decided[p[0]] = (p[1].strip(), p[2].strip() if len(p) > 2 and p[2].strip() else None,
                                 p[3].strip() if len(p) > 3 else "")
    # what else was uploaded for each date, to tell a back page from a Yiddishe Tzeit cover
    siblings = {}
    for uid, ext, name, hint in rows:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}),[A-Z]+,([A-Z0-9]+),(\d+)", name)
        if m: siblings.setdefault(m.group(1), set()).add((m.group(2), int(m.group(3))))
    out = []
    added = 0
    for uid, ext, name, hint in rows:
        path = os.path.join(imgdir, uid + ".jpg")
        if not os.path.exists(path):
            out.append((uid, name, "missing", "", "")); continue
        d, sec = by_name(name, hint, siblings.get(name[:10], set()))
        opts = ""
        if uid in decided:
            sec, d2, opts = decided[uid]
            if d2: d = date(*map(int, d2.split("-")))
        if sec == "skip":
            out.append((uid, name, "skip", d.isoformat() if d else "", "")); continue
        if not d:
            out.append((uid, name, "check", "", "no date")); continue
        key = to_friday(d).isoformat()
        if sec is None:
            out.append((uid, name, "check", key, "")); continue
        im = Image.open(path); im.load()
        if "rot=cw" in opts: im = im.rotate(-90, expand=True)
        if "rot=ccw" in opts: im = im.rotate(90, expand=True)
        if im.width < 500 or im.height < 500 or im.height < im.width * 0.9:
            out.append((uid, name, "small", key, sec)); continue
        ed = data.setdefault(key, {"date": key, "vol": None, "no": None, "parsha": None, "covers": {}})
        if sec in ed["covers"]:
            out.append((uid, name, "dup", key, sec)); continue
        big = f"covers/archive/{key}-{sec}.jpg"; small = f"covers/wall/{sec}-{key}.jpg"
        final = render(im, os.path.join(ROOT, big), os.path.join(ROOT, small))
        ed["covers"][sec] = big
        if sec == "a" and not ed.get("no"):
            vol, no = read_volno(final)
            if vol: ed["vol"], ed["no"], ed["volno_read"] = vol, no, True
        ed.setdefault("texts", {})[sec] = cover_text(ocr(final.convert("L")))
        ed.setdefault("source", {})[sec] = f"mailchimp:{name}"
        out.append((uid, name, "added", key, sec))
        added += 1
        print(f"added {name}: {key} section {sec}", flush=True)
    enrich(data)
    json.dump(dict(sorted(data.items())), open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            for row in out: f.write("\t".join(row) + "\n")
    from collections import Counter
    print(Counter(r[2] for r in out))
    print(f"{added} covers added; {len(data)} editions in {os.path.relpath(DATA, ROOT)}")

if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {}
    for flag in ("--decisions", "--report"):
        if flag in args:
            i = args.index(flag); opts[flag] = args[i + 1]; del args[i:i + 2]
    main(args[0], args[1], decisions_path=opts.get("--decisions"), report=opts.get("--report"))
