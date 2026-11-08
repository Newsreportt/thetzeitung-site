"""First-page text and render for every downloaded PDF in out/."""
import json, os, subprocess, sys
out = sys.argv[1]
L = json.load(open(f"{out}/listing.json", encoding="utf-8"))
for it in L:
    pdf = f"{out}/{it['tag']}.pdf"
    if not it["ok"] or not os.path.exists(pdf): it["rendered"] = False; continue
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    it["pages"] = next((int(l.split()[-1]) for l in info.splitlines() if l.startswith("Pages:")), 0)
    subprocess.run(["pdftotext", "-f", "1", "-l", "1", pdf, f"{out}/{it['tag']}.txt"])
    subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "110", "-jpeg", "-jpegopt", "quality=88", "-singlefile", pdf, f"{out}/{it['tag']}"])
    subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", "200", "-jpeg", "-jpegopt", "quality=85", "-singlefile", pdf, f"{out}/{it['tag']}-zoom"])
    it["rendered"] = os.path.exists(f"{out}/{it['tag']}.jpg")
    os.remove(pdf)
json.dump(L, open(f"{out}/listing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("rendered", sum(1 for l in L if l.get("rendered")), "of", len(L))
