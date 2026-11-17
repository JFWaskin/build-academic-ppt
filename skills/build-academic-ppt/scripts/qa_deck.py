#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_deck -- the mechanical gate. Run it on every deck, every time.

A visual review catches layout defects a bounding-box analysis cannot see
(it is good at "does this look wrong", bad at "is anything at y=7.2in on all
40 slides"). Run both. But the mechanical gate has to be honest about its own
blind spots, so this version closes the ones that mattered:

  * text sitting on top of a screenshot   (qa_deck v1 was blind: it only
    compared text boxes with each other)
  * text escaping its own frame           (boxes do not clip)
  * a highlight that silently vanished     (amber-pixel scan of every crop)
  * a slide with no screenshot / no citation
  * type below the floor                  (read sz from the XML: python-pptx
    truncates 10.5pt to 10 and reports a false positive)
  * the right margin                      (the old hardcoded 898pt threshold
    flagged every text block that sat exactly on the margin, and Chinese
    hanging punctuation pushes a full stop 0.19in past the margin)

Usage
-----
  python3 qa_deck.py deck.pptx              # render + check
  python3 qa_deck.py deck.pptx --keep       # keep the JPEGs for a vision review
  python3 qa_deck.py deck.pptx --no-render  # geometry checks only, no soffice
  python3 qa_deck.py deck.pptx --require-highlight
  python3 qa_deck.py deck.pptx --min-body 14

Exit code is non-zero when a hard failure is found.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pptx import Presentation          # noqa: E402
from pptx.enum.shapes import MSO_SHAPE_TYPE   # noqa: E402

FOOTER_TOP_PT = 500.0        # ~6.94in on a 7.5in slide
HANG_PT = 14.0               # Chinese hanging punctuation may sit this far out
CAPTION_FLOOR_PT = 10.5      # captions/labels/footers may go below this
BODY_FLOOR_PT = 14.0         # body prose may not
BODY_LONG_CHARS = 40         # a run this long is prose, not a label
CAPTION_GAP_PT = 0.15 * 72   # a caption must clear its crop by 0.15in
BAND_HEIGHT_PT = 0.05 * 72   # every evidence strip must be the same height
AMBER_MIN = 40               # amber pixels a real highlight must have


def _is_amber(r, g, b):
    return r >= 235 and 195 <= g <= 245 and 150 <= b <= 220


# ------------------------------------------------------------------ render
def render(pptx, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", outdir, pptx],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    subprocess.run(["pdftotext", "-bbox-layout", pdf,
                    os.path.join(outdir, "o.html")], check=True)
    subprocess.run(["pdftoppm", "-jpeg", "-r", "110", pdf,
                    os.path.join(outdir, "s")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return pdf


def load_boxes(outdir):
    html = open(os.path.join(outdir, "o.html"), encoding="utf-8").read()
    return re.split(r"<page ", html)[1:]


def word_boxes(page):
    return [(float(a), float(b), float(c), float(d), t)
            for a, b, c, d, t in re.findall(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)"'
                r' yMax="([\d.]+)">(.*?)</word>', page)]


# ------------------------------------------------------------------ pptx
def shape_rect(sh):
    if sh.left is None or sh.top is None:
        return None
    return (sh.left / 914400 * 72, sh.top / 914400 * 72,
            (sh.left + (sh.width or 0)) / 914400 * 72,
            (sh.top + (sh.height or 0)) / 914400 * 72)


def overlap_area(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if not (ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0):
        return 0.0
    return (min(ax1, bx1) - max(ax0, bx0)) * (min(ay1, by1) - max(ay0, by0))


def run_size_pt(run):
    """Read the size off the XML. python-pptx's font.size.pt truncates 10.5 to
    10 (integer division), which makes every 10.5pt caption a false positive."""
    sz = run._r.get_or_add_rPr().get("sz")
    return int(sz) / 100.0 if sz else None


def slide_furniture(pptx):
    """Footer furniture boxes, so the rendered check can tell the footer's own
    words from content that intruded into the footer band."""
    prs = Presentation(pptx)
    out = {}
    for si, slide in enumerate(prs.slides, 1):
        boxes = []
        for sh in slide.shapes:
            if (sh.name or "").startswith("dk_footer"):
                r = shape_rect(sh)
                if r:
                    boxes.append(r)
        out[si] = boxes
    return out


def deck_manifest(pptx):
    mpath = os.path.splitext(pptx)[0] + ".manifest.json"
    if os.path.exists(mpath):
        try:
            with open(mpath, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return None


# ------------------------------------------------------------------ checks
def check(pptx, keep=False, do_render=True, min_body=BODY_FLOOR_PT,
          require_highlight=False, strict_margin=False):
    outdir = tempfile.mkdtemp(prefix="qa_deck_")
    prs = Presentation(pptx)
    slide_w_pt = prs.slide_width / 914400 * 72
    margin_pt = 0.85 * 72
    right_edge = slide_w_pt - margin_pt
    furniture = slide_furniture(pptx)
    manifest = deck_manifest(pptx)

    low, right, overlaps, floors = [], [], [], []
    over_img, over_frame, no_shot, no_cite, no_mark = [], [], [], [], []
    bands, gaps = [], []

    # ---------- geometry from the pptx (exact) ----------
    for si, slide in enumerate(prs.slides, 1):
        pics, texts = [], []
        for sh in slide.shapes:
            r = shape_rect(sh)
            if r is None:
                continue
            if (sh.name or "").startswith("dk_footer"):
                continue
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pics.append((r, sh))
            elif sh.has_text_frame and sh.text_frame.text.strip():
                texts.append((r, sh))
        for pr, psh in pics:
            for tr, tsh in texts:
                a = overlap_area(pr, tr)
                if a > 0.004 * (pr[2] - pr[0]) * (pr[3] - pr[1]):
                    over_img.append((si, tsh.text_frame.text[:40].replace("\n", " ")))
        for r, sh in texts:
            need = 0.0
            for pa in sh.text_frame.paragraphs:
                if not pa.runs:
                    continue
                size = run_size_pt(pa.runs[0]) or min_body
                text = "".join(x.text for x in pa.runs)
                ls = pa.line_spacing if isinstance(pa.line_spacing, float) else 1.15
                sys.path.insert(0, HERE)
                from deck_kit import est_height
                need += est_height([[(text, {})]], (r[2] - r[0]) / 72,
                                   size=size, line=ls)
            if need > (r[3] - r[1]) / 72 + 0.06:
                over_frame.append((si, sh.text_frame.text[:40].replace("\n", " ")))

        # type floor. deck_kit tags the roles it owns (citation bar, caption,
        # eyebrow, title, sub, footer); those may sit below the body floor.
        # Everything else is body prose and may not.
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            role = (sh.name or "")
            if role.startswith("dk_"):
                continue
            for pa in sh.text_frame.paragraphs:
                for r_ in pa.runs:
                    if not r_.text.strip():
                        continue
                    sz = run_size_pt(r_)
                    if sz is None:
                        continue
                    if sz < CAPTION_FLOOR_PT:
                        floors.append((si, sz, "HARD", r_.text[:24]))
                    elif sz < min_body:
                        floors.append((si, sz, "body", r_.text[:24]))

        # screenshot / citation presence
        if manifest and si - 1 < len(manifest.get("slides", [])):
            info = manifest["slides"][si - 1]
            if info.get("content"):
                if not pics:
                    no_shot.append((si, ""))
                if not info.get("cite"):
                    no_cite.append((si, ""))
        elif not manifest:
            if not pics:
                no_shot.append((si, ""))

        # band geometry: the evidence strips must be the same height.
        # Crops taken from different pages have different heights, so a
        # full-width strip renders at a different height on every slide and
        # the whitespace above the band jumps from slide to slide -- the deck
        # visibly steps up and down. Pad the crops to a common aspect ratio
        # (deck_kit.pad_uniform) and every band lines up.
        # only a WIDE picture is an evidence band; a small inset is not
        wide = [p for p in pics if (p[0][2] - p[0][0]) > 0.6 * slide_w_pt]
        if wide:
            pr = max(wide, key=lambda p: (p[0][2] - p[0][0]) * (p[0][3] - p[0][1]))
            box = pr[0]
            bands.append((si, round(box[1], 3), round(box[3], 3)))
            # the caption must clear the image by a readable margin
            for tr, sh in texts:
                if (sh.name or "") == "dk_caption":
                    gap_pt = tr[1] - box[3]
                    if gap_pt < CAPTION_GAP_PT:
                        gaps.append((si, round(gap_pt / 72, 3),
                                     sh.text_frame.text[:24]))

        # highlight presence
        if require_highlight:
            for pr, psh in pics:
                try:
                    blob = psh.image.blob
                except Exception:
                    continue
                import io
                from PIL import Image
                try:
                    im = Image.open(io.BytesIO(blob)).convert("RGB")
                except Exception:
                    continue
                if im.width * im.height > 4_000_000:
                    im = im.resize((im.width // 2, im.height // 2))
                px = im.load()
                n = 0
                for y in range(im.height):
                    for x in range(im.width):
                        rr, gg, bb = px[x, y]
                        if _is_amber(rr, gg, bb):
                            n += 1
                if n < AMBER_MIN:
                    no_mark.append((si, psh.name or ""))

    # ---------- rendered checks ----------
    if do_render:
        pdf = render(pptx, outdir)
        pages = load_boxes(outdir)
        for pi, page in enumerate(pages, 1):
            words = word_boxes(page)
            fb = furniture.get(pi, [])
            body = []
            for x0, y0, x1, y1, t in words:
                inside_footer = any(x0 >= b[0] - 2 and x1 <= b[2] + 2 and
                                    y0 >= b[1] - 3 and y1 <= b[3] + 3 for b in fb)
                if not inside_footer:
                    body.append((x0, y0, x1, y1, t))
            for x0, y0, x1, y1, t in body:
                if y1 > FOOTER_TOP_PT:
                    low.append((pi, round(y1, 1), round(y0, 1), t))
                tol = 0 if strict_margin else HANG_PT
                if x1 > right_edge + tol:
                    right.append((pi, round(x1, 1), t))
            for i in range(len(body)):
                for j in range(i + 1, len(body)):
                    a, b = body[i], body[j]
                    if (a[0] < b[2] and a[2] > b[0]
                            and a[1] < b[3] and a[3] > b[1]):
                        overlaps.append((pi, a[4][:26], b[4][:26]))

    # ---------- placeholders ----------
    # markitdown is optional. Without it the deck's text is read straight out
    # of the pptx instead -- same result, no extra dependency.
    txt = ""
    try:
        txt = subprocess.run([sys.executable, "-m", "markitdown", pptx],
                             capture_output=True, text=True).stdout
    except Exception:
        txt = ""
    if not txt.strip():
        from pptx import Presentation as _P
        try:
            _prs = _P(pptx)
            txt = "\n".join(sh.text_frame.text for sl in _prs.slides
                             for sh in sl.shapes if sh.has_text_frame)
        except Exception:
            txt = ""
    junk = re.findall(r"(?i)\b(lorem|ipsum|xxxx|placeholder|TODO|FIXME)\b", txt)

    # ---------- report ----------
    print(f"deck        : {os.path.basename(pptx)}  ({len(prs.slides._sldIdLst)} slides)")
    print(f"right margin: {right_edge:.1f}pt (+{0 if strict_margin else HANG_PT:.0f}pt hanging tolerance)")
    print(f"footer band : {len(low)} word(s) below {FOOTER_TOP_PT/72:.2f}in")
    for pi, y1, y0, t in low[:8]:
        print(f"   p{pi}  y={y0/72:.2f}..{y1/72:.2f}  {t[:50]}")
    print(f"margins     : {len(right)} word(s) outside the right margin")
    for pi, x1, t in right[:8]:
        print(f"   p{pi}  x1={x1/72:.2f}in  {t[:50]}")
    print(f"overlap     : {len(overlaps)} intersecting text pair(s)")
    for pi, a, b in overlaps[:8]:
        print(f"   p{pi}  {a!r} x {b!r}")
    print(f"text/image  : {len(over_img)} text box(es) over a screenshot")
    for si, t in over_img[:8]:
        print(f"   p{si}  {t}")
    print(f"frame spill : {len(over_frame)} text box(es) taller than their frame")
    for si, t in over_frame[:8]:
        print(f"   p{si}  {t}")
    print(f"type floor  : {len(floors)} run(s) under the floor")
    for si, sz, kind, t in floors[:8]:
        print(f"   p{si}  {sz}pt [{kind}]  {t}")
    print(f"placeholders: {len(junk)}")
    print(f"screenshots : {len(no_shot)} slide(s) without one"
          + (f" -> {[s for s, _ in no_shot][:10]}" if no_shot else ""))
    print(f"citations   : {len(no_cite)} content slide(s) without one"
          + (f" -> {[s for s, _ in no_cite][:10]}" if no_cite else ""))
    if require_highlight:
        print(f"highlights  : {len(no_mark)} screenshot(s) with no highlight")
        for si, nm in no_mark[:8]:
            print(f"   p{si}  {nm}")

    # band alignment: every evidence strip must be the same height, so the
    # whitespace above it does not jump from slide to slide
    band_issue = ""
    if len(bands) >= 2:
        heights = [b[2] - b[1] for b in bands]
        spread = max(heights) - min(heights)
        if spread > BAND_HEIGHT_PT:
            band_issue = (f"the {len(bands)} evidence strips have different "
                          f"heights (spread {spread/72:.2f}in) -- pad them to "
                          f"a common aspect ratio with deck_kit.pad_uniform")
            print(f"band align  : {band_issue}")
            for si, t, b in bands:
                print(f"   p{si}  top={t/72:.3f}in bottom={b/72:.3f}in "
                      f"h={(b-t)/72:.3f}in")
    if gaps:
        print(f"caption gap : {len(gaps)} caption(s) closer than 0.15in to its crop")
        for si, g, t in gaps[:8]:
            print(f"   p{si}  {g:.3f}in  {t}")

    hard = bool(low or right or overlaps or over_img or over_frame or junk
                or no_shot or [f for f in floors if f[2] == "HARD"] or no_mark
                or band_issue or gaps)
    if keep:
        print(f"\nJPEGs kept in {outdir}")
        return (1 if hard else 0), outdir
    return (1 if hard else 0), outdir


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-render", dest="do_render", action="store_false")
    ap.add_argument("--require-highlight", action="store_true")
    ap.add_argument("--min-body", type=float, default=BODY_FLOOR_PT)
    ap.add_argument("--strict-margin", action="store_true")
    args = ap.parse_args(argv)
    code, _ = check(args.pptx, args.keep, args.do_render, args.min_body,
                    args.require_highlight, args.strict_margin)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
