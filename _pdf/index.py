"""Build the archive's word index out of the text read from the PDFs.

Every word of every page (text/<date>.json.gz in R2) is written down against the issue and the
page it stands on, and the result is put back in the bucket as a set of small files, one for
each pair of opening letters: idx/w/<two letters>.json. A reader's search fetches the one file
its word belongs to, so the whole archive is searchable without anything being downloaded whole
— and the index holds words and page numbers only, never a line of an article.

  python3 _pdf/index.py [--limit N]

idx/meta.json   {"built", "editions": [[date, vol, no, parsha, hdate, pages, sections], …], …}
idx/hw/<ab>.json the same, over the headlines alone: [edition, headlines, id, id, …]
idx/h/<year>.json {"<date>": [[page, "the headline"], …]} — what the reader is shown
idx/w/<ab>.json {"<word>": [edition, mentions, page, page, …,  edition, mentions, page, …], …}
                (<ab> is the word's first two characters: Hebrew, Latin or digits)
                (the edition is a place in the editions list, written as a step from the one before)
"""
import gzip, json, os, re, sys, time, collections, tempfile

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_pdf"))

HEB = "א-ת"
# Not the Yiddish alone: an advertiser's name in English, a telephone number, a year — a reader
# looking for any of those is looking for an article too.
WORD = re.compile(f"[{HEB}]+(?:['׳\"״][{HEB}]+)*"          # קאשוי, ד'קאשוי
                  r"|[A-Za-z][A-Za-z'&.]{1,}[A-Za-z]"       # Lipa, B&H, U.S.A
                  r"|\d{3,}(?:[-.\u2013/]\d{3,})*")         # 2026, 718-851-6607
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
MAX_PAGES = 30         # how many page numbers are kept for one word in one issue
MIN_LEN = 2

args = sys.argv[1:]
LIMIT = int(args[args.index("--limit") + 1]) if "--limit" in args else 0

s3 = boto3.client("s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  region_name="auto", aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
BUCKET = os.environ["R2_BUCKET"]

def key_of(word):
    """What a word is filed under: no apostrophes or the marks that hold a number together,
    final Hebrew letters written plainly, and the Latin alphabet in small letters — so that
    Lipa, LIPA and lipa are one word, and 718-851-6607 is one number."""
    w = re.sub(r"['׳\"״&.\-\u2013/]", "", word).translate(FINALS)
    return w.lower() if w.isascii() else w

# Yiddish and loshn koydesh hang their little words on the front of the next one: דקאשוי,
# בקאשוי, ובקאשויער. A reader types the name itself, so the name is filed as well.
HANGERS = "בדהוכלמש"

def keys_of(word):
    """A word is filed under itself; under what follows a letter tied on with an apostrophe, as
    in ד'קאשוי or ר'ישראל; and under what is left when the one or two little letters hung on its
    front are taken off, so that דקאשוי and ובקאשוי answer to קאשוי."""
    k = key_of(word)
    out = {k}
    m = re.match(f"^[{HEB}]['׳]([{HEB}].*)$", word)
    if m: out.add(key_of(m.group(1)))
    for n in (1, 2):
        if len(k) >= n + 4 and all(c in HANGERS for c in k[:n]):
            out.add(k[n:])
    return {k2 for k2 in out if len(k2) >= MIN_LEN}

def shard_of(key):
    return key[:2]

def sections_of(entry):
    """Where each section of the paper runs, read off the files the issue was made of. An older
    issue was kept a page to a file, so a run of pages belonging to one section is written as the
    one stretch it is; where the files say nothing about sections, the stretch is left unnamed."""
    import archive as ar
    out, page = [], 1
    for f in entry.get("files", []):
        n = f.get("pages")
        if not n: continue
        sec, _ = ar.section_of(f["name"].split("/")[-1])
        sec = (sec or "").lower()
        if out and out[-1][2] == sec: out[-1][1] = page + n - 1
        else: out.append([page, page + n - 1, sec])
        page += n
    return [tuple(x) for x in out]

def section_at(bounds, page):
    for lo, hi, sec in bounds:
        if lo <= page <= hi: return sec
    return ""

def editions():
    """The issues that have both a PDF and its text, newest last, with what a reader sees."""
    pdfs = json.load(open(os.path.join(ROOT, "pdfs.json"), encoding="utf-8"))
    eds = json.load(open(os.path.join(ROOT, "_build", "editions.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(ROOT, "_pdf", "manifest.json"), encoding="utf-8"))
    out = []
    for date in sorted(pdfs):
        e = eds.get(date, {})
        out.append({"date": date, "vol": e.get("vol"), "no": e.get("no"), "parsha": e.get("parsha"),
                    "hdate": e.get("hdate"), "pages": pdfs[date].get("pages"),
                    "sections": sections_of(man.get(date, {}))})
    return out

def text_of(date):
    try:
        body = s3.get_object(Bucket=BUCKET, Key=f"text/{date}.json.gz")["Body"].read()
    except s3.exceptions.NoSuchKey:
        return None
    return json.loads(gzip.decompress(body))

def main():
    sys.path.insert(0, os.path.join(ROOT, "_pdf"))
    eds = editions()
    if LIMIT: eds = eds[:LIMIT]
    print(f"{len(eds)} issues to index", flush=True)
    with tempfile.TemporaryDirectory() as td:
        files, hfiles, read, missing = {}, {}, 0, 0
        heads_by_year, heads_total = collections.defaultdict(dict), 0
        for i, ed in enumerate(eds):
            doc = text_of(ed["date"])
            if not doc: missing += 1; continue
            read += 1
            where = collections.defaultdict(lambda: collections.defaultdict(int))   # key -> page -> count
            heads, hwhere = [], collections.defaultdict(set)                        # key -> headline ids
            for pg in doc["pages"]:
                n = pg["n"]
                for w in WORD.findall(pg["t"]):
                    if len(w) < MIN_LEN: continue
                    for k in keys_of(w): where[k][n] += 1
                for h in pg.get("h", ()):
                    hid = len(heads); heads.append([n, h])
                    for w in WORD.findall(h):
                        if len(w) < MIN_LEN: continue
                        for k in keys_of(w): hwhere[k].add(hid)
            for k, pages in where.items():
                sh = shard_of(k)
                f = files.get(sh)
                if f is None: f = files[sh] = open(os.path.join(td, "w-" + sh + ".txt"), "w", encoding="utf-8")
                top = sorted(pages, key=lambda p: (-pages[p], p))[:MAX_PAGES]
                f.write(f"{k}\t{i}\t{sum(pages.values())}\t{','.join(map(str, sorted(top)))}\n")
            for k, ids in hwhere.items():
                sh = shard_of(k)
                f = hfiles.get(sh)
                if f is None: f = hfiles[sh] = open(os.path.join(td, "h-" + sh + ".txt"), "w", encoding="utf-8")
                f.write(f"{k}\t{i}\t{len(ids)}\t{','.join(map(str, sorted(ids)))}\n")
            if heads:
                heads_by_year[ed["date"][:4]][ed["date"]] = heads
                heads_total += len(heads)
            if read % 50 == 0: print(f"  {read} issues read, {heads_total} headlines so far", flush=True)
        for f in list(files.values()) + list(hfiles.values()): f.close()
        print(f"{heads_total} headlines in {sum(len(v) for v in heads_by_year.values())} issues", flush=True)

        # what the reader is shown: the headlines themselves, a year to a file
        for year, issues in sorted(heads_by_year.items()):
            body = gzip.compress(json.dumps(issues, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
            s3.put_object(Bucket=BUCKET, Key=f"idx/h/{year}.json", Body=body,
                          ContentType="application/json", ContentEncoding="gzip")
        print(f"{read} issues read, {missing} without text, {len(files)} shards", flush=True)

        def pack(which, prefix, key_prefix):
            """One slice at a time: the postings of every word filed under those two letters."""
            names, terms, size = [], 0, 0
            for sh in sorted(which):
                index = collections.defaultdict(list)
                with open(os.path.join(td, prefix + sh + ".txt"), encoding="utf-8") as f:
                    for line in f:
                        k, i, n, rest = line.rstrip("\n").split("\t")
                        index[k].append((int(i), int(n), [int(x) for x in rest.split(",") if x]))
                out = {}
                for k, rows in index.items():
                    rows.sort()
                    flat, prev = [], 0
                    for i, n, nums in rows:
                        flat.append(i - prev); prev = i
                        flat.append(n); flat.append(len(nums)); flat.extend(nums)
                    out[k] = flat
                body = gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
                s3.put_object(Bucket=BUCKET, Key=f"idx/{key_prefix}/{sh}.json", Body=body,
                              ContentType="application/json", ContentEncoding="gzip")
                names.append(sh); terms += len(out); size += len(body)
                if len(names) % 100 == 0: print(f"  {len(names)} {key_prefix} slices written", flush=True)
            return names, terms, size

        hshards, hterms, hbytes = pack(hfiles, "h-", "hw")
        print(f"{hterms} headline words across {len(hshards)} slices, {hbytes / 1e6:.0f} MB", flush=True)

        shards, terms_total, bytes_total = [], 0, 0
        for sh in sorted(files):
            index = collections.defaultdict(list)
            with open(os.path.join(td, "w-" + sh + ".txt"), encoding="utf-8") as f:
                for line in f:
                    k, i, n, pages = line.rstrip("\n").split("\t")
                    index[k].append((int(i), int(n), [int(p) for p in pages.split(",") if p]))
            out = {}
            for k, rows in index.items():
                rows.sort()
                flat, prev = [], 0
                for i, n, pages in rows:
                    flat.append(i - prev); prev = i
                    flat.append(n); flat.append(len(pages)); flat.extend(pages)
                out[k] = flat
            body = gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6)
            s3.put_object(Bucket=BUCKET, Key=f"idx/w/{sh}.json", Body=body,
                          ContentType="application/json", ContentEncoding="gzip")
            shards.append(sh); terms_total += len(out); bytes_total += len(body)
            if len(shards) % 50 == 0: print(f"  {len(shards)} shards written", flush=True)

        meta = {"built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "shards": shards,
                "terms": terms_total, "min_len": MIN_LEN,
                "head_shards": hshards, "head_terms": hterms, "headlines": heads_total,
                "head_years": sorted(heads_by_year),
                "editions": [[e["date"], e["vol"], e["no"], e["parsha"], e["hdate"], e["pages"], e["sections"]]
                             for e in eds]}
        s3.put_object(Bucket=BUCKET, Key="idx/meta.json",
                      Body=gzip.compress(json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6),
                      ContentType="application/json", ContentEncoding="gzip")
        print(f"{terms_total} words across {len(shards)} shards, {bytes_total / 1e6:.0f} MB in the bucket")

if __name__ == "__main__":
    main()
