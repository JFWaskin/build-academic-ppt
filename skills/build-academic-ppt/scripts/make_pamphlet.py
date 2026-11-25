#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a real trifold pamphlet from the skill's own theme + crop pipeline,
then compose it into a photorealistic-looking mockup.

Everything here is produced by the skill's own machinery: the palette comes
from scripts/themes.py, the screenshot comes from scripts/ocr_shots.py. The
mockup is composition, not invention -- the print itself is the real output.
"""
import os
import sys
import math
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops  # noqa: E402

from themes import get as get_theme  # noqa: E402
import ocr_shots  # noqa: E402

OUT = "/Users/jonathanwaskin/Library/CloudStorage/OneDrive-Personal/autumn semester 2026/third/1/skill-demo"
PDF = "/Users/jonathanwaskin/Library/CloudStorage/OneDrive-Personal/autumn semester 2026/third/1/_build/wangshuhuai_2023.pdf"
os.makedirs(OUT, exist_ok=True)

T = get_theme("paper-warm")
C = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # noqa: E731

SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"
HEITI_L = "/System/Library/Fonts/STHeiti Light.ttc"
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"


def serif(size, index=0):
    return ImageFont.truetype(SONGTI, size, index=index)


def sans(size, light=False):
    return ImageFont.truetype(HEITI_L if light else HEITI, size, index=0)


def serif_en(size):
    return ImageFont.truetype(GEORGIA, size)


# ---------------------------------------------------------------- crop
def make_crop():
    """A real crop from the scanned source, with the amber highlight."""
    path = os.path.join(OUT, "pamphlet_evidence.png")
    if os.path.exists(path):
        return path
    crop, notes = ocr_shots.crop_scanned(
        PDF, 2, ["将时间倒错拉平"], ctx_before=1, ctx_after=2, out=path)
    if crop is None:
        print("crop failed:", notes)
        return None
    print("crop ok:", crop.size, "via", notes)
    return path


# ---------------------------------------------------------------- helpers
def text(draw, xy, s, font, fill, anchor="la", spacing=0):
    draw.text(xy, s, font=font, fill=fill, anchor=anchor)
    return draw.textlength(s, font=font)


def wrap(draw, s, font, max_w):
    """Wrap a mixed CJK/latin string by measured width."""
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        t = cur + ch
        if draw.textlength(t, font=font) > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def fit_size(draw, s, path, max_w, desired_px, index=0, floor_px=10):
    """The largest size <= desired_px at which the string fits max_w.

    Type on a fixed panel has to be MEASURED. Seven CJK glyphs at 15mm are
    105mm wide, and the panel is 71mm -- the line runs into the next panel
    and nobody notices until the sheet is on the press.
    """
    size = desired_px
    while size > floor_px:
        f = ImageFont.truetype(path, size, index=index) if index is not None \
            else ImageFont.truetype(path, size)
        if draw.textlength(s, font=f) <= max_w:
            return f
        size -= 1
    return ImageFont.truetype(path, floor_px, index=index) if index is not None \
        else ImageFont.truetype(path, floor_px)


def paragraph(draw, xy, s, font, fill, max_w, leading, max_lines=None):
    """leading MUST be larger than the font size -- a leading of 0.63em piles
    the lines on top of each other."""
    x, y = xy
    lines = wrap(draw, s, font, max_w)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
    for ln in lines:
        text(draw, (x, y), ln, font, fill)
        y += leading
    return y


# ---------------------------------------------------------------- pamphlet
MM = 200 / 25.4                      # 200 dpi
PW, PH = int(297 * MM), int(210 * MM)  # A4 landscape
PANEL = PW // 3
GUT = int(3 * MM)                     # fold gutter


def build_pamphlet(crop_path):
    img = Image.new("RGB", (PW, PH), C(T.bg))
    d = ImageDraw.Draw(img)

    ink, ink_soft = C(T.ink), C(T.ink_soft)
    accent, accent2 = C(T.accent), C(T.accent2)
    rule = C(T.rule)

    m = int(14 * MM)                    # panel margin
    colw = PANEL - 2 * m                # usable column width

    def title_font(s_, desired_mm):
        return fit_size(d, s_, SONGTI, colw, int(desired_mm * MM))

    def label_font(s_, desired_mm):
        return fit_size(d, s_, HEITI, colw, int(desired_mm * MM))

    # ---------------------------------------------------- panel 1: back cover
    x = m
    y = int(14 * MM)
    text(d, (x, y), "文献基础与方法论评议", label_font("文献基础与方法论评议", 6.5), accent)
    y += int(10 * MM)
    for ln in ("以译作为中心的", "翻译批评"):
        f = title_font(ln, 10.5)
        text(d, (x, y), ln, f, ink)
        y += int(14 * MM)
    d.rectangle([x, y, x + int(30 * MM), y + int(0.9 * MM)], fill=accent)
    y += int(6 * MM)
    y = paragraph(d, (x, y),
                  "译文在哪些可指认的语言层级与原文发生偏移？"
                  "这些偏移造成何种意义、信息结构或衔接效果？",
                  sans(int(5.6 * MM)), ink, colw, int(8.6 * MM))
    y += int(2 * MM)
    d.line([x, y, x + colw, y], fill=rule, width=2)
    y += int(5 * MM)
    text(d, (x, y), "本文依据", serif(int(6.5 * MM)), accent2)
    y += int(9 * MM)
    y = paragraph(d, (x, y),
                  "王树槐. 文学翻译的叙事批评模式建构[J]. "
                  "外国语, 2023, 46(2): 88-98.",
                  serif(int(5.4 * MM)), ink_soft, colw, int(8 * MM))
    y += int(4 * MM)
    for a, b in (("先给结构", "研究问题与十二要素模型"),
                 ("再给证据", "每页一处可回查的原文截图"),
                 ("最后给限度", "因果方向不能凭一次对比确证")):
        d.rectangle([x, y + int(0.9 * MM), x + int(1.3 * MM),
                     y + int(3.4 * MM)], fill=accent)
        text(d, (x + int(3.8 * MM), y), a, sans(int(5.6 * MM)), ink)
        text(d, (x + int(33 * MM), y + int(0.7 * MM)), b,
             sans(int(4.8 * MM), light=True), ink_soft)
        y += int(9.5 * MM)

    # ------------------------------------------------------ panel 2: inside
    x = PANEL + m
    y = int(14 * MM)
    text(d, (x, y), "六条文本分析路径", label_font("六条文本分析路径", 6.5), accent)
    y += int(10 * MM)
    f2 = fit_size(d, "彼此并非互斥范式", SONGTI, colw, int(8.5 * MM))
    text(d, (x, y), "彼此并非互斥范式", f2, ink)
    y += int(12 * MM)
    d.rectangle([x, y, x + int(26 * MM), y + int(0.8 * MM)], fill=accent2)
    y += int(5 * MM)
    paths = ["对比语言学路径", "计量文体学路径", "文学文体学路径",
             "功能文体学路径", "经典叙事学路径", "文学批评理论路径"]
    for i, pth in enumerate(paths):
        text(d, (x, y), f"{i + 1:02d}", serif_en(int(7 * MM)), accent)
        fp = fit_size(d, pth, SONGTI, colw - int(11 * MM), int(7.5 * MM))
        text(d, (x + int(10 * MM), y), pth, fp, ink)
        y += int(11 * MM)
        if i < len(paths) - 1:
            d.line([x, y - int(4 * MM), x + colw, y - int(4 * MM)],
                   fill=rule, width=1)

    if crop_path and os.path.exists(crop_path):
        shot = Image.open(crop_path).convert("RGB")
        ch = int(colw * shot.height / shot.width)
        shot = shot.resize((colw, ch), Image.LANCZOS)
        cy = PH - int(46 * MM)
        d.rectangle([x - int(0.9 * MM), cy - int(0.9 * MM),
                     x + colw + int(0.9 * MM), cy + ch + int(0.9 * MM)],
                    fill=C(T.bg_soft), outline=rule, width=1)
        img.paste(shot, (x, cy))
        text(d, (x, cy + ch + int(2.6 * MM)),
             "原文 P2：将时间倒错拉平为「顺序」（高亮处）",
             sans(int(4.4 * MM), light=True), ink_soft)

    # ------------------------------------------------------ panel 3: cover
    x = 2 * PANEL + m
    band_h = int(58 * MM)
    if crop_path and os.path.exists(crop_path):
        shot = Image.open(crop_path).convert("RGB")
        band_w = PANEL
        sh = int(band_w * shot.height / shot.width)
        shot = shot.resize((band_w, sh), Image.LANCZOS)
        if sh < band_h:
            # pad with paper only above, so the crop sits on the fold line
            canvas = Image.new("RGB", (band_w, band_h), C(T.bg_soft))
            canvas.paste(shot, (0, band_h - sh))
            shot = canvas
        else:
            top = (sh - band_h) // 2
            shot = shot.crop((0, top, band_w, top + band_h))
        img.paste(shot, (2 * PANEL, 0))
        d.rectangle([2 * PANEL, band_h - int(0.9 * MM),
                     2 * PANEL + PANEL, band_h], fill=accent)

    y = band_h + int(12 * MM)
    text(d, (x, y), "功能性与翻译研究 · 文献基础与方法论评议",
         label_font("功能性与翻译研究 · 文献基础与方法论评议", 6.0), accent)
    y += int(9 * MM)
    for ln, col in (("以译作为中心的", ink), ("翻译批评", ink),
                    ("六条文本分析路径", accent)):
        f = title_font(ln, 10.5)
        text(d, (x, y), ln, f, col)
        y += int(14 * MM)
    y += int(3 * MM)
    y = paragraph(d, (x, y), "每页的论断，都能回到原文的某一段。",
                  serif(int(5.6 * MM)), ink_soft, colw, int(8.6 * MM))
    d.line([x, PH - int(18 * MM), x + colw, PH - int(18 * MM)], fill=rule, width=2)
    text(d, (x, PH - int(13 * MM)), "build-academic-ppt",
         serif_en(int(6.0 * MM)), ink_soft)
    text(d, (x + colw, PH - int(13 * MM)), "2026",
         serif_en(int(6.0 * MM)), ink_soft, anchor="ra")

    # ------------------------------------------------------------- folds
    overlay = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    for fx in (PANEL, 2 * PANEL):
        g = Image.new("L", (GUT, PH), 0)
        gd = ImageDraw.Draw(g)
        for i in range(GUT):
            v = int(92 * math.sin(math.pi * (i + 0.5) / GUT))
            gd.line([(i, 0), (i, PH)], fill=v)
        g = g.filter(ImageFilter.GaussianBlur(3))
        strip = Image.new("RGBA", (GUT, PH), (0, 0, 0, 0))
        strip.putalpha(g)
        overlay.paste(strip, (fx - GUT // 2, 0), strip)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    return img


# ---------------------------------------------------------------- mockup
def build_mockup(leaflet):
    W, H = 2400, 1600
    # backdrop: warm neutral studio sweep
    bg = Image.new("RGB", (W, H))
    bd = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        v = int(228 - 46 * (t ** 1.5))
        bd.line([(0, y), (W, y)], fill=(v, v - 3, v - 8))
    # a soft pool of light behind the leaflet
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.06, -H * 0.28, W * 0.98, H * 0.92], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    bg = Image.composite(Image.new("RGB", (W, H), (255, 252, 246)), bg, glow)

    # the leaflet, laid down at a slight angle
    lw = int(W * 0.74)
    lh = int(leaflet.height * lw / leaflet.width)
    small = leaflet.resize((lw, lh), Image.LANCZOS).convert("RGBA")

    # contact shadow
    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([W * 0.5 - lw / 2 + 18, H * 0.5 - lh / 2 + 34,
                          W * 0.5 + lw / 2 + 30, H * 0.5 + lh / 2 + 44],
                         radius=10, fill=190)
    sh = sh.filter(ImageFilter.GaussianBlur(34))
    bg = Image.composite(Image.new("RGB", (W, H), (58, 52, 46)), bg, sh)

    # perspective + rotation for a laid-on-a-table feel
    ang = math.radians(-3.2)
    cx, cy = W * 0.5, H * 0.5
    k = 0.13                                   # keystone: far edge a little narrower
    src = [(0, 0), (lw, 0), (lw, lh), (0, lh)]
    dst = []
    for (x, y) in src:
        x -= lw / 2; y -= lh / 2
        f = 1 + k * (-y / lh)                  # far edge slightly narrower
        x *= f; y *= f
        # rotate
        rx = x * math.cos(ang) - y * math.sin(ang)
        ry = x * math.sin(ang) + y * math.cos(ang)
        dst.append((rx + cx, ry + cy))
    coeffs = _perspective_coeffs(dst, src)

    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sheet.paste(small, (0, 0))
    sheet = sheet.transform((W, H), Image.PERSPECTIVE, coeffs,
                            Image.BICUBIC, fillcolor=(0, 0, 0, 0))

    # light the sheet: a gentle diagonal sheen, keeping the alpha intact
    sheen = Image.new("L", (W, H), 0)
    sd2 = ImageDraw.Draw(sheen)
    for i in range(-H, W, 2):
        sd2.line([(i, 0), (i + H, H)],
                 fill=int(26 * (1 - abs(i - W * 0.3) / (W * 0.9))))
    sheen = sheen.filter(ImageFilter.GaussianBlur(90))
    rgb = sheet.convert("RGB")
    lit = Image.composite(Image.new("RGB", (W, H), (255, 255, 250)), rgb, sheen)
    sheet = Image.merge("RGBA", (*lit.split(), sheet.split()[3]))

    bg.paste(sheet, (0, 0), sheet)

    # vignette + grain
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.30, -H * 0.34, W * 1.30, H * 1.34], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(240))
    bg = Image.composite(bg, Image.new("RGB", (W, H), (120, 112, 102)), vig)

    noise = Image.effect_noise((W, H), 7).convert("L")
    bg = ImageChops.overlay(bg, Image.merge("RGB", (noise, noise, noise)))
    bg = bg.point(lambda v: int(min(255, max(0, v * 0.985 + 6))))
    return bg


def _perspective_coeffs(dst, src):
    """Solve the 8 coefficients for PIL's PERSPECTIVE transform."""
    A = []
    B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        B.append(v)
    import numpy as np
    res = np.linalg.solve(np.array(A, dtype=float), np.array(B, dtype=float))
    return tuple(res)


if __name__ == "__main__":
    crop = make_crop()
    leaf = build_pamphlet(crop)
    p1 = os.path.join(OUT, "pamphlet_折页_印刷稿.png")
    leaf.save(p1)
    print("pamphlet:", p1, leaf.size)
    mock = build_mockup(leaf)
    p2 = os.path.join(OUT, "pamphlet_折页_样张.png")
    mock.save(p2, quality=95)
    print("mockup:", p2, mock.size)
