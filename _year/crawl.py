"""Walk public Drive folders through the embedded folder view (no sign-in needed), pick the cover
files of every issue and keep only their first page.

Per issue folder one main cover is chosen, by preference: a page-1 file (…_PG001.pdf, 1.pdf,
01.pdf, 1,65-67.pdf), a file named cover/front, "Section A.pdf" (whole section), or the whole
paper (full.pdf). "Section B/C/D.pdf" are taken as well: their first pages are the covers of the
Yiddishe Tzeit and the other supplements. Each PDF is downloaded, its first page rendered and
its text read, then the PDF is deleted. Writes out/listing.json, out/<tag>.jpg, <tag>-zoom.jpg, <tag>.txt.

The work resumes: an out/selected.json from an earlier round is reused instead of crawling again,
and covers already rendered are skipped. Google throttles anonymous downloads from one address
after a while; when that happens the round stops early and leaves ../again as a marker, so the
workflow can start another round from a fresh runner.
"""
import html, json, os, re, subprocess, sys, time, urllib.request
import concurrent.futures, threading

job = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
AGAIN = os.path.join(os.path.dirname(os.path.abspath(out)), "again")
if os.path.exists(AGAIN): os.remove(AGAIN)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def fetch(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r: return r.read().decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(3 + 5 * i)
    raise err

denied = []
def children(folder_id):
    for attempt in range(6):
        page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}#list")
        if 'id="entry-' in page or ("Access Denied" not in page and "You need access" not in page): break
        time.sleep(30 * (attempt + 1))          # sharing may still be spreading through the tree
    else:
        denied.append(folder_id); print("access denied:", folder_id, flush=True); return []
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
    if re.match(r"^0*1(?:[\s,.\-]*(?:color|\d+))*\.pdf$", n): return "a", 5   # 1.pdf, 01 color.pdf, 1,65-67.pdf
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
            walk(fid, f"{path}/{name}", issue or (f"{path}/{name}" if depth == 0 else None), depth + 1)
            time.sleep(0.05)
        else:
            kind, score = kind_of(name)
            if not kind or not issue: continue
            cur = issues.setdefault(issue, {}).get(kind)
            if not cur or score > cur[0]: issues[issue][kind] = (score, fid, f"{path}/{name}")
    if nfolders % 25 == 0: print(f"{nfolders} folders, {len(issues)} issues so far", flush=True)

def crawl():
    for f in job["folders"]:
        walk(f["id"], f["name"], None)
    sel = [{"id": fid, "path": p, "issue": iss, "kind": k} for iss, kinds in issues.items() for k, (score, fid, p) in sorted(kinds.items())]
    print(f"crawled {nfolders} folders; {len(issues)} issues, {len(sel)} cover files; {len(denied)} folders denied", flush=True)
    json.dump(denied, open(f"{out}/denied.json", "w"))
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
    kept = 0
    for it in selected:
        if it["id"] in fresh:
            it.update(fresh.pop(it["id"])); it.pop("skip", None); kept += 1
        else:
            it["skip"] = True
    selected += list(fresh.values())
    print(f"selection renewed: {kept} files kept, {len(selected) - kept - len(fresh)} dropped, {len(fresh)} added", flush=True)
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
listing, throttled_files, consecutive = [], 0, 0

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
    global throttled_files, consecutive
    tag = f"{i:05d}"; pdf = f"{out}/{tag}.pdf"
    if it.get("skip"): return                    # no longer chosen by the rules
    if rendered(tag):
        with lock:
            rec = previous.get(tag) or {"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": True}
            rec["rendered"] = True; listing.append(rec)
        return
    if stop.is_set(): return                     # left for the next round
    rec = {"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": False, "rendered": False}
    t0 = time.time(); throttled = False
    for attempt in range(3):
        ok, err, throttled = download(it["id"], pdf)
        if ok: rec["ok"] = True; break
        if stop.is_set(): break
        time.sleep(90 if throttled else 8)       # a short throttle passes; a long one ends the round below
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
    else:
        rec["error"] = err
    with lock:
        if rec["ok"]: consecutive = 0
        elif throttled:
            throttled_files += 1; consecutive += 1
            if consecutive >= 3 and not stop.is_set():
                stop.set(); print("throttled by Google: ending this round early", flush=True)
        if rec["ok"] or not throttled: listing.append(rec)   # a throttled file is tried again next round
        print(f"{len(listing)}/{len(selected)} {'ok' if rec['rendered'] else 'FAIL'} {rec['seconds']}s {rec.get('bytes', 0)//1000000}MB {it['path']}" + (f"  [{err}]" if not rec["ok"] else ""), flush=True)
        if len(listing) % 20 == 0: json.dump(sorted(listing, key=lambda r: r["tag"]), open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    list(ex.map(lambda a: grab(*a), enumerate(selected, 1)))
listing.sort(key=lambda r: r["tag"])
json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
done = sum(1 for l in listing if l.get("rendered"))
left = sum(1 for it in selected if not it.get("skip")) - len(listing)
print(f"done: {done} rendered of {len(selected)}; {len(listing) - done} failed; {left} left for another round", flush=True)
if left:
    open(AGAIN, "w").write(str(left))
