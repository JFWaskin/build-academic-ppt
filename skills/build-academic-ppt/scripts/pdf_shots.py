#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_shots -- crop a passage out of a source PDF and render it with a precise
highlight.

Handles the failure modes that make naive `search_for` + crop produce garbage:

  * fitz.Rect.__and__ returns an EMPTY Rect that is still truthy -> always
    test .is_empty
  * a CJK PDF reports a whole paragraph as one "line"  -> cluster spans by
    y-centre instead of trusting PyMuPDF's line boxes
  * two-column layouts bleed the far column into the crop -> anchor x to the
    needle's column
  * journal mastheads run vertically in the outer margin -> drop tall/narrow
    spans
  * running heads / half-cut lines at the crop edge    -> snap to whole lines

Two failure modes this version adds, both of which used to pass silently:

  * THE HIGHLIGHT VANISHES. `search_for` finds the phrase somewhere on the
    PAGE; if that occurrence lies outside the crop rectangle, the crop is
    still produced -- without a highlight. The image looks plausible, so
    nothing complains, and the slide ends up showing a crop whose evidence
    is not marked. Every crop is now checked for amber pixels, and a crop
    with no highlight is a hard error.
  * THE WRONG OCCURRENCE. A phrase that appears three times (in the
    abstract, in the body and in the reference list) silently resolves to
    the first one. Ambiguity is now reported, and `occ` / `col` pick the
    one you meant.

Usage
-----
# probe: which pages contain a phrase
python3 pdf_shots.py probe paper.pdf "functional asymmetry" "dual code"

# crop: one shot per job
python3 pdf_shots.py shots paper.pdf jobs.json outdir/

jobs.json is a list of dicts:
  {"name": "shot_id", "page": 52, "needles": ["Textual panorama is de"],
   "ctx": 2, "pad": 16, "occ": 0, "col": "left"}
    page    1-based page number
    needles substrings to highlight
    ctx     extra lines of context above and below (1-2 is usually right)
    pad     horizontal padding in PDF points
    occ     which occurrence of the needle on the page (0-based)
    col     "left" | "right" | "auto" -- pick the match in that column

Options: --zoom 3.0 (render scale), --no-verify (skip the highlight check),
         --no-manifest (skip manifest.json)
"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw

ZOOM = 3.0
MARK = (255, 198, 96)          # warm amber; reads on both white and cream
MARK_ALPHA = 110
LINE_TOL = 3.0
VERTICAL_H, VERTICAL_W = 11.0, 22.0

# The composited highlight on a white page lands near (255, 230, 186). A crop
# is only evidence if the highlight is actually in the image.
AMBER_MIN_PIXELS = 40


def _is_amber(r, g, b):
    return r >= 235 and 195 <= g <= 245 and 150 <= b <= 220


def count_highlight(img):
    """Count pixels that look like the composited amber highlight."""
    small = img.convert("RGB")
    if small.width * small.height > 4_000_000:
        small = small.resize((small.width // 2, small.height // 2))
    px = small.load()
    n = 0
    for y in range(small.height):
        for x in range(small.width):
            r, g, b = px[x, y]
            if _is_amber(r, g, b):
                n += 1
    return n * (4 if small.width != img.width else 1)


# ----------------------------------------------------------------- probing
def cmd_probe(path, needles):
    doc = fitz.open(path)
    for nd in needles:
        hits = []
        for i in range(doc.page_count):
            if doc[i].search_for(nd):
                hits.append(i + 1)
        print(f"{nd!r:52} -> {hits if hits else 'NOT FOUND'}")
    doc.close()


# ----------------------------------------------------------------- internals
def _column_boundary(page, spans):
    """X split between the two columns of a two-column article, or None."""
    xs = sorted(b[0] for b in page.get_text("blocks") if b[6] == 0)
    if len(xs) < 4:
        return None
    lo, hi = page.rect.width * 0.20, page.rect.width * 0.80
    inside = [x for x in xs if lo <= x <= hi]
    if len(inside) < 2:
        return None
    gaps = [(inside[i + 1] - inside[i], (inside[i] + inside[i + 1]) / 2)
            for i in range(len(inside) - 1)]
    gap, mid = max(gaps)
    if gap < page.rect.width * 0.08:
        return None
    left = any(s[0].x1 <= mid for s in spans)
    right = any(s[0].x0 >= mid for s in spans)
    return mid if (left and right) else None


def _cluster_lines(page, x0=None, x1=None):
    """Return [(bbox, y_center, text)] with one entry per visual line.

    Fed by `get_text("words")`, which is fast -- the "dict" mode does a
    per-character layout analysis and is up to two orders of magnitude
    slower on a document with full-page images -- and carries the block and
    line numbers needed to keep columns apart.

    PyMuPDF's own line segmentation is unreliable for CJK: a whole paragraph
    can come back as a single line, and in a two-column page a left-column
    line and a right-column line at the same height would merge into one
    bbox spanning both columns. So the words are re-clustered on their
    vertical centre, with the column taken from the block number.
    """
    spans = []
    for wx0, wy0, wx1, wy1, text, block, line, wno in page.get_text("words"):
        if not text or not text.strip():
            continue
        bb = fitz.Rect(wx0, wy0, wx1, wy1)
        if (bb.y1 - bb.y0) > VERTICAL_H and (bb.x1 - bb.x0) < VERTICAL_W:
            continue  # vertical masthead in the outer margin
        if x0 is not None and (bb.x1 < x0 - 2 or bb.x0 > x1 + 2):
            continue
        if x1 is not None and bb.x0 > x1 + 2:
            continue
        spans.append((bb, text, block))
    if not spans:
        return []
    if x0 is not None and x1 is not None:
        mid = None
    else:
        mid = _column_boundary(page, spans)
    spans.sort(key=lambda t: (((t[0].y0 + t[0].y1) / 2),
                             0 if (mid is None or (t[0].x0 + t[0].x1) / 2 < mid) else 1,
                             t[2],
                             t[0].x0))
    lines = []
    for bb, t, block in spans:
        yc = (bb.y0 + bb.y1) / 2
        col = 0 if (mid is None or (bb.x0 + bb.x1) / 2 < mid) else 1
        key = (col, round(yc / LINE_TOL))
        if lines and lines[-1][3] == (col, key[1]):
            lines[-1] = (lines[-1][0] | bb, yc, lines[-1][2] + " " + t, (col, key[1]))
        else:
            lines.append((bb, yc, t, (col, key[1])))
    lines.sort(key=lambda t: (round(t[0].y0, 1), t[0].x0))
    return [(b, y, t) for b, y, t, _ in lines]


def _column(page, lines, xc):
    col = [L for L in lines if L[0].x0 - 4 <= xc <= L[0].x1 + 4]
    return col or lines


def _pick_rect(page, needle, occ=None, col=None):
    """Choose which occurrence of the needle to highlight.

    The old behaviour was "always the first one on the page", which silently
    picks the abstract instead of the passage you meant.
    """
    found = page.search_for(needle)
    if not found:
        return None, "not-found"
    if len(found) > 1:
        if occ is not None:
            if occ >= len(found):
                return None, f"occ {occ} out of range ({len(found)} matches)"
            return found[occ], f"occurrence {occ}/{len(found)}"
        if col in ("left", "right"):
            mid = page.rect.width / 2
            cands = [r for r in found
                     if (r.x0 + r.x1) / 2 < mid] if col == "left" else \
                    [r for r in found if (r.x0 + r.x1) / 2 >= mid]
            if cands:
                return cands[0], f"column={col} of {len(found)} matches"
        return found[0], f"AMBIGUOUS: {len(found)} matches, using the first"
    return found[0], "unique"


def crop(path, page_no, needles, ctx=2, pad=16.0, x0=None, x1=None,
         zoom=ZOOM, out=None, occ=None, col=None, verify=True,
         ctx_before=None, ctx_after=None):
    doc = fitz.open(path)
    page = doc[page_no - 1]
    rects = []
    notes = []
    for nd in needles:
        r, note = _pick_rect(page, nd, occ=occ, col=col)
        notes.append(f"{nd!r}: {note}")
        if r is None:
            print(f"  !! page {page_no}: {note} -> {nd!r}")
            continue
        rects.append(r)
    if not rects:
        doc.close()
        return None, notes

    u = rects[0]
    for r in rects[1:]:
        u |= r

    lines = _cluster_lines(page, x0, x1)
    xc = (u.x0 + u.x1) / 2
    if x0 is not None and x1 is not None:
        col_lines = lines
    else:
        col_lines = _column(page, lines, xc)

    idx = [i for i, L in enumerate(col_lines)
           if any(not (r & L[0]).is_empty for r in rects)]
    if not idx:
        doc.close()
        return None, notes + ["needle not on any clustered line"]

    # the context above and below can differ: too much context below is how
    # a crop ends up carrying a reference list instead of the passage
    cb = ctx if ctx_before is None else ctx_before
    ca = ctx if ctx_after is None else ctx_after
    lo = max(0, min(idx) - cb)
    hi = min(len(col_lines) - 1, max(idx) + ca)
    sel = col_lines[lo:hi + 1]

    seed = [L for L in sel if any(not (r & L[0]).is_empty for r in rects)] or sel
    cx0, cx1 = min(L[0].x0 for L in seed), max(L[0].x1 for L in seed)
    keep = [L for L in sel if L[0].x0 >= cx0 - 8 and L[0].x1 <= cx1 + 8] or sel

    left = x0 if x0 is not None else min(L[0].x0 for L in keep) - pad
    right = x1 if x1 is not None else max(L[0].x1 for L in keep) + pad
    clip = fitz.Rect(left,
                     min(L[0].y0 for L in sel) - 6,
                     right,
                     max(L[0].y1 for L in sel) + 9) & page.rect

    # THE GUARD: a needle whose rect does not meet the clip produces a crop
    # with no highlight in it -- a plausible-looking picture of nothing.
    outside = [r for r in rects if (r & clip).is_empty]
    if outside:
        doc.close()
        return None, notes + [
            "HIGHLIGHT OUTSIDE THE CROP: the phrase was found on the page but "
            "not inside the cropped region -- widen ctx/pad, or pass explicit "
            "x0/x1 for the column"]

    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)

    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for r in rects:
        x0p = (r.x0 - clip.x0) * zoom - 2
        y0p = (r.y0 - clip.y0) * zoom - 1.5
        x1p = (r.x1 - clip.x0) * zoom + 2
        y1p = (r.y1 - clip.y0) * zoom + 1.5
        dr.rectangle([x0p, y0p, x1p, y1p], fill=MARK + (MARK_ALPHA,))
    out_img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    if verify:
        n = count_highlight(out_img)
        if n < AMBER_MIN_PIXELS:
            doc.close()
            return None, notes + [
                f"NO HIGHLIGHT IN THE IMAGE ({n} amber px) -- the crop would "
                f"show text with nothing marked"]
        notes.append(f"highlight px: {n}")

    doc.close()
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        out_img.save(out)
    return out_img, notes


def cmd_shots(pdf, jobs_path, outdir, zoom=ZOOM, verify=True, manifest=True):
    jobs = json.load(open(jobs_path, encoding="utf-8"))
    os.makedirs(outdir, exist_ok=True)
    man = {}
    failures = 0
    for j in jobs:
        img, notes = crop(pdf, j["page"], j["needles"],
                          ctx=j.get("ctx", 2), pad=j.get("pad", 16),
                          x0=j.get("x0"), x1=j.get("x1"), zoom=zoom,
                          out=None, occ=j.get("occ"), col=j.get("col"),
                          verify=verify, ctx_before=j.get("ctx_before"),
                          ctx_after=j.get("ctx_after"))
        for n in notes:
            if "AMBIGUOUS" in n or "OUTSIDE" in n or "NO HIGHLIGHT" in n:
                print(f"  !! {j['name']}: {n}")
        if img is None:
            print(f"  !! {j['name']}: FAILED ({'; '.join(notes)})")
            failures += 1
            continue
        dest = os.path.join(outdir, j["name"] + ".png")
        img.save(dest)
        w, h = img.size
        print(f"  ok {j['name']:20} p{j['page']:<4} {w}x{h}  ar={w/h:.2f}")
        man[j["name"]] = {"file": dest, "page": j["page"], "needles": j["needles"],
                          "w": w, "h": h}
    if manifest:
        mpath = os.path.join(outdir, "manifest.json")
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
        print(f"  manifest -> {mpath}")
    return failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    if cmd == "probe":
        cmd_probe(sys.argv[2], sys.argv[3:])
    elif cmd == "shots":
        z = ZOOM
        verify = True
        man = True
        args = sys.argv[2:]
        if "--zoom" in args:
            i = args.index("--zoom")
            z = float(args[i + 1]); args = args[:i] + args[i + 2:]
        if "--no-verify" in args:
            args.remove("--no-verify"); verify = False
        if "--no-manifest" in args:
            args.remove("--no-manifest"); man = False
        raise SystemExit(1 if cmd_shots(args[0], args[1], args[2], z, verify, man) else 0)
    else:
        print(__doc__)
        raise SystemExit(1)
