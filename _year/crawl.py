"""Walk public Drive folders through the embedded folder view (no sign-in needed), pick the cover
files of every issue and keep only their first page.

Per issue folder one main cover is chosen, by preference: a page-1 file (…_PG001.pdf, 1.pdf,
01.pdf, 1,65-67.pdf), a file named cover/front, "Section A.pdf" (whole section), or the whole
paper (full.pdf). "Section B/C/D.pdf" are taken as well: their first pages are the covers of the
Yiddishe Tzeit and the other supplements. Each PDF is downloaded, its first page rendered and
its text read, then the PDF is deleted. Writes out/listing.json, out/<tag>.jpg, <tag>-zoom.jpg, <tag>.txt."""
import html, json, os, re, subprocess, sys, time, urllib.request

job = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
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

def kind_of(name):
    n = name.lower()
    if not n.endswith(".pdf"): return None, 0
    if re.search(r"_pg0*1\.pdf$", n): return "a", 6
    if re.match(r"^0*1(?!\d)", n): return "a", 5
    if re.match(r"^(cover|front|shaar)", n): return "a", 4
    if re.match(r"^section\s*a\b", n): return "a", 3
    if re.match(r"^(full|whole|complete|all)\b", n): return "a", 2
    m = re.match(r"^section\s*([b-d])\b", n)
    if m: return m.group(1), 5
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
            time.sleep(0.2)
        else:
            kind, score = kind_of(name)
            if not kind or not issue: continue
            cur = issues.setdefault(issue, {}).get(kind)
            if not cur or score > cur[0]: issues[issue][kind] = (score, fid, f"{path}/{name}")
    if nfolders % 25 == 0: print(f"{nfolders} folders, {len(issues)} issues so far", flush=True)

for f in job["folders"]:
    walk(f["id"], f["name"], None)
selected = [{"id": fid, "path": p, "issue": iss, "kind": k} for iss, kinds in issues.items() for k, (score, fid, p) in sorted(kinds.items())]
print(f"crawled {nfolders} folders; {len(issues)} issues, {len(selected)} cover files; {len(denied)} folders denied", flush=True)
json.dump(selected, open(f"{out}/selected.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(denied, open(f"{out}/denied.json", "w"))

listing = []
for i, it in enumerate(selected, 1):
    tag = f"{i:05d}"; pdf = f"{out}/{tag}.pdf"
    ok = False
    for attempt in range(3):
        r = subprocess.run(["gdown", "--quiet", "--continue", it["id"], "-O", pdf], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(pdf) and os.path.getsize(pdf) > 1000: ok = True; break
        if os.path.exists(pdf): os.remove(pdf)
        time.sleep(5 + 10 * attempt)
    rec = {"tag": tag, "path": it["path"], "id": it["id"], "issue": it["issue"], "kind": it["kind"], "ok": ok, "rendered": False}
    if ok:
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        rec["pages"] = next((int(l.split()[-1]) for l in info.splitlines() if l.startswith("Pages:")), 0)
        rec["bytes"] = os.path.getsize(pdf)
        subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, f"{out}/{tag}.txt"])
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-jpeg", "-jpegopt", "quality=88", "-singlefile", pdf, f"{out}/{tag}"])
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "200", "-jpeg", "-jpegopt", "quality=85", "-singlefile", pdf, f"{out}/{tag}-zoom"])
        rec["rendered"] = os.path.exists(f"{out}/{tag}.jpg")
        os.remove(pdf)
    listing.append(rec)
    if i % 25 == 0:
        print(f"{i}/{len(selected)} done", flush=True)
        json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done:", sum(1 for l in listing if l["rendered"]), "rendered of", len(listing))
