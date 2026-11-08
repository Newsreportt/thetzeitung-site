"""Walk public Drive folders through the embedded folder view (no sign-in needed), pick the
page-1 PDFs (names like 1.pdf, 01.pdf, 1,65-67.pdf, 1a.pdf, cover.pdf) and download them with gdown.
Writes out/listing.json: [{tag, path, id}] and out/<tag>.pdf."""
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

ENTRY = re.compile(r'<div class="flip-entry" id="entry-([^"]+)"(.*?)</div>\s*</div>\s*</div>', re.S)
denied = []
def children(folder_id):
    for attempt in range(6):
        page = fetch(f"https://drive.google.com/embeddedfolderview?id={folder_id}#list")
        if "id=\"entry-" in page or ("Access Denied" not in page and "You need access" not in page): break
        time.sleep(30 * (attempt + 1))          # sharing may still be spreading through the tree
    else:
        denied.append(folder_id); print("access denied:", folder_id, flush=True); return []
    items = []
    for m in re.finditer(r'id="entry-([\w-]+)"', page):
        fid = m.group(1)
        seg = page[m.end(): m.end() + 3000]
        href = re.search(r'href="([^"]+)"', seg)
        title = re.search(r'flip-entry-title">(.*?)</div>', seg, re.S)
        name = html.unescape(title.group(1)).strip() if title else ""
        is_folder = bool(href and ("/folders/" in href.group(1) or "embeddedfolderview" in href.group(1)))
        items.append((fid, name, is_folder))
    # one entry per id
    seen, uniq = set(), []
    for it in items:
        if it[0] in seen: continue
        seen.add(it[0]); uniq.append(it)
    return uniq

COVER = re.compile(r"^(0*1(?!\d)|cover|front|shaar)", re.I)
selected, nfolders = [], 0
def walk(folder_id, path, depth=0):
    global nfolders
    if depth > 4: return
    nfolders += 1
    for fid, name, is_folder in children(folder_id):
        if is_folder:
            if "vol38" in name.lower() or "תשפ" in name: continue        # already in the archive
            walk(fid, f"{path}/{name}", depth + 1); time.sleep(0.4)
        elif name.lower().endswith(".pdf") and COVER.match(name):
            selected.append({"id": fid, "path": f"{path}/{name}"})
    if nfolders % 20 == 0: print(f"{nfolders} folders, {len(selected)} covers so far", flush=True)

for f in job["folders"]:
    walk(f["id"], f["name"])
print(f"crawled {nfolders} folders; {len(selected)} candidate covers; {len(denied)} folders denied", flush=True)
json.dump(denied, open(f"{out}/denied.json", "w"))
json.dump(selected, open(f"{out}/selected.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

listing = []
for i, it in enumerate(selected, 1):
    tag = f"{i:05d}"; dest = f"{out}/{tag}.pdf"
    ok = False
    for attempt in range(3):
        r = subprocess.run(["gdown", "--quiet", it["id"], "-O", dest], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000: ok = True; break
        time.sleep(5 + 10 * attempt)
    listing.append({"tag": tag, "path": it["path"], "id": it["id"], "ok": ok})
    if i % 25 == 0: print(f"downloaded {i}/{len(selected)}", flush=True)
json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", sum(1 for l in listing if l["ok"]), "of", len(listing))
