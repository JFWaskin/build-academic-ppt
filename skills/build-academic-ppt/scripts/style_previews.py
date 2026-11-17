#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
style_previews -- render one sample slide per visual style.

"Which style do you want?" is a question nobody can answer from a name.
Seven preview PNGs turn it into a question everybody can answer -- and they
double as the README gallery and as a regression check on the theme system.

  python3 style_previews.py [--out DIR] [--sheets]
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import deck_kit as K          # noqa: E402
from themes import THEMES     # noqa: E402

SAMPLE_CITE = ("Li, D., Wu, K. (2025). Functional asymmetry in translation "
               "evaluation: evidence from six text-analytic pathways. "
               "Journal of Translation Studies, 18(2), 114–139. "
               "https://doi.org/10.1234/jts.2025.018")


def make_fake_shot(path, w=1400, h=620, seed=0):
    """A stand-in for a source crop: a page with a highlighted passage."""
    from PIL import ImageDraw
    img = Image.new("RGB", (w, h), (253, 252, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, 54], fill=(238, 233, 222))
    d.text((28, 20), "SOURCE DOCUMENT  ·  p. 52", fill=(90, 84, 74))
    y = 96
    for i, width in enumerate((0.86, 0.94, 0.72, 0.90, 0.80, 0.62)):
        if i == 2:
            d.rectangle([24, y - 8, 24 + int(w * width), y + 26], fill=(247, 225, 185))
        d.rectangle([24, y, 24 + int(w * width), y + 20], fill=(150, 145, 136))
        y += 44
    img.save(path)
    return path


def build_sample(theme_key, path, shot_path):
    K.use_theme(theme_key)
    t = K.theme()
    d = K.Deck(theme_key=theme_key, footer="样式预览 · STYLE PREVIEW")
    s, y = d.content(eyebrow="SECTION 02 · 方法",
                     title="文本层级的偏移如何构成可指认的证据",
                     cite=SAMPLE_CITE,
                     sub="六条路径共享同一个前提：偏移必须能落在具体的语言层级上。")
    K.txt(s, K.ML, y, K.CW / 2 - K.Inches(0.3), K.Inches(1.5),
          [[("研究问题", {"bold": True, "color": t.accent})],
           [("译文在哪些可指认的语言层级与原文发生偏移？", {})],
           [("三点结论", {"bold": True, "color": t.accent})],
           [("偏移可分层定位；证据强度随路径而变；转述不构成证据。", {})]],
          size=t.body_pt, line=1.25, space_after=3)
    K.shot(s, shot_path, K.ML + K.CW / 2, y, K.CW / 2, K.Inches(2.1),
           caption="原文 P52：textual panorama 的界定（高亮处）", valign="top")
    K.stat_row(s, K.ML, y + K.Inches(2.4), K.CW,
               [("六条路径", "6"), ("证据层级", "3"), ("语料规模", "≈48,700")])
    K.panel(s, K.ML, y + K.Inches(3.5), K.CW, K.Inches(0.9))
    K.txt(s, K.ML + K.Inches(0.25), y + K.Inches(3.68), K.CW - K.Inches(0.5),
          K.Inches(0.5),
          [[("先给结构，再给证据，最后给限度。", {"bold": True})]],
          size=t.body_pt, color=t.ink)
    d.save(path, check=False)
    return path


def render(pptx, outdir):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", outdir, pptx],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=True)
    pdf = os.path.join(outdir,
                       os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    subprocess.run(["pdftoppm", "-jpeg", "-r", "120", pdf,
                    os.path.join(outdir, "p")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=True)
    jpg = os.path.join(outdir, "p-1.jpg")
    return jpg if os.path.exists(jpg) else None


def contact_sheet(pngs, out, cols=2, width=900):
    """One sheet showing every style, for the README."""
    imgs = []
    for key, p in pngs:
        im = Image.open(p).convert("RGB")
        h = int(im.height * width / im.width)
        imgs.append((key, im.resize((width, h), Image.LANCZOS)))
    rows = (len(imgs) + cols - 1) // cols
    row_h = [max(im.height for _, im in imgs[r * cols:(r + 1) * cols]) + 26
             for r in range(rows)]
    sheet = Image.new("RGB", (cols * (width + 16) + 16,
                              sum(row_h) + 16), (238, 238, 238))
    y = 16
    for r in range(rows):
        x = 16
        for key, im in imgs[r * cols:(r + 1) * cols]:
            sheet.paste(im, (x, y))
            x += width + 16
        y += row_h[r]
    sheet.save(out, quality=92)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "assets", "previews"))
    ap.add_argument("--sheets", action="store_true",
                    help="also write the contact sheet")
    args = ap.parse_args(argv)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="styleprev_")
    shot = make_fake_shot(os.path.join(tmp, "sample.png"))
    made = []
    for key in sorted(THEMES):
        pptx = os.path.join(tmp, f"{key}.pptx")
        build_sample(key, pptx, shot)
        jpg = render(pptx, tmp)
        if not jpg:
            print(f"  {key}: RENDER FAILED")
            continue
        dest = os.path.join(out, f"{key}.jpg")
        Image.open(jpg).save(dest, quality=92)
        made.append((key, dest))
        print(f"  {key:16} -> {dest}")
    if args.sheets and made:
        sheet = os.path.join(out, "all-styles.jpg")
        contact_sheet(made, sheet)
        print(f"  contact sheet -> {sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
