"""Walk public Drive folders through the embedded folder view (no sign-in needed), pick the cover
files of every issue and keep only their first page.

Per issue folder one main cover is chosen, by preference: a page-1 file (…_PG001.pdf, 1.pdf,
01.pdf, 1,65-67.pdf), a file named cover/front, "Section A.pdf" (whole section), or the whole
paper (full.pdf). "Section B/C/D.pdf" are taken as well: their first pages are the covers of the
Yiddishe Tzeit and the other supplements. Each PDF is downloaded, its first page rendered and
its text read, then the PDF is deleted. Writes out/listing.json, out/<tag>.jpg, <tag>-zoom.jpg, <tag>.txt.

The work resumes: an out/selected.json from an earlier round is reused instead of crawling again
(unless job.json's "selection" number changed: then the folders are crawled again and the
selection renewed without moving the tags of files already fetched), and covers already rendered
are skipped. Google allows an anonymous address only so many gigabytes of downloads before it
throttles; when that happens the round fetches Drive's own first-page thumbnails (1024px, no
text layer) for whatever is left, as <tag>.thumb.jpg, and leaves ../again as a marker so the
workflow starts another round from a fresh runner, which tries the PDFs again.
"""
import html, json, os, re, subprocess, sys, time, urllib.request
import concurrent.futures, threading

job = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
AGAIN = os.path.join(os.path.dirname(os.path.abspath(out)), "again")
if os.path.exists(AGAIN): os.remove(AGAIN)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def fetch(url, tries=5, binary=False):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(3 + 5 * i)
    raise err

failed_folders = []
def children(folder_id):
    """The entries of a folder. A real folder view always carries the flip-entries list, even when
    empty; anything else (access denied while sharing spreads, an error page) is retried."""
    for attempt in range(7):
        try: page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}#list")
        except Exception: page = ""
        if "flip-entries" in page or 'id="entry-' in page: break
        time.sleep((10, 20, 40, 60, 90, 120, 120)[attempt])
    else:
        failed_folders.append(folder_id); print("folder could not be read:", folder_id, flush=True); return []
    items, seen = [], set()
    for m in re.finditer(r'id="entry-([\w-]+)"', page):
        fid = m.group(1)
        if fid in seen: continue
        seen.add(fid)
        seg = page[m.end(): m.end() + 3000]
        href = re.search(r'href="([^"]+)"', seg)
        title = re.search(r'flip-entry-title">(.*?)</div>', seg, re.S)
        name = html.unescape(title.group(1)).strip() if title else ""
        is_folder = bool(href and ("/folders/" in href.group(1) or "embeddedfolderview" in href.group(1)))
        items.append((fid, name, is_folder))
    return items

CODE_KIND = {"tze": ("a", 7), "tz1": ("b", 6), "tz2": ("d", 6), "gen": ("g", 5), "sp1": ("s", 5)}
def kind_of(name):
    """(kind, preference) of a file by its name: a = the main cover, b/c/d/e = a whole section whose
    first page is a supplement's cover, g/s = the GEN and SP1 specials of 5778-5779 (the importer
    reads the section off the page)."""
    n = name.lower().strip()
    if not n.endswith(".pdf"): return None, 0
    m = re.search(r"_xdi_([a-z0-9]+)_pg0*1\.pdf$", n)
    if m: return CODE_KIND.get(m.group(1), ("a", 6))
    if re.search(r"_pg0*1\.pdf$", n): return "a", 6
    if re.match(r"^0*1(?=[\s,.\-]|\.pdf$)(?:[\s,.\-]+(?:color|\d+))*\.pdf$", n): return "a", 5   # 1.pdf, 01 color.pdf, 1,65-67.pdf
    if re.match(r"^(cover|front|shaar)", n): return "a", 4
    m = re.match(r"^\d\d-\d\d([a-e])\.pdf$", n)                               # 31-02a.pdf: whole section A
    if m: return m.group(1), 3 if m.group(1) == "a" else 5
    m = re.match(r"^sect\w{0,3}\s*([a-e])(?:[\s\-_]*[a-e])?(?=[\s.\-_(\d])", n)   # Section A.pdf, Section A-B, Secton A, Section C Sup
    if m: return m.group(1), 3 if m.group(1) == "a" else 5
    if re.match(r"^(full|whole|complete|all)[\s\d_-]*\.pdf$", n): return "a", 2
    return None, 0

issues = {}          # issue path -> {kind: (score, id, path)}
nfolders = 0
def walk(folder_id, path, issue, depth=0):
    global nfolders
    if depth > 4: return
    nfolders += 1
    for fid, name, is_folder in children(folder_id):
        if is_folder:
            if "vol38" in name.lower() or "תשפ" in name: continue        # already in the archive
            if depth >= 1 and re.fullmatch(r"\d{1,2}", name.strip()): continue   # a copy of another issue filed inside this one
            walk(fid, f"{path}/{name}", issue or (f"{path}/{name}" if depth == 0 else None), depth + 1)
            time.sleep(0.05)
        else:
            kind, score = kind_of(name)
            if not kind or not issue: continue
            cur = issues.setdefault(issue, {}).get(kind)
            if not cur or score > cur[0]: issues[issue][kind] = (score, fid, f"{path}/{name}")
    if nfolders % 50 == 0: print(f"{nfolders} folders, {len(issues)} issues so far", flush=True)

def crawl():
    for f in job["folders"]:
        walk(f["id"], f["name"], None)
    sel = [{"id": fid, "path": p, "issue": iss, "kind": k} for iss, kinds in issues.items() for k, (score, fid, p) in sorted(kinds.items())]
    print(f"crawled {nfolders} folders; {len(issues)} issues, {len(sel)} cover files; {len(failed_folders)} folders unreadable", flush=True)
    json.dump(failed_folders, open(f"{out}/denied.json", "w"))
    return sel

SELECTED = f"{out}/selected.json"; VERSION = f"{out}/selection.version"
version = str(job.get("selection", 1))
if os.path.exists(SELECTED) and os.path.exists(VERSION) and open(VERSION).read().strip() == version:
    selected = json.load(open(SELECTED, encoding="utf-8"))
    print(f"reusing the selection of an earlier round: {len(selected)} cover files", flush=True)
elif os.path.exists(SELECTED):
    # the rules changed: crawl again, but keep every earlier file at its position so the tags of
    # covers already rendered stay valid; files no longer chosen are skipped, new ones appended
    selected = json.load(open(SELECTED, encoding="utf-8"))
    fresh = {it["id"]: it for it in crawl()}
    kept = dropped = 0
    for it in selected:
        if it["id"] in fresh:
            it.update(fresh.pop(it["id"])); it.pop("skip", None); kept += 1
        elif failed_folders:
            pass                                   # the crawl missed folders: keep the old choice
        else:
            it["skip"] = True; dropped += 1; print("dropped:", it["path"], flush=True)
    for it in fresh.values(): print("added:", it["path"], flush=True)
    selected += list(fresh.values())
    print(f"selection renewed: {kept} files kept, {dropped} dropped, {len(fresh)} added", flush=True)
else:
    selected = crawl()
json.dump(selected, open(SELECTED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(VERSION, "w").write(version)

# what earlier rounds already rendered
previous = {}
if os.path.exists(f"{out}/listing.json"):
    for rec in json.load(open(f"{out}/listing.json", encoding="utf-8")):
        previous[rec["tag"]] = rec
def rendered(tag):
    return all(os.path.exists(f"{out}/{tag}{s}") for s in (".jpg", "-zoom.jpg", ".txt"))

THROTTLE = re.compile(r"many accesses|Cannot retrieve the public link|Too many users|unusual traffic|Too many requests|429", re.I)
lock = threading.Lock()
stop = threading.Event()
listing, consecutive = [], 0

def download(fid, pdf):
    """(ok, error text, throttled?)"""
    try:
        r = subprocess.run(["gdown", "--quiet", "--continue", fid, "-O", pdf], capture_output=True, text=True, timeout=420)
        err = (r.stderr or "")[-300:]
    except subprocess.TimeoutExpired:
        err = "timeout"
    if os.path.exists(pdf) and os.path.getsize(pdf) > 1000:
        if open(pdf, "rb").read(5) == b"%PDF-": return True, "", False
        err = "not a pdf: " + repr(open(pdf, "rb").read(80))
    if os.path.exists(pdf): os.remove(pdf)
    return False, err, bool(THROTTLE.search(err))

def grab(i, it):
    global consecutive
    tag = f"{i:05d}"; pdf = f"{out}/{tag}.pdf"
    if it.get("skip"): return                    # no longer chosen by the rules
    if rendered(tag):
        with lock:
            rec = previous.get(tag) or {"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": True}
            rec["rendered"] = True; rec.pop("thumb", None); listing.append(rec)
        return
    if stop.is_set(): return                     # left for the next round (and for the thumbnails below)
    rec = {"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": False, "rendered": False}
    t0 = time.time(); throttled = False
    for attempt in range(2):
        ok, err, throttled = download(it["id"], pdf)
        if ok: rec["ok"] = True; break
        if stop.is_set(): break
        time.sleep(60 if throttled else 8)       # a short throttle passes; a long one ends the round below
    rec["seconds"] = round(time.time() - t0)
    if rec["ok"]:
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        rec["pages"] = next((int(l.split()[-1]) for l in info.splitlines() if l.startswith("Pages:")), 0)
        rec["bytes"] = os.path.getsize(pdf)
        subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, f"{out}/{tag}.txt"], timeout=300)
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-jpeg", "-jpegopt", "quality=88", "-singlefile", pdf, f"{out}/{tag}"], timeout=300)
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "200", "-jpeg", "-jpegopt", "quality=85", "-singlefile", pdf, f"{out}/{tag}-zoom"], timeout=300)
        if not os.path.exists(f"{out}/{tag}.txt"): open(f"{out}/{tag}.txt", "w").close()
        rec["rendered"] = os.path.exists(f"{out}/{tag}.jpg")
        os.remove(pdf)
        for s in (".thumb.jpg",):                # the real page replaces a thumbnail
            if os.path.exists(f"{out}/{tag}{s}"): os.remove(f"{out}/{tag}{s}")
    else:
        rec["error"] = err
    with lock:
        if rec["ok"]: consecutive = 0
        elif throttled:
            consecutive += 1
            if consecutive >= 2 and not stop.is_set():
                stop.set(); print("throttled by Google: no more PDFs this round", flush=True)
        if rec["ok"] or not throttled: listing.append(rec)   # a throttled file is tried again next round
        print(f"{len(listing)}/{len(selected)} {'ok' if rec['rendered'] else 'FAIL'} {rec['seconds']}s {rec.get('bytes', 0)//1000000}MB {it['path']}" + (f"  [{err}]" if not rec["ok"] else ""), flush=True)
        if len(listing) % 20 == 0: json.dump(sorted(listing, key=lambda r: r["tag"]), open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    list(ex.map(lambda a: grab(*a), enumerate(selected, 1)))

# Drive's own first-page thumbnails for whatever the PDF budget did not cover (1024px wide, no text)
have = {r["tag"] for r in listing}
left = [(i, it) for i, it in enumerate(selected, 1) if not it.get("skip") and f"{i:05d}" not in have]
thumbs = 0
def thumb(i, it):
    global thumbs
    tag = f"{i:05d}"; path = f"{out}/{tag}.thumb.jpg"
    if os.path.exists(path): return True
    try:
        data = fetch(f"https://drive.google.com/thumbnail?id={it['id']}&sz=w1024", tries=3, binary=True)
    except Exception as e:
        print(f"thumb FAIL {it['path']} [{str(e)[:80]}]", flush=True); return False
    if data[:3] != b"\xff\xd8\xff" and data[:8] != b"\x89PNG\r\n\x1a\n":
        print(f"thumb FAIL {it['path']} [not an image: {data[:40]!r}]", flush=True); return False
    open(path, "wb").write(data)
    with lock:
        thumbs += 1
        if thumbs % 25 == 0: print(f"{thumbs} thumbnails", flush=True)
    return True
if left:
    print(f"fetching thumbnails for the {len(left)} covers still without a page", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(lambda a: thumb(*a), left))
    print(f"{thumbs} thumbnails fetched", flush=True)
# thumbnails stand in the listing until the real page arrives
for i, it in left:
    tag = f"{i:05d}"
    if os.path.exists(f"{out}/{tag}.thumb.jpg"):
        listing.append({"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": False, "rendered": False, "thumb": True})
listing.sort(key=lambda r: r["tag"])
json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
done = sum(1 for l in listing if l.get("rendered"))
nthumb = sum(1 for l in listing if l.get("thumb"))
print(f"done: {done} rendered of {len(selected)}; {nthumb} only as thumbnails; {len(listing) - done - nthumb} failed; {len(left)} left for another round", flush=True)
if left:
    fetched = sum(1 for l in listing if l.get("rendered") and "seconds" in l)      # PDFs fetched this round
    open(AGAIN, "w").write(f"{len(left)} {fetched}\n")
