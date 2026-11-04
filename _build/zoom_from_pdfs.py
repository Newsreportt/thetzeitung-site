#!/usr/bin/env python3
"""Sharper copies of covers already in the archive, from their source PDFs:
    python3 _build/zoom_from_pdfs.py path/to/*.pdf
Each PDF is matched to its edition and section the way the importer does; a matching cover gets
covers/zoom/<date>-<section>.jpg (1500px wide) for zooming in. Run _build/build.py afterwards."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_covers as ic
data = json.load(open(ic.DATA, encoding="utf-8"))
ic.KNOWN_FRIDAYS.update(data.keys())
done = skipped = 0
for pdf in sys.argv[1:]:
    text = ic.text_of(pdf); name = os.path.basename(pdf)
    sec = ic.section_of(text, name); d = ic.date_of(text)
    if not d: skipped += 1; continue
    key = ic.to_friday(d).isoformat()
    ed = data.get(key)
    if not ed or sec not in ed["covers"]: skipped += 1; print("no match", name, key, sec); continue
    out = os.path.join(ic.ROOT, "covers", "zoom", f"{key}-{sec}.jpg")
    if os.path.exists(out): continue
    ic.render_zoom(pdf, out); done += 1
    print("zoom", key, sec, "<-", name, flush=True)
print(f"{done} made, {skipped} skipped")
