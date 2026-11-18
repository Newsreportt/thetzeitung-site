"""Read the words out of the PDFs in the bucket, page by page, for the archive's search.

Every issue PDF (pdf/<date>.pdf in R2) is fetched, pdftotext reads each page, the Yiddish is
straightened out — a coded font, a layer stored the way the page looks rather than the way it
reads — and the result goes back into the bucket as text/<date>.json.gz
— {"date", "pages": [{"n": 1, "t": "…"}, …]}. _pdf/index.py builds the search index from those.
Fetching and reading is the slow part, so it is done once and kept.

  python3 _pdf/extract.py --probe 24       # a sample: how much of the archive has readable text
  python3 _pdf/extract.py [--hours 5] [--limit N] [--redo] [--only 2015]
"""
import gzip, json, os, re, subprocess, sys, tempfile, time, random, statistics

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

def read_pages(pdf):
    """The text of each page, straightened out. Pages pdftotext cannot read come back empty."""
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", pdf, "-"],
                         capture_output=True, text=True, timeout=1200).stdout
    return [best_reading(p) for p in out.split("\f")[:-1] or [out]]

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
        raw = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", pdf, "-"],
                             capture_output=True, text=True, timeout=1200).stdout
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
    dump(DUMP) if DUMP else (probe(PROBE) if PROBE else main())
