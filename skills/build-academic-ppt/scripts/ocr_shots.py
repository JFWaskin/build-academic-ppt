#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_shots -- crop a passage out of a SCANNED pdf (no text layer).

`pdf_shots.py` relies on the text layer. When a source is a scan, there is no
text layer, `search_for()` finds nothing, and the natural conclusion -- "a
scanned book cannot be made into an evidence deck" -- is wrong. It can, by
OCR-ing the page and cropping the rendered image.

Pipeline
--------
  1. render the page with PyMuPDF at zoom Z
  2. OCR that render with tesseract (TSV output)
  3. cluster the words into VISUAL lines (block/par/line, then merged by
     vertical centre -- OCR splits one printed line into several fragments)
  4. match the needle against those lines with a normalised fuzzy match
  5. crop the rendered image over the matched line's x-range, but take the
     x-range of the whole text column so neighbouring lines are not sliced
     in half at the frame edge
  6. draw the amber highlight, then verify amber pixels are actually present

The renderer must be the same one used for the OCR corpus. If you OCR with
`pdftoppm` and crop with PyMuPDF, the two render the page differently, the
OCR text and the crop disagree, and the needle "cannot be found" even though
it is plainly there. This script uses PyMuPDF for both by construction.

Usage
-----
  python3 ocr_shots.py probe book.pdf 52 "占全书比例超出"
  python3 ocr_shots.py shots book.pdf jobs.json outdir/

jobs.json: [{"name": "s1", "page": 52, "needles": ["占全书比例超出"], "ctx": 2}]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher

import fitz
from PIL import Image, ImageDraw

ZOOM = 3.0
MARK = (255, 198, 96)
MARK_ALPHA = 110
AMBER_MIN_PIXELS = 40
CJK_PUNCT = "，。、；：？！“”‘’（）《》〈〉【】…—　·"


def _is_amber(r, g, b):
    return r >= 235 and 195 <= g <= 245 and 150 <= b <= 220


def count_highlight(img):
    small = img.convert("RGB")
    scale = 1
    if small.width * small.height > 4_000_000:
        small = small.resize((small.width // 2, small.height // 2))
        scale = 4
    px = small.load()
    n = 0
    for y in range(small.height):
        for x in range(small.width):
            r, g, b = px[x, y]
            if _is_amber(r, g, b):
                n += 1
    return n * scale


def normalize(s):
    s = s.strip()
    for ch in CJK_PUNCT + " \t\r\n":
        s = s.replace(ch, "")
    return s


def render_page(pdf, page_no, zoom=ZOOM):
    doc = fitz.open(pdf)
    page = doc[page_no - 1]
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    doc.close()
    return img


def _run_tesseract(src, lang):
    """Run tesseract and return (tsv_text, stderr_text, language_used).

    Three things go wrong here that all look like "tesseract is broken":

      * the language pack is not installed ("Failed loading language
        'chi_sim'"), which is common -- fall back to English and say so;
      * stderr is not valid UTF-8, which kills `text=True` outright and
        masks the real error behind a UnicodeDecodeError;
      * leptonica cannot open a file through a symlinked directory such as
        /tmp (which points at /private/tmp) when it is given the symlinked
        absolute path. Resolve the path before handing it over.
    """
    src = os.path.realpath(src)
    proc = subprocess.run(["tesseract", src, "stdout", "-l", lang, "tsv"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tsv = proc.stdout.decode("utf-8", errors="ignore")
    err = proc.stderr.decode("utf-8", errors="ignore")
    if ("Failed loading language" in err or "not found" in err) and "eng" not in lang:
        proc = subprocess.run(["tesseract", src, "stdout", "-l", "eng", "tsv"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        tsv = proc.stdout.decode("utf-8", errors="ignore")
        err = proc.stderr.decode("utf-8", errors="ignore")
        err += (f"\n[ocr_shots] language pack {lang!r} is not installed; "
                f"fell back to English only.")
        return tsv, err, "eng"
    if not tsv.strip() and err.strip():
        # an empty TSV with a message on stderr is a real failure; say what
        # it was instead of returning silence
        err += f"\n[ocr_shots] tesseract produced no output for {src}"
    return tsv, err, lang


def ocr_lines(img, lang="chi_sim+eng", tmpdir=None, tmpname=None):
    """OCR an image and return [(text, x0, y0, x1, y1)] in image pixels."""
    tmpdir = tmpdir or tempfile.mkdtemp(prefix="ocr_")
    src = os.path.join(tmpdir, (tmpname or "page") + ".png")
    img.save(src)

    # Do NOT use text=True here. Tesseract writes progress and warnings to
    # stderr in a local encoding, and on a Chinese page that byte stream can
    # be invalid UTF-8 -- subprocess then raises UnicodeDecodeError and the
    # whole OCR run dies on a page that OCRs perfectly well.
    tsv, err, lang = _run_tesseract(src, lang)

    lines = {}
    for row in tsv.splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) < 12:
            continue
        try:
            level = int(parts[0])
            block, par, line = int(parts[2]), int(parts[3]), int(parts[4])
            left, top, width, height = (int(parts[6]), int(parts[7]),
                                        int(parts[8]), int(parts[9]))
        except ValueError:
            continue
        if level != 5:
            continue
        text = parts[11].strip()
        if not text:
            continue
        key = (block, par, line)
        b = lines.setdefault(key, {"words": [], "y": [], "x0": [], "x1": []})
        b["words"].append(text)
        b["y"].append((top, top + height))
        b["x0"].append(left)
        b["x1"].append(left + width)

    if not lines and err.strip():
        # silence is the worst possible error message: say what tesseract said
        print(f"  !! ocr_shots: tesseract returned no lines\n{err.strip()}")

    # merge fragments that share a vertical band (OCR splits one printed line)
    raw = []
    for key, b in lines.items():
        y0 = min(y[0] for y in b["y"])
        y1 = max(y[1] for y in b["y"])
        raw.append({"text": " ".join(b["words"]),
                    "x0": min(b["x0"]), "x1": max(b["x1"]),
                    "y0": y0, "y1": y1,
                    "yc": (y0 + y1) / 2})
    raw.sort(key=lambda r: r["yc"])
    merged = []
    for r in raw:
        if merged and abs(r["yc"] - merged[-1]["yc"]) <= max(6, (r["y1"] - r["y0"]) * 0.45):
            m = merged[-1]
            m["text"] = (m["text"] + " " + r["text"]).strip()
            m["x0"] = min(m["x0"], r["x0"]); m["x1"] = max(m["x1"], r["x1"])
            m["y0"] = min(m["y0"], r["y0"]); m["y1"] = max(m["y1"], r["y1"])
            m["yc"] = (m["y0"] + m["y1"]) / 2
        else:
            merged.append(dict(r))
    return merged


def match_line(lines, needle):
    """Fuzzy match a needle against the OCR lines."""
    nn = normalize(needle)
    best = None
    for i, L in enumerate(lines):
        lt = normalize(L["text"])
        if not lt:
            continue
        if nn and nn in lt:
            score = 1.0
        else:
            score = SequenceMatcher(None, nn, lt).ratio()
        if best is None or score > best[0]:
            best = (score, i)
    if best is None or best[0] < 0.55:
        return None, 0.0
    return best[1], best[0]


def crop_scanned(pdf, page_no, needles, ctx=2, zoom=ZOOM, lang="chi_sim+eng",
                 out=None, tmpdir=None, verify=True):
    img = render_page(pdf, page_no, zoom)
    lines = ocr_lines(img, lang=lang, tmpdir=tmpdir,
                      tmpname=f"p{page_no}")
    if not lines:
        return None, ["no OCR lines"]
    notes = []
    hits = []
    for nd in needles:
        idx, score = match_line(lines, nd)
        if idx is None:
            notes.append(f"{nd!r}: no OCR line matched (best score too low)")
            continue
        notes.append(f"{nd!r}: matched line {idx} (score {score:.2f})")
        hits.append(idx)
    if not hits:
        return None, notes

    lo = max(0, min(hits) - ctx)
    hi = min(len(lines) - 1, max(hits) + ctx)
    sel = lines[lo:hi + 1]

    # the crop spans the whole text column so a neighbour line is not sliced
    col_x0 = min(L["x0"] for L in lines)
    col_x1 = max(L["x1"] for L in lines)
    pad = 14
    x0 = max(0, col_x0 - pad)
    x1 = min(img.width, col_x1 + pad)
    y0 = max(0, min(L["y0"] for L in sel) - 8)
    y1 = min(img.height, max(L["y1"] for L in sel) + 10)

    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for idx in set(hits):
        L = lines[idx]
        dr.rectangle([L["x0"] - 3, L["y0"] - 3, L["x1"] + 3, L["y1"] + 3],
                     fill=MARK + (MARK_ALPHA,))
    out_img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    crop = out_img.crop((int(x0), int(y0), int(x1), int(y1)))

    if verify:
        n = count_highlight(crop)
        if n < AMBER_MIN_PIXELS:
            return None, notes + [f"no highlight in the crop ({n} amber px)"]
        notes.append(f"highlight px: {n}")

    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        crop.save(out)
    return crop, notes


def cmd_probe(pdf, page_no, needles, lang="chi_sim+eng"):
    img = render_page(pdf, page_no)
    lines = ocr_lines(img, lang=lang)
    print(f"page {page_no}: {len(lines)} OCR lines")
    for i, L in enumerate(lines):
        print(f"  {i:3}  {L['text'][:90]}")
    for nd in needles:
        idx, score = match_line(lines, nd)
        print(f"{nd!r:40} -> line {idx} (score {score:.2f})"
              if idx is not None else f"{nd!r:40} -> NOT FOUND")


def cmd_shots(pdf, jobs_path, outdir, zoom=ZOOM, lang="chi_sim+eng"):
    jobs = json.load(open(jobs_path, encoding="utf-8"))
    os.makedirs(outdir, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="ocrshots_")
    man = {}
    fails = 0
    for j in jobs:
        img, notes = crop_scanned(pdf, j["page"], j["needles"],
                                  ctx=j.get("ctx", 2), zoom=zoom, lang=lang,
                                  out=None, tmpdir=tmpdir)
        if img is None:
            print(f"  !! {j['name']}: FAILED ({'; '.join(notes)})")
            fails += 1
            continue
        dest = os.path.join(outdir, j["name"] + ".png")
        img.save(dest)
        w, h = img.size
        print(f"  ok {j['name']:20} p{j['page']:<4} {w}x{h}  ar={w/h:.2f}")
        man[j["name"]] = {"file": dest, "page": j["page"],
                          "needles": j["needles"], "w": w, "h": h}
    mpath = os.path.join(outdir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2)
    print(f"  manifest -> {mpath}")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "shots"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--lang", default="chi_sim+eng")
    ap.add_argument("--zoom", type=float, default=ZOOM)
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        cmd_probe(a.args[0], int(a.args[1]), a.args[2:], a.lang)
        return 0
    fails = cmd_shots(a.args[0], a.args[1], a.args[2], a.zoom, a.lang)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
