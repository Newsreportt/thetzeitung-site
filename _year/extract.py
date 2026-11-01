"""Unpack a year's PDFs. For every PDF keep the text of its first page; render the first page as a
JPEG only where it can be a cover: the file is the first page (name starts with 1) or its text
carries the masthead's VOL/NO line."""
import os, re, subprocess, sys, zipfile, json
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
def text_of(pdf):
    return subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, "-"], capture_output=True, text=True).stdout
with zipfile.ZipFile(src) as z:
    names = [n for n in z.namelist() if n.lower().endswith(".pdf") and "__MACOSX" not in n]
    print(len(names), "pdfs in the zip", flush=True)
    listing = []
    for i, n in enumerate(sorted(names), 1):
        tag = f"{i:05d}"
        base = os.path.basename(n)
        pdf = f"{out}/{tag}.pdf"
        with z.open(n) as f, open(pdf, "wb") as g: g.write(f.read())
        info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
        pages = next((int(l.split()[-1]) for l in info.splitlines() if l.startswith("Pages:")), 0)
        txt = text_of(pdf)
        open(f"{out}/{tag}.txt", "w", encoding="utf-8").write(txt)
        first = bool(re.match(r"^0*1([,.\-_ ]|\.pdf$)", base, re.I)) or bool(re.search(r"cover|front|shaar|שער", base, re.I))
        masthead = bool(re.search(r"VOL\.?\s*\d+\D{1,8}NO\.?\s*\d+", txt, re.I))
        rendered = False
        if first or masthead:
            subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-jpeg", "-jpegopt", "quality=88", "-singlefile", pdf, f"{out}/{tag}"])
            rendered = os.path.exists(f"{out}/{tag}.jpg")
        os.remove(pdf)
        listing.append({"tag": tag, "path": n, "pages": pages, "bytes": os.path.getsize(f"{out}/{tag}.txt"), "rendered": rendered})
        if i % 100 == 0: print(i, flush=True)
json.dump(listing, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done", len(listing), "rendered", sum(1 for l in listing if l["rendered"]))
