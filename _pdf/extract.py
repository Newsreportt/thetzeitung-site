"""Read the words out of the PDFs in the bucket, page by page, for the archive's search.

Every issue PDF (pdf/<date>.pdf in R2) is fetched, pdftotext reads each page, the Yiddish is
straightened out — a coded font, a layer stored the way the page looks rather than the way it
reads — and the result goes back into the bucket as text/<date>.json.gz
— {"date", "pages": [{"n": 1, "t": "…"}, …]}. _pdf/index.py builds the search index from those.
Fetching and reading is the slow part, so it is done once and kept.

  python3 _pdf/extract.py --probe 24       # a sample: how much of the archive has readable text
  python3 _pdf/extract.py [--hours 5] [--limit N] [--redo] [--only 2015]
"""
import gzip, json, os, re, subprocess, sys, tempfile, time, random, statistics, collections

import boto3
from botocore.exceptions import ClientError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_build"))
import import_covers as ic

HEB = re.compile(r"[א-ת]")
WORD = re.compile(r"[א-ת]{2,}")
BIDI = re.compile(r"[‎‏‪-‮⁦-⁩]")
# Everyday Yiddish: how a reading of the text layer is judged. A page of the paper is full of them.
COMMON = re.compile(r"(?<![א-ת])(און|אין|פון|מיט|אויף|נאך|פאר|דער|די|דאס|דעם|זיך|זיין|האט|האבן|"
                    r"וועט|וועלן|איז|זענען|נישט|ווי|אז|אויך|ווערט|געווען|אלע|ביי|וואס|וועלכע|"
                    r"יאר|טאג|גאר|שוין|נאר|מען|זיי|ער|עס|אים|איר|דארט|דא|גאנץ|גרויס)(?![א-ת])")

FINAL_END = re.compile(r"(?<![א-ת])[א-ת]+[ךםןףץ](?![א-ת])")

LEFTOVER = re.compile(r"[ -ÿ]")

def score(text):
    """How much this reads like Yiddish: everyday words count most, a word ending in a final
    letter is the next sign that the letters are the right way round, and every character still
    sitting outside the alphabet counts against it — a font read with the wrong shift leaves
    those behind."""
    return len(COMMON.findall(text)) * 6 + len(FINAL_END.findall(text)) * 2 - len(LEFTOVER.findall(text))

def orient(text):
    """A page can hold both kinds of line: a headline set in a coded font, stored the way the
    page looks, beside a line of ordinary Hebrew already in reading order. Each line is turned
    round on its own, and a line that gives no sign either way follows the rest of the page."""
    lines = text.splitlines()
    turn_page = sum(score(l[::-1]) for l in lines) > sum(score(l) for l in lines)
    out = []
    for l in lines:
        if not HEB.search(l): out.append(l); continue
        a, b = score(l), score(l[::-1])
        out.append(l[::-1] if (b > a or (a == b and turn_page)) else l)
    return "\n".join(out)

# The paper's own fonts carry the alphabet as a plain run of codes — the letter's place in this
# order plus a number that differs from font to font. Finals come before the letter they close.
ALEFBEIS = "אבגדהוזחטיךכלםמןנסעףפץצקרשת"
OFFSETS = range(0x90, 0xE2)

def shift(text, off):
    """Read a coded font: every character that lands inside the alphabet becomes its letter."""
    return "".join(ALEFBEIS[o] if 0 <= (o := ord(c) - off) < len(ALEFBEIS) else c for c in text)

def font_offsets(text, keep=4):
    """Which shifts this page's fonts use. A page can hold several — a headline font beside the
    body font — so the shifts that bring the most characters inside the alphabet are shortlisted
    first (that is only arithmetic), and the few that then read most like Yiddish are kept."""
    hist = [0] * 0x100
    for ch in text:
        if 0x80 <= (o := ord(ch)) < 0x100: hist[o] += 1
    run = [0] * (0x101)
    for i, v in enumerate(hist): run[i + 1] = run[i] + v
    cover = sorted(((run[min(off + len(ALEFBEIS), 0x100)] - run[off], off) for off in OFFSETS), reverse=True)
    if not cover or cover[0][0] < 20: return []
    sample = text[:4000]
    ranked = sorted(((max(score(s := shift(sample, o)), score(mirror(s))), o) for _, o in cover[:8]), reverse=True)
    return [o for _, o in ranked[:keep]]

def mirror(text):
    return "\n".join(line[::-1] for line in text.splitlines())

def read_lines(text, offs):
    """Line by line: as it comes or through one of the page's fonts, whichever reads best."""
    out = []
    for line in text.splitlines():
        best, s = line, score(line) if HEB.search(line) else 0
        for cand in [line] + [shift(line, o) for o in offs]:
            for t in (cand, cand[::-1]):
                if (v := score(t)) > s: best, s = t, v
        out.append(best)
    return "\n".join(out)

def best_reading(text):
    """Which way of reading this page's text layer gives real Yiddish: as it comes, through the
    coded fonts the page uses, or off a Hebrew keyboard — each then turned the right way round
    line by line. The reading that comes out most like Yiddish is kept."""
    text = BIDI.sub("", text)
    best, best_score, letters = text, -1, -1
    offs = font_offsets(text)
    for read in (lambda t: t, ic.decode_glyphs, ic.decode_keyboard, lambda t: read_lines(t, offs)):
        try: cand = orient(read(text))
        except Exception: continue
        s, h = score(cand), len(HEB.findall(cand))
        if s > best_score or (s == best_score == 0 and h > letters): best, best_score, letters = cand, s, h
    return best

args = sys.argv[1:]
def opt(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default
PROBE = int(opt("--probe", 0)); ONLY = opt("--only"); REDO = "--redo" in args; DUMP = opt("--dump")
HEADS = opt("--heads")
LIMIT = int(opt("--limit", 0)); HOURS = float(opt("--hours", 5.0))
T0 = time.time()

s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  region_name="auto", aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
BUCKET = os.environ["R2_BUCKET"]

def have(key):
    try:
        s3.head_object(Bucket=BUCKET, Key=key); return True
    except ClientError:
        return False

# What the page says in plain letters and figures: a telephone number, an advertiser's name in
# English, a year. These come from the layer as it stands — the fonts' own decoding shifts the
# Latin alphabet by 29 and would turn 2026 into OMOS — so they are read off the raw page and set
# down beside the straightened Yiddish.
PLAIN = re.compile(r"[A-Za-z][A-Za-z'&.]+[A-Za-z]|\d{3,}(?:[-.\u2013/]\d{3,})*")

def plain_of(raw):
    seen, out = set(), []
    for w in PLAIN.findall(raw):
        k = w.lower()
        if k not in seen: seen.add(k); out.append(w)
    return " ".join(out)

# ---- the headlines -----------------------------------------------------------------------------
# A reader looking for an article is looking for its headline, not for a word somewhere in the
# ninth paragraph. pdftotext can hand over every line with the box it sits in, and a headline is
# what it looks like: a line set far larger than the page's own body type.
HEAD_RATIO = 1.7       # how much larger than the body type a line must be set
HEAD_MIN_LETTERS = 7   # shorter than this is a page number, a date, a column rule

def page_lines(pdf):
    """Every line of every page with the size of the type it is set in. pdftotext hands over the
    words but not how large they stand; the page's own structure does, and a headline is a line
    set far larger than the body type around it."""
    try: import pymupdf
    except ImportError: import fitz as pymupdf
    doc = pymupdf.open(pdf)
    pages = []
    for page in doc:
        lines = []
        try: d = page.get_text("dict")
        except Exception: d = {"blocks": []}
        for b in d.get("blocks", []):
            for ln in b.get("lines", []):
                text = "".join(sp.get("text", "") for sp in ln.get("spans", []))
                if not text.strip(): continue
                size = max((sp.get("size", 0) for sp in ln.get("spans", [])), default=0)
                lines.append((float(size), text))
        pages.append(lines)
    doc.close()
    return pages

def head_score(t, vocab):
    """How much a headline reads like one. Counting Hebrew letters is no help — a wrong shift
    turns one coded font into Hebrew letters just as readily as the right one — so the words
    are weighed against the issue's own body text, which is read well. A headline shares its
    words with the article underneath it."""
    words = WORD.findall(t)
    known = sum(1 for w in words if w in vocab)
    return (known * 12 + len(COMMON.findall(t)) * 6 + len(FINAL_END.findall(t)) * 2
            + len(HEB.findall(t)) * 0.1 - len(LEFTOVER.findall(t)) * 3)

def best_line(text, vocab=frozenset(), offs=()):
    """One line, read every way the paper sets its type. A headline is set in a display font of
    its own, which the issue's body type says nothing about, so rather than guess the font every
    shift is tried: there are eighty-two of them and a headline is a handful of words."""
    text = BIDI.sub("", text)
    cands = [text, ic.decode_glyphs(text), ic.decode_keyboard(text)]
    cands += [shift(text, o) for o in OFFSETS]
    for o in offs: cands.append(shift(text, o))
    best, score_best = text, -1e9
    for c in cands:
        for t in (c, c[::-1]):
            v = head_score(t, vocab)
            if v > score_best: best, score_best = t, v
    return best

def headlines_of(lines, vocab=frozenset(), offs=()):
    """The lines of a page that are set as headlines, read the right way round. The page's own
    fonts are worked out from the whole issue — a headline is a few words, far too little to
    tell one coded font from another on its own."""
    sizes = [h for h, _ in lines if h > 0]
    if len(sizes) < 4: return []
    body = statistics.median(sizes)
    if not body: return []
    out, seen = [], set()
    for h, text in lines:
        if h < body * HEAD_RATIO: continue
        read = re.sub(r"\s+", " ", best_line(text, vocab, offs)).strip()
        words = WORD.findall(read)
        if len(HEB.findall(read)) < HEAD_MIN_LETTERS: continue          # not Yiddish enough
        if len(LEFTOVER.findall(read)) > len(read) / 8: continue        # still gibberish
        # and a headline whose words are strangers to the whole issue was not read right
        if vocab and words:
            known = sum(1 for w in words if w in vocab)
            if len(words) >= 3:
                if known < 2 or known * 2 < len(words): continue
            elif known < len(words): continue
        if read in seen: continue
        seen.add(read); out.append(read)
    return out

# The paper's own furniture — the masthead over each page, the section's name, "continued on" —
# stands in the same large type as a headline and says nothing about any article. What comes up
# again and again through one issue is furniture.
FURNITURE_PAGES = 3

def vocabulary(texts):
    """Every word the issue's own body text is made of — what a rightly read headline looks like."""
    seen = collections.Counter()
    for t in texts: seen.update(WORD.findall(t))
    # a word the issue uses only once may itself be a misreading; twice is a word
    return frozenset(w for w, n in seen.items() if len(w) >= 3 and n >= 2)

def issue_headlines(pages, body=()):
    """Every page's headlines, with what repeats through the issue thrown out."""
    vocab = vocabulary(body)
    offs_all = font_offsets("\n".join(t for lines in pages for _, t in lines)[:40000], keep=6)
    per = [headlines_of(lines, vocab, offs_all) for lines in pages]
    seen = collections.Counter(h for hs in per for h in set(hs))
    return [[h for h in hs if seen[h] < FURNITURE_PAGES] for hs in per]

def heads(date):
    """What this issue's headlines come out as — for seeing whether the catch is right."""
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "x.pdf"); s3.download_file(BUCKET, f"pdf/{date}.pdf", pdf)
        pages = page_lines(pdf)
        body = read_pages(pdf)
    per = issue_headlines(pages, body)
    print(f"{date}: {len(pages)} pages, {sum(len(l) for l in pages)} lines, "
          f"{sum(len(h) for h in per)} headlines", flush=True)
    for i, hs in enumerate(per[:20]):
        if not hs: continue
        print(f"\n--- page {i + 1} ---", flush=True)
        for h in hs[:8]: print("   ", h[:150], flush=True)

def read_pages(pdf):
    """The text of each page, straightened out. Pages pdftotext cannot read come back empty."""
    # one issue in 2010 carries a byte that is no part of its own declared encoding; a page is
    # worth having with one character lost, so what cannot be decoded is let through as it is
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", pdf, "-"], capture_output=True,
                         text=True, errors="replace", timeout=1200).stdout
    pages = out.split("\f")[:-1] or [out]
    done = []
    for p in pages:
        plain = plain_of(BIDI.sub("", p))
        done.append(best_reading(p) + ("\n" + plain if plain else ""))
    return done

def pdf_pages(date, dest):
    s3.download_file(BUCKET, f"pdf/{date}.pdf", dest)
    return read_pages(dest)

def store(date, pages):
    body = gzip.compress(json.dumps({"date": date, "pages": pages}, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8"), 6)
    s3.put_object(Bucket=BUCKET, Key=f"text/{date}.json.gz", Body=body,
                  ContentType="application/json", ContentEncoding="gzip")
    return len(body)

def dump(date):
    """One issue, a page at a time: what pdftotext hands over and what each reading makes of it."""
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "x.pdf"); s3.download_file(BUCKET, f"pdf/{date}.pdf", pdf)
        raw = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", pdf, "-"], capture_output=True,
                             text=True, errors="replace", timeout=1200).stdout
    pages = raw.split("\f")[:-1]
    print(f"{date}: {len(pages)} pages")
    shown = 0
    for i, pg in enumerate(pages):
        if len(HEB.findall(pg)) < 200: continue
        print(f"\n--- page {i + 1} ---")
        clean = BIDI.sub("", pg)
        for name, t in [("as it comes", clean), ("glyphs", ic.decode_glyphs(clean)),
                        ("glyphs oriented", orient(ic.decode_glyphs(clean))),
                        ("keyboard", ic.decode_keyboard(clean)), ("CHOSEN", best_reading(pg))]:
            flat = re.sub(r"\s+", " ", t).strip()
            print(f"  {name:16s} heb {len(HEB.findall(t)):5d}  everyday {len(COMMON.findall(t)):4d}  score {score(t):5d}")
            print(f"      {flat[:170]}")
        if shown >= 2: break
        shown += 1

def probe(n):
    """A sample spread over the years: how many pages carry words, and do they read right."""
    dates = sorted(json.load(open(os.path.join(ROOT, "pdfs.json"), encoding="utf-8")))
    step = max(1, len(dates) // n)
    sample = dates[::step][:n]
    rows = []
    for date in sample:
        with tempfile.TemporaryDirectory() as td:
            try:
                pages = pdf_pages(date, os.path.join(td, "x.pdf"))
            except Exception as ex:
                print(f"{date}: could not be read — {ex}", flush=True); continue
        words = [len(WORD.findall(p)) for p in pages]
        withtext = sum(1 for w in words if w >= 20)
        allw = " ".join(pages)
        common = len(re.findall(r"(?<![א-ת])(און|אין|פון|מיט|אויף|נאך|דער|די|דאס)(?![א-ת])", allw))
        rows.append((date, len(pages), withtext, sum(words), common))
        print(f"{date}: {len(pages):3d} pages, {withtext:3d} with words, {sum(words):6d} words, "
              f"{common:5d} everyday words{'   ← no text layer' if withtext == 0 else ''}", flush=True)
    if not rows: return
    pages = sum(r[1] for r in rows); good = sum(r[2] for r in rows)
    print(f"\n{len(rows)} issues, {pages} pages: {good} ({100 * good / pages:.0f}%) carry words.")
    print(f"median words a page: {statistics.median([r[3] / max(1, r[1]) for r in rows]):.0f}")
    dead = [r[0] for r in rows if r[2] == 0]
    if dead: print(f"{len(dead)} issues with no text layer at all, e.g. {dead[:6]}")

def main():
    public = json.load(open(os.path.join(ROOT, "pdfs.json"), encoding="utf-8"))
    dates = sorted(d for d in public if not ONLY or d.startswith(ONLY))
    done = skipped = failed = 0; left = 0
    for date in dates:
        if not REDO and have(f"text/{date}.json.gz"): skipped += 1; continue
        if time.time() - T0 > HOURS * 3600 or (LIMIT and done >= LIMIT): left += 1; continue
        try:
            with tempfile.TemporaryDirectory() as td:
                pages = pdf_pages(date, os.path.join(td, "x.pdf"))
            keep = [{"n": i + 1, "t": t} for i, t in enumerate(pages) if len(WORD.findall(t)) >= 5]
            size = store(date, keep)
            words = sum(len(WORD.findall(p["t"])) for p in keep)
            done += 1
            print(f"{date}: {len(pages):3d} pages, {len(keep):3d} with words, {words:6d} words, {size // 1024} KB", flush=True)
        except Exception as ex:
            failed += 1; print(f"{date}: FAILED — {ex}", flush=True)
    print(f"{done} read, {skipped} already done, {failed} failed, {left} left for the next run")
    open(os.path.join(ROOT, "_pdf", "again"), "w").write(f"{left}\n")

if __name__ == "__main__":
    if HEADS: heads(HEADS)
    elif DUMP: dump(DUMP)
    elif PROBE: probe(PROBE)
    else: main()
