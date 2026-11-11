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
import io, json, os, re, sys, time, tempfile, subprocess
import requests
from pypdf import PdfReader, PdfWriter
import boto3
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

def section_of(name):
    """The section a file belongs to, and its page number when the file is a single page:
    'Section A 53.pdf' -> ('A', 53), 'Sec C sup.pdf' -> ('C', None), '39-01A.pdf' -> ('A', None),
    'Section A-B.pdf' -> ('A-B', None), 'Tzeitung.pdf' -> ('', None)."""
    n = re.sub(r"\.pdf$", "", name, flags=re.I).replace("_", " ")
    m = re.search(r"(?i)\b(?:sec\w*|sup\w*)\.?\s*([A-Z])\s*[-–]\s*([A-Z])\b", n)
    if m: return (m.group(1).upper() + "-" + m.group(2).upper(), None)
    m = re.search(r"(?i)\b(?:sec\w*|sup\w*)\.?\s*([A-Z])\b", n) or re.search(r"\b\d\d-\d\d\s*([a-zA-Z])\b", n)
    if not m: return ("", None)
    sec = m.group(1).upper()
    rest = n[m.end():]
    p = re.fullmatch(r"\s*(\d{1,3})\s*", rest)     # a plain page number and nothing else
    return (sec, int(p.group(1)) if p else None)

def order_key(f, path):
    """Sections in order, pages in order."""
    sec, page = section_of(f["name"])
    nums = [int(x) for x in re.findall(r"\d+", re.sub(r"\b\d\d-\d\d[a-z]?\b", "", f["name"]))]
    return (path, sec or "Z", page if page is not None else (nums[0] if nums else 0), f["name"].lower())

OWN = re.compile(r"^\d\d-\d\d[a-z]\.pdf$", re.I)      # the office's own whole-section files, 39-01a.pdf

def pick(files):
    keep = [(f, p) for f, p in files if not any(s.search(f["name"]) or s.search(p) for s in SKIP) and int(f.get("size", 0)) > 20000]
    own = [(f, p) for f, p in keep if OWN.match(f["name"])]
    if own: keep = own          # that set is the whole paper; anything else beside it is a second copy
    return sorted(keep, key=lambda fp: order_key(*fp))

def plan(files):
    """Some issue folders hold a section twice: the whole thing (39-01A.pdf) and the same pages one
    by one (Section A 1.pdf … Section A 48.pdf). Keep one of the two. Which one is settled after the
    whole-section files are read: they win when they carry at least as many pages as there are
    single-page files, and otherwise (a cover, a part of the section) the page files do."""
    groups = {}
    for f, path in files:
        sec, page = section_of(f["name"])
        g = groups.setdefault((path, sec), {"pages": [], "whole": []})
        (g["pages"] if page is not None else g["whole"]).append((f, path))
    contested = [k for k, g in groups.items() if g["pages"] and g["whole"] and len(g["pages"]) > 2]
    return groups, contested

def issue_folders():
    root = JOB["root"]
    vols = []
    for f in children(root):
        m = re.match(r"\s*Vol\s*(\d+)", f["name"]) if f["mimeType"] == FOLDER else None
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
    done = 0; left = 0
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
        with tempfile.TemporaryDirectory() as td:
            got = {}                                  # name -> (local file, page count)
            def fetch(f, path, i):
                dest = os.path.join(td, f"{i:03d}.pdf"); download(f["id"], dest)
                try:
                    n = len(PdfReader(dest).pages)
                except Exception as ex:
                    print(f"  unreadable {f['name']}: {ex}"); os.unlink(dest); return None
                got[f["id"]] = (dest, n); return n
            # a section held twice (whole file and page files): read the whole files, then drop one set
            groups, contested = plan(files)
            drop = set()
            for key in contested:
                g = groups[key]
                whole = sum(fetch(f, p, 900 + len(got)) or 0 for f, p in g["whole"])
                if whole >= len(g["pages"]):
                    drop |= {f["id"] for f, _ in g["pages"]}
                    print(f"  {key[1] or '?'}: {len(g['pages'])} page files left out, the whole section has {whole} pages")
                else:
                    drop |= {f["id"] for f, _ in g["whole"]}
                    print(f"  {key[1] or '?'}: the whole-section file(s) ({whole} pages) left out, {len(g['pages'])} page files kept")
            w = PdfWriter(); parts = []
            for i, (f, path) in enumerate(files):
                if f["id"] in drop: continue
                if f["id"] not in got and fetch(f, path, i) is None:
                    parts.append({"name": f["name"], "error": "unreadable"}); continue
                dest, n = got.pop(f["id"])
                w.append(PdfReader(dest)); parts.append({"name": (path + "/" if path else "") + f["name"], "pages": n, "bytes": int(f.get("size", 0))})
            out = os.path.join(td, "issue.pdf")
            w.add_metadata({"/Title": f"Di Tzeitung {date} (vol. {vol} no. {no})", "/Author": "The Tzeitung — News Report"})
            with open(out, "wb") as fh: w.write(fh)
            pages = len(PdfReader(out).pages); size = os.path.getsize(out)
            s3.upload_file(out, bucket, f"pdf/{date}.pdf", ExtraArgs={"ContentType": "application/pdf"})
        public[date] = {"bytes": size, "pages": pages}
        manifest[date] = {"vol": vol, "no": no, "folder": folder["name"], "bytes": size, "pages": pages, "files": parts}
        done += 1
        print(f"Vol {vol}/{no:02d} -> {date}: {len(parts)} files, {pages} pages, {size / 1e6:.0f} MB" + ("   (few pages?)" if pages < 40 else ""), flush=True)
        if done % 20 == 0: save()
    save()
    print(f"{done} issues done this run, {left} left for the next; {len(public)} PDFs in the archive")
    open(os.path.join(ROOT, "_pdf", "again"), "w").write(f"{left}\n")

if __name__ == "__main__":
    main()
