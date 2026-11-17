#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deck_kit -- helpers for building academic decks with python-pptx.

Every workaround in here exists because stock python-pptx gets the thing wrong
in a way that fails *silently* -- no exception, just a broken deck. Each one
is marked with the failure it prevents.

1.  COLOUR. `run.font.color` is None on some builds, so `font.color.rgb = X`
    raises AttributeError. Colours are written straight into <a:solidFill>.

2.  NO CLIPPING. Text boxes do not clip. A box sized for one line lets the
    wrapped line 2 escape and overprint whatever sits below it. `fits()`
    predicts the real rendered height (including the CJK line box factor) and
    `txt()` records the overflow.

3.  LANGUAGE. A run with no `lang` attribute is laid out as en-US, so a run of
    Chinese with no spaces is treated as one unbreakable word and the whole
    paragraph runs off the right edge. Every run gets lang="zh-CN" and
    altLang="en-US". This one root cause explains three unrelated-looking
    defects: text overrunning the margin, text sitting on top of a
    screenshot, and Chinese quotation marks rendering as corner brackets.

4.  UNITS. `est_height()` returns INCHES; `Inches()` returns EMU. Adding the
    two produces a container 0.7in tall holding 658368in of text. Every
    geometry helper here names its unit, and `txt()` refuses a float where
    EMU is required instead of silently making a zero-width box.

5.  THEME RESOLUTION. Colour and typeface defaults are resolved at CALL time,
    not bound as default arguments. A default argument captures the value at
    definition time, so switching themes after import silently does nothing --
    which is exactly how a deck ends up with the wrong palette and no error.

6.  Z-ORDER. Pictures are always the topmost shape, so any text that lands
    under a screenshot is invisible. `Deck.check()` intersects every picture
    with every text box and reports the overlap.

Deliberately NOT done: no `cap="all"` (it turns "Garcia et al." into
"GARCIA ET AL." mid-sentence), no gradients, no shadows, no rounded corners.
"""
import json
import math
import os
import sys

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from themes import DEFAULT_THEME, THEMES, get as get_theme  # noqa: E402

# ------------------------------------------------------------------ state
_THEME = get_theme(DEFAULT_THEME)
WARN = []          # build-time overflow records
DECK = []          # one entry per deck built in this process (for check())


def use_theme(key):
    """Switch the active theme. Raises on an unknown key -- never falls back
    silently, because a silent fallback ships a deck in a style nobody chose."""
    global _THEME
    _THEME = get_theme(key)
    return _THEME


def theme():
    return _THEME


def IN(inches):
    """Inches -> EMU, named so the unit is visible at the call site."""
    return Inches(inches)


SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
ML = MR = Inches(0.85)
CW = SLIDE_W - ML - MR
FOOTER_Y = Inches(7.04)
CONTENT_BOTTOM = Inches(6.95)   # nothing may live below this

CJK = set("　、。，．：；！？（）〈〉《》「」『』【】—–…“”‘’·")


def _is_emu(v):
    return isinstance(v, int) and not isinstance(v, bool)


def E(v):
    """Cast a computed EMU value to int. Use after arithmetic that leaves a
    float (CW / 2, x + Inches(0.3))."""
    return int(round(v))


def _need_emu(name, v):
    """python-pptx accepts a float where EMU is expected and treats it as a
    tiny EMU count -- a table cell 0.001in wide, one character per line, the
    whole table stacked on itself. Fail loudly instead.

    A float is tolerated only when it is plainly an EMU quantity (>= 1000,
    i.e. bigger than a thousandth of an inch) and lands on a whole EMU. A
    small float is almost always inches passed by mistake.
    """
    if _is_emu(v):
        return v
    if isinstance(v, float) and v >= 1000:
        return int(round(v))
    raise TypeError(
        f"{name} must be an int in EMU (use IN(x) / Inches(x) / E(...)), got "
        f"{type(v).__name__} {v!r}. If you meant inches, wrap it: IN({v}). "
        f"If you meant a computed EMU value, wrap it: E({v}).")


# ------------------------------------------------------------------ fitting
def _units(t):
    """Approximate display width in 'full-width character' units."""
    u = 0.0
    for c in t:
        if c in CJK or "一" <= c <= "鿿" or "＀" <= c <= "￯":
            u += 1.0
        else:
            u += 0.52
    return u


LINE_BOX = 1.20   # the CJK font line box is ~1.2x the nominal line spacing


def _para_text(pl):
    if isinstance(pl, str):
        raise TypeError(
            "est_height() needs paragraphs as [[(text, {opts}), ...], ...]; a "
            "bare string silently collapses to its first character and the "
            "estimate comes out about five times too small.")
    try:
        parts = []
        for item in pl:
            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                raise TypeError(f"run must be (text, opts), got {item!r}")
            parts.append(str(item[0]))
        return "".join(parts)
    except TypeError:
        raise
    except Exception as e:  # pragma: no cover - defensive
        raise TypeError(f"cannot read paragraph {pl!r}: {e}")


def est_height(paras, width_in, size=None, line=1.15, space_after=0,
               width_factor=1.0):
    """Predicted rendered height in INCHES.

    width_factor shrinks the assumed line width. Latin text is set wider than
    the 0.52-unit estimate suggests, so a dense bibliography measured at full
    width comes out one line short. 0.85 is the value that keeps dense
    citation blocks honest; pass it for bibliographies and tables.
    """
    size = theme().body_pt if size is None else size
    if width_in > 100:
        raise ValueError(
            f"width_in looks like EMU ({width_in}); est_height() takes inches.")
    per_line = max(1.0, width_in * width_factor * 72.0 / size)
    h = 0.0
    for pl in paras:
        t = _para_text(pl)
        # an explicit newline starts a new rendered line
        segments = t.split("\n")
        n = 0
        for seg in segments:
            n += max(1, math.ceil(_units(seg) / per_line))
        h += n * size * line * LINE_BOX / 72.0
        h += space_after / 72.0
    return h


def fits(tag, paras, width_in, box_h_in, size=None, line=1.15, space_after=0,
         width_factor=1.0):
    """Record a warning if the text will not fit its box. Call before txt()."""
    h = est_height(paras, width_in, size, line, space_after, width_factor)
    if h > box_h_in + 0.005:
        WARN.append((tag, round(h, 2), round(box_h_in, 2)))
    return h


def report():
    if WARN:
        for t, h, b in WARN:
            print(f"  OVERFLOW  {t:22} needs {h}\" vs box {b}\"")
    else:
        print("  no estimated overflows")
    return len(WARN)


def clear_warnings():
    WARN.clear()


# ------------------------------------------------------------------ text
def _typeface(run, latin, ea):
    rPr = run._r.get_or_add_rPr()
    for tag, name in (("a:latin", latin), ("a:ea", ea), ("a:cs", latin)):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", name)


def _set_color(run, color):
    rPr = run._r.get_or_add_rPr()
    rPr.get_or_change_to_solidFill()
    sf = rPr.find(qn("a:solidFill"))
    srgb = sf.find(qn("a:srgbClr"))
    if srgb is None:
        srgb = etree.SubElement(sf, qn("a:srgbClr"))
    srgb.set("val", str(color))


def _lang(run, lang="zh-CN", alt="en-US"):
    """A run without `lang` is laid out as en-US: a Chinese paragraph with no
    spaces becomes one unbreakable word and overruns the box."""
    rPr = run._r.get_or_add_rPr()
    rPr.set("lang", lang)
    rPr.set("altLang", alt)


def _name(shape, name):
    """Tag a shape with a role name. The QA gate uses these to tell a
    citation bar from body prose, instead of guessing from the length of
    the text."""
    shape.name = name
    return shape


def txt(slide, x, y, w, h, runs, size=None, color=None, bold=False,
        italic=False, latin=None, ea=None, line=1.15, space_after=0,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=None,
        dark=False, font="sans", lang="zh-CN", role=None):
    """Place a text box.

    Colour, size and typeface resolve from the ACTIVE THEME at call time, so
    `use_theme()` after import actually changes the output. Sizes are in
    points; geometry is in EMU.

    `role` tags the shape with its job -- "dk_eyebrow", "dk_meta",
    "dk_label", "dk_body". The QA gate skips tagged shapes when it checks
    the type floor, because a label or an eyebrow is allowed below 14pt
    while body prose is not. Untagged text is treated as body prose.
    """
    t = theme()
    x = _need_emu("x", x); y = _need_emu("y", y)
    w = _need_emu("w", w); h = _need_emu("h", h)
    if size is None:
        size = t.body_pt
    if color is None:
        color = t.dark_ink if dark else t.ink
    f = t.fonts()
    if latin is None or ea is None:
        if font == "serif":
            latin = latin or f["serif_en"]
            ea = ea or f["serif_cn"]
        elif font == "mono":
            latin = latin or f["mono_en"]
            ea = ea or f["sans_cn"]
        else:
            latin = latin or f["sans_en"]
            ea = ea or f["sans_cn"]

    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(runs, str):
        runs = [[(runs, {})]]
    first = True
    for pl in runs:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.line_spacing = line
        p.space_before = Pt(0)
        p.space_after = Pt(space_after)
        pPr = p._p.get_or_add_pPr()
        pPr.append(etree.SubElement(pPr, qn("a:buNone")))
        for item in pl:
            text, ov = item if isinstance(item, (tuple, list)) else (item, {})
            o = dict(size=size, color=color, bold=bold, italic=italic,
                     latin=latin, ea=ea, spacing=spacing)
            o.update(ov or {})
            r = p.add_run()
            fnt = r.font
            fnt.size, fnt.bold, fnt.italic = Pt(o["size"]), o["bold"], o["italic"]
            fnt.name = o["latin"]
            _set_color(r, o["color"])
            rPr = r._r.get_or_add_rPr()
            if o["spacing"] is not None:
                rPr.set("spc", str(int(o["spacing"] * 100)))
            _typeface(r, o["latin"], o["ea"])
            _lang(r, lang)
            r.text = text
    if role:
        tb.name = role
    return tb


def replace_in_para(pa, old, new):
    """Replace text spanning multiple runs, keeping the first run's format."""
    runs = pa.runs
    if not runs:
        return False
    full = "".join(r.text for r in runs)
    k = full.find(old)
    if k < 0:
        return False
    a, b = k, k + len(old)
    spans, pos = [], 0
    for r in runs:
        spans.append((pos, pos + len(r.text), r))
        pos += len(r.text)
    first = True
    for s0, s1, r in spans:
        if s1 <= a or s0 >= b:
            continue
        lo, hi = max(a, s0) - s0, min(b, s1) - s0
        if first:
            r.text = r.text[:lo] + new + r.text[hi:]
            first = False
        else:
            r.text = r.text[:lo] + r.text[hi:]
    return True


def replace_text(prs, page_no, old, new):
    """Replace a phrase anywhere on a 1-based slide, across run boundaries."""
    for sh in prs.slides[page_no - 1].shapes:
        if not sh.has_text_frame:
            continue
        for pa in sh.text_frame.paragraphs:
            if replace_in_para(pa, old, new):
                return True
    return False


# ------------------------------------------------------------------ shapes
def rect(slide, x, y, w, h, fill=None, line=None, lw=0.75):
    x = _need_emu("x", x); y = _need_emu("y", y)
    w = _need_emu("w", w); h = _need_emu("h", h)
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    spPr = s._element.spPr
    for tag in ("a:solidFill", "a:noFill", "a:ln"):
        el = spPr.find(qn(tag))
        if el is not None:
            spPr.remove(el)
    ln = spPr.makeelement(qn("a:ln"), {})
    if line is None:
        etree.SubElement(ln, qn("a:noFill"))
    else:
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", str(line))
        ln.set("w", str(int(lw * 12700)))
    spPr.append(ln)
    tag = "a:solidFill" if fill is not None else "a:noFill"
    el = spPr.makeelement(qn(tag), {})
    if fill is not None:
        etree.SubElement(el, qn("a:srgbClr")).set("val", str(fill))
    spPr.insert_element_before(el, "a:ln", "a:effectLst", "a:effectDag",
                               "a:scene3d", "a:sp3d", "a:extLst")
    s.shadow.inherit = False
    return s


def hrule(slide, x, y, w, color=None, pt=None):
    t = theme()
    return rect(slide, x, y, w, Pt(pt if pt is not None else t.rule_pt),
                fill=color or t.rule)


def new_slide(prs, dark=False):
    t = theme()
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=t.dark_bg if dark else t.bg)
    return s


# ------------------------------------------------------------------ images
def shot(slide, path, x, y, w, h, caption=None, valign="center",
         cap_w=None, cap_size=None, dark=False, label=None):
    """Place a screenshot fitted inside (w,h), preserving aspect, framed and
    captioned. On a dark slide the mat stays light: a crop is paper."""
    t = theme()
    cap_size = cap_size or t.cap_pt
    iw, ih = Image.open(path).size
    ar = iw / ih
    if w / h > ar:
        fh = h; fw = h * ar
    else:
        fw = w; fh = w / ar
    fw, fh = int(fw), int(fh)
    fx = int(x + (w - fw) / 2)
    fy = int(y if valign == "top" else y + (h - fh) / 2)
    mat = t.mat_on_dark if dark else t.bg_soft
    rect(slide, fx - Inches(0.045), fy - Inches(0.045), fw + Inches(0.09),
         fh + Inches(0.09), fill=mat, line=t.dark_rule if dark else t.rule)
    slide.shapes.add_picture(path, fx, fy, fw, fh)
    if caption:
        ccol = t.dark_ink_soft if dark else t.ink_soft
        _name(txt(slide, fx, fy + fh + Inches(0.10), cap_w or fw, Inches(0.44),
                  [[(caption, {})]], size=cap_size, color=ccol, line=1.22,
                  dark=dark), "dk_caption")
    return fx, fy, fw, fh


def swap_pic(slide, old_shape, new_path, box_w=None, box_h=None,
             left=None, top=None):
    """Replace a picture in place, preserving z-order."""
    L, T, W, H = old_shape.left, old_shape.top, old_shape.width, old_shape.height
    iw, ih = Image.open(new_path).size
    ar = iw / ih
    nw = int(box_w) if box_w else int(W)
    nh = int(nw / ar)
    if box_h and nh > int(box_h):
        nh = int(box_h); nw = int(nh * ar)
    l = int(left) if left is not None else L + int((W - nw) / 2)
    t = int(top) if top is not None else T
    spTree = slide.shapes._spTree
    idx = list(spTree).index(old_shape._element)
    old_shape._element.getparent().remove(old_shape._element)
    pic = slide.shapes.add_picture(new_path, l, t, nw, nh)
    spTree.remove(pic._element)
    spTree.insert(idx, pic._element)
    return pic


# ------------------------------------------------------------------ helpers
def stat_row(slide, x, y, w, items, value_pt=23, gap=0.18, dark=False,
             value_color=None, label_color=None, align=PP_ALIGN.LEFT):
    """A row of big numbers with labels under them.

    Every value shares ONE font size, chosen as the largest size at which no
    value wraps. A row where each tile picks its own size is a row where
    "48,700" wraps to "48,7 / 00" and the second line lands on the label.
    """
    t = theme()
    n = len(items)
    tile_w = (w - Inches(gap) * (n - 1)) / n
    size = value_pt
    for label, value in items:
        while size > 10 and _units(str(value)) > tile_w / 914400 * 72 / size:
            size -= 0.5
    for i, (label, value) in enumerate(items):
        tx = x + int((tile_w + Inches(gap)) * i)
        txt(slide, tx, y, int(tile_w), Inches(size / 72 * 1.6),
            [[(str(value), {"bold": True})]], size=size,
            color=value_color or (t.dark_ink if dark else t.ink),
            font="serif", line=1.0)
        _name(txt(slide, tx, y + Inches(size / 72 * 1.6) + Inches(0.04),
                  int(tile_w), Inches(0.5), [[(str(label), {})]],
                  size=t.label_pt,
                  color=label_color or (t.dark_ink_soft if dark else t.ink_soft),
                  line=1.15), "dk_label")
    return y + Inches(size / 72 * 1.6) + Inches(0.04) + Inches(0.5)


def panel(slide, x, y, w, h, dark=False, accent=True):
    """A flat panel with an accent bar on its left edge. No rounded corners,
    no shadow -- rounded card stacks read as machine-generated."""
    t = theme()
    rect(slide, x, y, w, h, fill=t.bg_deep)
    if accent:
        rect(slide, x, y, Inches(t.accent_bar_in), h, fill=t.accent)
    return y + h


# ------------------------------------------------------------------ geometry
def _overlap_area(a, b):
    """Overlap area in EMU^2. Tests intersection BEFORE multiplying: two
    negative widths multiply to a positive number, which reads as a huge
    overlap that does not exist."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if not (ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0):
        return 0
    return (min(ax1, bx1) - max(ax0, bx0)) * (min(ay1, by1) - max(ay0, by0))


def _shape_rect(sh):
    if sh.left is None or sh.top is None:
        return None
    return (sh.left, sh.top, sh.left + (sh.width or 0),
            sh.top + (sh.height or 0))


# ------------------------------------------------------------------ deck
class Deck:
    """A deck. `theme` picks the style, `footer` is the running footer text
    (never hard-coded -- the previous version shipped one project's footer
    string into every deck it built)."""

    def __init__(self, theme_key=None, footer="", title="", author=""):
        if theme_key:
            use_theme(theme_key)
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = SLIDE_W, SLIDE_H
        self.n = 0
        self.footer_text = footer
        self.title = title
        self.author = author
        self._index = []
    # -- slides ---------------------------------------------------------
    def blank(self, dark=False):
        s = new_slide(self.prs, dark)
        self._index.append({"dark": dark, "content": False, "cite": None})
        return s

    def content(self, eyebrow=None, title=None, cite=None, sub=None, dark=False,
                accent=None):
        """A content slide with the standard header. Returns (slide, y)."""
        s = self.blank(dark=dark)
        y = self.head(s, eyebrow or "", title or "", sub=sub, cite=cite,
                      accent=accent, dark=dark)
        self._index[-1]["content"] = True
        self._index[-1]["cite"] = cite
        return s, y

    def divider(self, eyebrow, title, sub=None):
        s = self.blank(dark=True)
        t = theme()
        _name(txt(s, ML, Inches(2.7), CW, Inches(0.3), [[(eyebrow, {})]],
                  size=t.eyebrow_pt, color=t.accent_soft, spacing=1.6, line=1.0,
                  dark=True), "dk_eyebrow")
        _name(txt(s, ML, Inches(3.05), CW, Inches(0.9), [[(title, {})]],
                  size=t.title_pt + 6, color=t.dark_ink, bold=True, font="serif",
                  line=1.1, dark=True), "dk_title")
        if sub:
            _name(txt(s, ML, Inches(4.0), Inches(8.5), Inches(0.6),
                      [[(sub, {})]], size=t.sub_pt, color=t.dark_ink_soft,
                      italic=True, line=1.25, font="serif", dark=True),
                  "dk_sub")
        self.footer(s, dark=True)
        return s

    # -- furniture ------------------------------------------------------
    def stat_row(self, slide, x, y, w, items, **kw):
        """A row of big numbers with labels under them. Also available as
        the module-level `deck_kit.stat_row`."""
        return stat_row(slide, x, y, w, items, **kw)

    def panel(self, slide, x, y, w, h, **kw):
        """A flat panel with an accent bar. Also available as the
        module-level `deck_kit.panel`."""
        return panel(slide, x, y, w, h, **kw)

    def footer(self, slide, dark=False):
        t = theme()
        self.n = len(self.prs.slides._sldIdLst)
        c = t.dark_ink_soft if dark else t.ink_soft
        if self.footer_text:
            sh = txt(slide, ML, FOOTER_Y, Inches(8), Inches(0.22),
                     [[(self.footer_text, {})]], size=9, color=c, spacing=0.8,
                     line=1.0, dark=dark)
            sh.name = "dk_footer_text"
        sh = txt(slide, SLIDE_W - MR - Inches(1.2), Inches(7.00), Inches(1.2),
                 Inches(0.26), [[(f"{self.n:02d}", {})]], size=13, color=c,
                 font="serif", align=PP_ALIGN.RIGHT, line=1.0, dark=dark)
        sh.name = "dk_footer_num"

    def head(self, slide, eyebrow, title, sub=None, cite=None, accent=None,
             dark=False):
        """Header + optional citation bar. Returns the y content may start."""
        t = theme()
        ec = t.dark_ink_soft if dark else t.ink_soft
        tc = t.dark_ink if dark else t.ink
        acc = accent or (t.accent_soft if dark else t.accent)
        if eyebrow:
            _name(txt(slide, ML, Inches(0.34), CW, Inches(0.26),
                      [[(eyebrow, {})]],
                      size=t.eyebrow_pt, color=acc, spacing=1.6, line=1.0,
                      dark=dark), "dk_eyebrow")
        if title:
            th = est_height([[(title, {})]], CW / 914400, size=t.title_pt,
                            line=1.1)
            _name(txt(slide, ML, Inches(0.62), CW, Inches(th + 0.06),
                      [[(title, {})]], size=t.title_pt, color=tc, bold=True,
                      font="serif", line=1.1, dark=dark), "dk_title")
        hrule(slide, ML, Inches(1.20), CW, t.dark_rule if dark else t.rule)
        y = Inches(1.34)
        if cite:
            # A citation bar must be sized for the lines it actually wraps to,
            # or line 2 escapes and overprints the content below. Bibliographies
            # are set wider than the estimate suggests -> measure at 0.85.
            lines = max(1, math.ceil(_units(cite) /
                                     ((CW / 914400) * 0.85 * 72 / t.cite_pt)))
            h = Inches(0.24 * lines + 0.14)
            _name(txt(slide, ML, y, CW, h, [[(cite, {})]], size=t.cite_pt,
                      color=ec, font="serif", italic=True, line=1.24,
                      dark=dark), "dk_cite")
            y = y + h + Inches(0.10)
        if sub:
            sublines = max(1, math.ceil(_units(sub) /
                                        ((CW / 914400) * 72 / t.sub_pt)))
            sh = Inches(0.26 * sublines + 0.12)
            _name(txt(slide, ML, y, CW, sh, [[(sub, {})]], size=t.sub_pt,
                      color=ec, font="serif", italic=True, line=1.26,
                      dark=dark), "dk_sub")
            y = y + sh + Inches(0.08)
        self.footer(slide, dark)
        return y

    # -- output ---------------------------------------------------------
    def write_manifest(self, path):
        """A sidecar describing each slide. qa_deck.py reads it to know which
        slides are content slides (and therefore owe a screenshot and a
        citation) -- a question the pptx alone cannot answer."""
        prs = Presentation(path)
        slides = []
        for i, slide in enumerate(prs.slides):
            info = self._index[i] if i < len(self._index) else {}
            pics = sum(1 for sh in slide.shapes
                       if sh.shape_type == MSO_SHAPE_TYPE.PICTURE)
            title = ""
            for sh in slide.shapes:
                if sh.has_text_frame and sh.text_frame.text.strip():
                    for pa in sh.text_frame.paragraphs:
                        for r in pa.runs:
                            sz = r._r.get_or_add_rPr().get("sz")
                            if sz and int(sz) >= 2200:
                                title = r.text
                                break
                        if title:
                            break
                if title:
                    break
            slides.append({"kind": "content" if info.get("content") else "other",
                           "cite": bool(info.get("cite")),
                           "pics": pics,
                           "title": title,
                           "dark": bool(info.get("dark"))})
        mpath = os.path.splitext(path)[0] + ".manifest.json"
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump({"theme": theme().key, "footer": self.footer_text,
                       "title": self.title, "slides": slides},
                      fh, ensure_ascii=False, indent=2)
        return mpath

    def save(self, path, check=True, manifest=True):
        report()
        self.prs.save(path)
        if manifest:
            self.write_manifest(path)
        if check:
            problems = self.check(path)
            if problems:
                print(f"  {len(problems)} build-time geometry problem(s) -- see "
                      f"CHECK lines above")
        return path

    def check(self, path=None):
        """Build-time geometry check, straight off the saved pptx.

        Catches the defects a per-box bounds check misses:
          * text overprinting a screenshot (pictures are topmost)
          * text escaping its own frame (boxes do not clip)
          * two text frames overlapping each other
          * content below the footer band or past the right margin
          * a content slide with no screenshot
        """
        target = path or self._tmp_path
        prs = Presentation(target)
        t = theme()
        right_edge_pt = (SLIDE_W - MR) / 914400 * 72
        issues = []
        for si, slide in enumerate(prs.slides, 1):
            pics, texts, shapes = [], [], []
            for sh in slide.shapes:
                r = _shape_rect(sh)
                if r is None:
                    continue
                if (sh.name or "").startswith("dk_footer"):
                    continue          # footer furniture is not content
                if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    pics.append((r, sh))
                elif sh.has_text_frame and sh.text_frame.text.strip():
                    texts.append((r, sh))
                else:
                    shapes.append(r)
            # text over a screenshot
            for pr, psh in pics:
                for tr, tsh in texts:
                    area = _overlap_area(pr, tr)
                    if area > 0.004 * (pr[2] - pr[0]) * (pr[3] - pr[1]):
                        issues.append((si, "text-over-image",
                                       tsh.text_frame.text[:40].replace("\n", " ")))
            # text over text
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    area = _overlap_area(texts[i][0], texts[j][0])
                    if area > 0.002 * min((texts[i][0][2] - texts[i][0][0]) *
                                          (texts[i][0][3] - texts[i][0][1]),
                                          (texts[j][0][2] - texts[j][0][0]) *
                                          (texts[j][0][3] - texts[j][0][1])):
                        issues.append((si, "text-over-text",
                                       texts[i][1].text_frame.text[:30]))
            # text escaping its own frame
            for r, sh in texts:
                need = 0.0
                for pa in sh.text_frame.paragraphs:
                    if not pa.runs:
                        continue
                    size = pa.runs[0].font.size.pt if pa.runs[0].font.size else t.body_pt
                    text = "".join(x.text for x in pa.runs)
                    ls = pa.line_spacing if isinstance(pa.line_spacing, float) else 1.15
                    need += est_height([[(text, {})]], (r[2] - r[0]) / 914400,
                                       size=size, line=ls)
                if need > (r[3] - r[1]) / 914400 + 0.06:
                    issues.append((si, "text-overflows-frame",
                                   sh.text_frame.text[:40].replace("\n", " ")))
            # margins and footer band
            for r, sh in texts:
                if r[3] > CONTENT_BOTTOM:
                    issues.append((si, "below-content-band",
                                   sh.text_frame.text[:40].replace("\n", " ")))
                if r[2] / 914400 * 72 > right_edge_pt + 2:
                    issues.append((si, "past-right-margin",
                                   sh.text_frame.text[:40].replace("\n", " ")))
            # a content slide needs a screenshot
            if si - 1 < len(self._index) and self._index[si - 1]["content"] \
                    and not pics:
                issues.append((si, "content-slide-without-screenshot", ""))
            # a content slide needs a citation
            if si - 1 < len(self._index) and self._index[si - 1]["content"] \
                    and not self._index[si - 1]["cite"]:
                issues.append((si, "content-slide-without-citation", ""))
        for si, kind, detail in issues:
            print(f"  CHECK  slide {si:>2}  {kind:32} {detail}")
        return issues
