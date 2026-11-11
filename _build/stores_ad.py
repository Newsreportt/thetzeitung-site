"""The 'in the stores' poster on the home page (ads/in-stores.jpg) shows the week's three covers
fanned out over the designed background. The background and the three page positions were
taken once from the office's poster (make_template); every week render(date) lays the week's
archive covers into the same positions.
    python3 _build/stores_ad.py 2026-11-13          # render the poster for that edition
    python3 _build/stores_ad.py --template 2026-11-06   # one-off: lift background + positions from ads/in-stores.jpg
"""
import json, os, sys
import numpy as np
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTER = os.path.join(ROOT, "ads", "in-stores.jpg")
TDIR = os.path.join(ROOT, "_build", "stores-ad")
BACKGROUND = os.path.join(TDIR, "background.jpg")
GEOMETRY = os.path.join(TDIR, "geometry.json")
PILL_IMG = os.path.join(TDIR, "pill.jpg")
PILL = (300, 994, 1060, 1056)     # the gold pill with "three sections, every week": drawn over the covers
SECTIONS = "abc"          # back to front: the main cover, Yiddishe Tzeit, Chassidishe Tzeit

def _offset_quad(q, margins):
    """Push the four edges of a quad outwards by (top, right, bottom, left) and intersect them."""
    q = np.asarray(q, float); c = q.mean(0); lines = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        e = (b - a) / np.linalg.norm(b - a); n = np.array([e[1], -e[0]])
        if np.dot(n, (a + b) / 2 - c) < 0: n = -n
        lines.append((a + n * margins[i], e))
    out = []
    for i in range(4):
        (p1, d1), (p2, d2) = lines[i - 1], lines[i]
        A = np.array([d1, -d2]).T; t = np.linalg.solve(A, p2 - p1)
        out.append(p1 + d1 * t[0])
    return np.array(out)

def _page(cover_bgr, size, margins):
    """The cover picture on a sheet of its own paper colour, with the page margins the trim took off."""
    W, H = size; mt, mr, mb, ml = margins
    corner = np.concatenate([cover_bgr[:6, :6].reshape(-1, 3), cover_bgr[:6, -6:].reshape(-1, 3)])
    paper = np.median(corner, axis=0)
    page = np.empty((H, W, 3), np.uint8); page[:] = paper
    iw, ih = W - ml - mr, H - mt - mb
    h, w = cover_bgr.shape[:2]; s = min(iw / w, ih / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    small = cv2.resize(cover_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
    x = ml + (iw - nw) // 2; y = mt
    page[y:y + nh, x:x + nw] = small
    return page

def _shadow(canvas, poly, shift, sigma, alpha):
    h, w = canvas.shape[:2]
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [np.int32(np.round(poly + np.array(shift)))], 1.0)
    m = cv2.GaussianBlur(m, (0, 0), sigma) * alpha
    return (canvas * (1 - m[..., None])).astype(np.uint8)

def render(date, out=POSTER):
    g = json.load(open(GEOMETRY, encoding="utf-8"))
    canvas = cv2.imread(BACKGROUND)
    H, W = canvas.shape[:2]
    for layer in g["layers"]:
        sec = layer["sec"]
        src = os.path.join(ROOT, "covers", "archive", f"{date}-{sec}.jpg")
        cover = cv2.imread(src)
        if cover is None: raise SystemExit(f"no cover {src}")
        quad = np.array(layer["page"], float)
        pw = int(round(np.linalg.norm(quad[1] - quad[0]))); ph = int(round(np.linalg.norm(quad[3] - quad[0])))
        scale = pw / np.linalg.norm(quad[1] - quad[0])
        margins = [int(round(m * scale)) for m in layer["margins"]]
        page = _page(cover, (pw, ph), margins)
        canvas = _shadow(canvas, quad, (6, 9), 9, 0.42)
        canvas = _shadow(canvas, quad, (1, 2), 2, 0.3)
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]]), np.float32(quad))
        warped = cv2.warpPerspective(page, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        alpha = cv2.warpPerspective(np.full((ph, pw), 255, np.uint8), M, (W, H), flags=cv2.INTER_LINEAR)
        a = (alpha.astype(np.float32) / 255)[..., None]
        canvas = (canvas * (1 - a) + warped * a).astype(np.uint8)
    x0, y0, x1, y1 = g["pill"]; pill = cv2.imread(PILL_IMG)
    fm = np.zeros((y1 - y0, x1 - x0), np.float32); fm[6:-6, 6:-6] = 1
    fm = cv2.GaussianBlur(fm, (0, 0), 3)[..., None]
    canvas[y0:y1, x0:x1] = (canvas[y0:y1, x0:x1] * (1 - fm) + pill * fm).astype(np.uint8)
    cv2.imwrite(out, canvas, [cv2.IMWRITE_JPEG_QUALITY, 88, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    return out

def make_template(date, margins):
    """Find the three covers of `date` in the office's poster (feature matching), lift the page
    rectangles, paint the covers out of the background and save both."""
    os.makedirs(TDIR, exist_ok=True)
    P = cv2.imread(POSTER); Pg = cv2.cvtColor(P, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(6000); kp2, des2 = sift.detectAndCompute(Pg, None)
    layers = []; mask = np.zeros(Pg.shape, np.uint8)
    for sec in SECTIONS:
        C = cv2.imread(os.path.join(ROOT, "covers", "archive", f"{date}-{sec}.jpg"))
        kp1, des1 = sift.detectAndCompute(cv2.cvtColor(C, cv2.COLOR_BGR2GRAY), None)
        m = cv2.BFMatcher().knnMatch(des1, des2, k=2)
        good = [a for a, b in m if a.distance < 0.75 * b.distance]
        src = np.float32([kp1[x.queryIdx].pt for x in good]).reshape(-1, 1, 2)
        dst = np.float32([kp2[x.trainIdx].pt for x in good]).reshape(-1, 1, 2)
        Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
        h, w = C.shape[:2]
        quad = cv2.perspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2), Hm).reshape(-1, 2)
        page = _offset_quad(quad, margins[sec])
        layers.append({"sec": sec, "page": page.round(1).tolist(), "margins": margins[sec], "inliers": int(inl.sum())})
        cv2.fillPoly(mask, [np.int32(np.round(page))], 255)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=34)
    mask[PILL[1]:, :] = 0                     # the pill and the green band below it stay as they are
    # a smooth fill: inpaint at a quarter of the size, then blend the upscaled fill into the masked area
    small = cv2.inpaint(cv2.resize(P, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA),
                        cv2.resize(mask, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST), 3, cv2.INPAINT_TELEA)
    fill = cv2.resize(small, (P.shape[1], P.shape[0]), interpolation=cv2.INTER_CUBIC)
    m = (cv2.GaussianBlur(mask, (0, 0), 2).astype(np.float32) / 255)[..., None]
    bg = (P * (1 - m) + fill * m).astype(np.uint8)
    cv2.imwrite(BACKGROUND, bg, [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(PILL_IMG, P[PILL[1]:PILL[3], PILL[0]:PILL[2]], [cv2.IMWRITE_JPEG_QUALITY, 95])
    json.dump({"size": [P.shape[1], P.shape[0]], "from": date, "pill": PILL, "layers": layers}, open(GEOMETRY, "w", encoding="utf-8"), indent=1)
    print("template from", date, [(l["sec"], l["inliers"]) for l in layers])

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--template":
        # page margins (poster px) measured on the office's poster: top, right, bottom, left
        make_template(args[1], {"a": [1, 12, 0, 12], "b": [38, 30, 29, 37], "c": [17, 29, 2, 17]})
    else:
        print(render(args[0]))
