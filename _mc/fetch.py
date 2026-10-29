"""Fetch cover images listed in manifest.tsv from Mailchimp's public image host
and re-save them as plain JPEGs (quality 90) under _mc/img/<uuid>.jpg."""
import os, sys, time, urllib.request
from PIL import Image

BASE = "https://mcusercontent.com/32d4918dafef1c115c1d3f6bc/images/"
os.makedirs("_mc/img", exist_ok=True)
rows = [l.rstrip("\n").split("\t") for l in open("_mc/manifest.tsv", encoding="utf-8") if l.strip()]
ok = fail = 0
log = open("_mc/fetch.log", "w", encoding="utf-8")
for uid, ext, name, hint in rows:
    out = f"_mc/img/{uid}.jpg"
    if os.path.exists(out):
        ok += 1; continue
    url = f"{BASE}{uid}.{ext}"
    tmp = f"_mc/tmp.{ext}"
    done = False
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                f.write(r.read())
            im = Image.open(tmp)
            im.load()
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(out, "JPEG", quality=90, optimize=True)
            done = True
            break
        except Exception as e:
            err = repr(e)
            time.sleep(2 + attempt * 3)
    if done:
        ok += 1
    else:
        fail += 1
        log.write(f"FAIL\t{uid}\t{name}\t{err}\n")
    if (ok + fail) % 100 == 0:
        print(f"{ok + fail}/{len(rows)} ok={ok} fail={fail}", flush=True)
log.close()
print(f"done ok={ok} fail={fail}")
