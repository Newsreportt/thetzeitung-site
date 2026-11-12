"""Build the PDF archive for the shop: every issue folder of the office's Google Drive ("News
Report old": Vol N / NN / the section or page PDFs) becomes one PDF of the whole paper in the
R2 bucket, pdf/<date>.pdf, and pdfs.json at the site root says which editions exist.

Runs in GitHub Actions (.github/workflows/pdf-archive.yml) with
  GDRIVE_SA_JSON   a Google service account key (JSON); the Drive folder is shared with it, read-only
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET   the Cloudflare R2 bucket
and _pdf/job.json (the root folder id, skip rules). The issue's date comes from the archive:
_build/editions.json knows the volume and number of every edition.

  python3 _pdf/archive.py [--only "Vol 39"] [--redo] [--limit N] [--hours H]
"""
import io, json, os, re, sys, time, tempfile, subprocess, traceback
import requests
import pypdf
from pypdf import PdfReader, PdfWriter
import boto3

# pypdf guards against a hostile PDF declaring an enormous stream; the office's own pages can
# carry a picture larger than its 75 MB default, so the guard is raised rather than tripped over.
# pypdf 7 moved the setting out of pypdf.filters into Configuration.
def _raise_stream_limit(limit=600_000_000):
    try:
        from pypdf import Configuration
        Configuration.maximum_declared_stream_length = limit; return "Configuration"
    except ImportError:
        pass
    try:
        import pypdf.filters
        pypdf.filters.MAX_DECLARED_STREAM_LENGTH = limit; return "pypdf.filters"
    except Exception as ex:
        return f"not raised ({ex})"
print(f"pypdf {pypdf.__version__}, stream limit via {_raise_stream_limit()}", flush=True)
from google.oauth2 import service_account
from google.auth.transport.requests import Request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOB = json.load(open(os.path.join(ROOT, "_pdf", "job.json"), encoding="utf-8"))
PUBLIC = os.path.join(ROOT, "pdfs.json")              # what the site and the shop read
MANIFEST = os.path.join(ROOT, "_pdf", "manifest.json")  # the same, with the files each PDF was made of
EDITIONS = json.load(open(os.path.join(ROOT, "_build", "editions.json"), encoding="utf-8"))
FOLDER = "application/vnd.google-apps.folder"

args = sys.argv[1:]
def opt(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default
ONLY = opt("--only"); REDO = "--redo" in args; LIMIT = int(opt("--limit", 0)); HOURS = float(opt("--hours", 5.2))
T0 = time.time()

# ---- Google Drive, read-only, as the service account ----------------------------------------
creds = None
def token():
    global creds
    if creds is None:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(os.environ["GDRIVE_SA_JSON"]), scopes=["https://www.googleapis.com/auth/drive.readonly"])
    if not creds.valid: creds.refresh(Request())
    return creds.token
S = requests.Session()
def api(path, **params):
    for attempt in range(6):
        r = S.get("https://www.googleapis.com/drive/v3/" + path, params=params, headers={"Authorization": "Bearer " + token()}, timeout=120)
        if r.status_code in (429, 500, 502, 503): time.sleep(2 ** attempt); continue
        r.raise_for_status(); return r.json()
    r.raise_for_status()
def children(fid):
    out, page = [], None
    while True:
        res = api("files", q=f"'{fid}' in parents and trashed = false", fields="nextPageToken, files(id, name, mimeType, size)",
                  pageSize=1000, pageToken=page, supportsAllDrives="true", includeItemsFromAllDrives="true")
        out += res.get("files", []); page = res.get("nextPageToken")
        if not page: return out
def download(fid, dest):
    for attempt in range(5):
        with S.get(f"https://www.googleapis.com/drive/v3/files/{fid}", params={"alt": "media", "supportsAllDrives": "true"},
                   headers={"Authorization": "Bearer " + token()}, stream=True, timeout=600) as r:
            if r.status_code in (429, 500, 502, 503): time.sleep(3 * (attempt + 1)); continue
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 20): f.write(chunk)
            return
    raise RuntimeError("download failed " + fid)

# ---- the issue folders and their editions ----------------------------------------------------
by_volno = {}
for k, e in EDITIONS.items():
    if e.get("vol") and e.get("no"): by_volno.setdefault((int(e["vol"]), int(e["no"])), []).append(k)

def pdfs_under(fid, depth=0):
    """Every PDF below an issue folder, with the folder path it sits in."""
    out = []
    for f in children(fid):
        if f["mimeType"] == FOLDER:
            if depth < 3: out += [(p, (f["name"] + "/" + path) if path else f["name"]) for p, path in pdfs_under(f["id"], depth + 1)]
        elif f["mimeType"] == "application/pdf" or f["name"].lower().endswith(".pdf"):
            out.append((f, ""))
    return out

SKIP = [re.compile(p, re.I) for p in JOB.get("skip", [])]

QUALIFIER = re.compile(r"(?i)\b(colou?r|bw|b&w|new|final|copy|done|pix)\b")
RANGE = re.compile(r"\d+\s*[-–,]\s*\d+")              # '(26-27)', '(1-16, 65-80)': several pages

def section_of(name):
    """The section a file belongs to, and its page number when the file is a single page:
    'Section A 53.pdf' -> ('A', 53), '02 color.pdf' -> ('', 2), 'Sup - part of B - 7.pdf' -> ('B', 7),
    'Section A (1).pdf' -> ('A', 1), 'Section A (26-27).pdf' -> ('A', None) (a spread),
    '39-01A.pdf' -> ('A', None), 'Section A-B.pdf' -> ('A-B', None), 'full.pdf' -> ('', None)."""
    n = re.sub(r"\.pdf$", "", name, flags=re.I).replace("_", " ")
    n = QUALIFIER.sub(" ", n)
    sec = ""
    m = re.search(r"(?i)\b(?:sec\w*|sup\w*|part\s+of)\b\.?\s*[-–]?\s*([A-Z])\s*[-–]\s*([A-Z])\b", n)
    if m: return (m.group(1).upper() + "-" + m.group(2).upper(), None)
    m = re.search(r"(?i)\b(?:sec\w*|sup\w*|part\s+of)\b\.?\s*[-–]?\s*([A-Z])\b", n) or re.search(r"\b\d\d-\d\d\s*([a-zA-Z])\b", n)
    if m: sec, n = m.group(1).upper(), n[m.end():]
    elif re.match(r"(?i)\s*sup\b", n): sec = "SUP"     # 'Sup 5.pdf': a supplement page, section unnamed
    n = re.sub(r"(?i)\bp\.?g\.?\s*(\d{1,3})\s*$", r" \1", n)   # '…_TZE_PG029.pdf' is page 29
    if RANGE.search(n): return (sec, None)             # a spread or a run of pages, not one page
    p = re.search(r"(?:^|[\s\-–(])(\d{1,3})\s*\)?\s*$", n)
    return (sec, int(p.group(1)) if p else None)

def order_key(f, path):
    """Sections in order, pages in order."""
    sec, page = section_of(f["name"])
    nums = [int(x) for x in re.findall(r"\d+", re.sub(r"\b\d\d-\d\d[a-z]?\b", "", f["name"]))]
    return (path, sec or "Z", page if page is not None else (nums[0] if nums else 0), f["name"].lower())

OWN = re.compile(r"^\d\d-\d\d[a-z]\.pdf$", re.I)      # the office's own whole-section files, 39-01a.pdf
PAGES_DIR = re.compile(r"(?i)pag")                     # 'Pages', 'PDF Full Pages/DONE', 'PDF Ful Pages'

def pick(files):
    keep = [(f, p) for f, p in files if not any(s.search(f["name"]) or s.search(p) for s in SKIP) and int(f.get("size", 0)) > 20000]
    own = [(f, p) for f, p in keep if OWN.match(f["name"])]
    if own: keep = own          # that set is the whole paper; anything else beside it is a second copy
    else:
        pages = [(f, p) for f, p in keep if PAGES_DIR.search(p)]
        if pages: keep = pages  # the paper lives in the Pages folder; what lies beside it is advertising
    return sorted(keep, key=lambda fp: order_key(*fp))

def plan(files):
    """Group an issue's PDFs by section. The same pages can sit in a folder more than once: the
    whole section (39-01A.pdf) beside its pages one by one (Section A 1.pdf … 48.pdf), or two
    subfolders holding the same thing (Pages/ and PDF Full Pages/). Each of those is a variant:
    {section letter: {variant key: [files]}}, where a variant is one subfolder's whole-section
    files, or one subfolder's single-page files."""
    groups = {}
    for f, path in files:
        sec, page = section_of(f["name"])
        groups.setdefault(sec, {}).setdefault((path, page is not None), []).append((f, path))
    return groups

def issue_folders():
    root = JOB["root"]
    vols = []
    for f in children(root):
        m = re.match(r"(?i)\s*vol\.?\s*(\d+)", f["name"]) if f["mimeType"] == FOLDER else None
        if m and (not ONLY or ONLY.lower() in f["name"].lower()): vols.append((int(m.group(1)), f))
    for vol, vf in sorted(vols):
        for f in children(vf["id"]):
            m = re.match(r"\s*(\d{1,2})\b", f["name"]) if f["mimeType"] == FOLDER else None
            if m: yield vol, int(m.group(1)), f

def main():
    public = json.load(open(PUBLIC, encoding="utf-8")) if os.path.exists(PUBLIC) else {}
    manifest = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {}
    s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", region_name="auto",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
    bucket = os.environ["R2_BUCKET"]
    done = 0; left = 0; failed = 0
    def save():
        json.dump(dict(sorted(public.items())), open(PUBLIC, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        json.dump(dict(sorted(manifest.items())), open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for vol, no, folder in issue_folders():
        keys = by_volno.get((vol, no), [])
        if len(keys) != 1:
            print(f"Vol {vol}/{no:02d} ({folder['name']}): {'no' if not keys else 'several'} edition(s) with that number {keys}; skipped"); continue
        date = keys[0]
        if date in public and not REDO: continue
        if time.time() - T0 > HOURS * 3600 or (LIMIT and done >= LIMIT): left += 1; continue
        files = pick(pdfs_under(folder["id"]))
        if not files: print(f"Vol {vol}/{no:02d} -> {date}: no PDFs; skipped"); continue
        try:
            with tempfile.TemporaryDirectory() as td:
                got = {}; seq = [0]                       # id -> (local file, page count)
                def fetch(f, path=None):
                    seq[0] += 1
                    dest = os.path.join(td, f"{seq[0]:04d}.pdf"); download(f["id"], dest)
                    try:
                        n = len(PdfReader(dest).pages)
                    except Exception as ex:
                        print(f"  unreadable {f['name']}: {ex}"); os.unlink(dest); return None
                    got[f["id"]] = (dest, n); return n
                # Every whole-section file is read first: there are few of them and their page
                # counts settle which copy of a section, and which loose pages, are the paper.
                groups = plan(files)
                for variants in groups.values():
                    for key, fs in variants.items():
                        if not key[1]:
                            for f, _ in fs: fetch(f)
                pages_of = lambda fs: sum(got.get(f["id"], (None, 0))[1] for f, _ in fs)
                drop = set()
                for sec, variants in groups.items():
                    if len(variants) < 2: continue
                    size = {k: (len(fs) if k[1] else pages_of(fs)) for k, fs in variants.items()}
                    best = max(size, key=lambda k: (size[k], not k[1]))
                    for key, fs in variants.items():
                        if key != best: drop |= {f["id"] for f, _ in fs}
                    if not best[1] and len(variants[best]) > 1:   # one file holding nearly the whole
                        pp = {f["id"]: got.get(f["id"], (None, 0))[1] for f, _ in variants[best]}
                        top = max(pp, key=pp.get)                 # section: the rest are its spreads
                        if pp[top] >= 0.8 * max(1, sum(pp.values())): drop |= set(pp) - {top}
                    kept = f"{len(variants[best])} file(s) from '{best[0] or '.'}'" + (" one page each" if best[1] else "")
                    print(f"  section {sec or '?'} is in the folder {len(variants)} times; kept {kept}, {size[best]} pages", flush=True)
                # loose pages of no named section (20151023_XDI_TZE_PG029.pdf) beside whole sections
                # that already carry as much: a second copy of the paper, or part of one
                whole_pages = sum(n for fid, (_, n) in got.items() if fid not in drop)
                loose = [f for key, fs in groups.get("", {}).items() if key[1] for f, _ in fs if f["id"] not in drop]
                if loose and whole_pages >= len(loose):
                    drop |= {f["id"] for f in loose}
                    print(f"  {len(loose)} loose page files left out; the whole sections carry {whole_pages} pages", flush=True)
                w = PdfWriter(); parts = []
                for i, (f, path) in enumerate(files):
                    if f["id"] in drop: continue
                    if f["id"] not in got and fetch(f) is None:
                        parts.append({"name": f["name"], "error": "unreadable"}); continue
                    dest, n = got.pop(f["id"])
                    try:
                        w.append(PdfReader(dest))
                    except Exception as ex:
                        print(f"  could not be merged, left out — {f['name']}: {ex}", flush=True)
                        parts.append({"name": f["name"], "error": str(ex)[:160]}); continue
                    parts.append({"name": (path + "/" if path else "") + f["name"], "pages": n, "bytes": int(f.get("size", 0))})
                out = os.path.join(td, "issue.pdf")
                w.add_metadata({"/Title": f"Di Tzeitung {date} (vol. {vol} no. {no})", "/Author": "The Tzeitung — News Report"})
                with open(out, "wb") as fh: w.write(fh)
                pages = len(PdfReader(out).pages); size = os.path.getsize(out)
                s3.upload_file(out, bucket, f"pdf/{date}.pdf", ExtraArgs={"ContentType": "application/pdf"})
        except Exception as ex:
            failed += 1
            print(f"Vol {vol}/{no:02d} -> {date}: left for later, it did not come together — {ex}", flush=True)
            traceback.print_exc(); continue
        public[date] = {"bytes": size, "pages": pages}
        manifest[date] = {"vol": vol, "no": no, "folder": folder["name"], "bytes": size, "pages": pages, "files": parts}
        done += 1
        print(f"Vol {vol}/{no:02d} -> {date}: {len(parts)} files, {pages} pages, {size / 1e6:.0f} MB" + ("   (few pages?)" if pages < 40 else ""), flush=True)
        if done % 20 == 0: save()
    save()
    print(f"{done} issues done this run, {failed} did not come together, {left} left for the next; {len(public)} PDFs in the archive")
    open(os.path.join(ROOT, "_pdf", "again"), "w").write(f"{left}\n")

if __name__ == "__main__":
    main()
