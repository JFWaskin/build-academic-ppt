#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
themes -- the visual style registry for academic decks.

A "style" here is not a colour swap. Each theme is a complete, self-consistent
system: surface colours, two accents, hairline colour, the dark-slide variant,
the typeface pairing, the type scale and the rules that keep the deck from
looking machine-made.

Why a registry instead of loose constants: the first version of this skill had
exactly one look (warm paper + cinnabar) and every deck came out looking the
same. A style has to be *chosen*, which means it has to be enumerable, nameable
and previewable.

Tokens
-----
bg            slide background (light)
bg_deep       panel / banded row / table zebra fill
bg_soft       screenshot mat (the frame around a pasted crop)
ink           primary text on light background
ink_soft      secondary text on light background (captions, citation bars)
accent        primary accent: eyebrow marks, rules, section marks
accent_soft   accent lightened for use on dark backgrounds
accent2       second series (a second path, a second model, a contrast class)
rule          hairline on light background
dark_bg       background of a divider / closing slide
dark_ink      primary text on dark background
dark_ink_soft secondary text on dark background
dark_rule     hairline on dark background
mat_on_dark   screenshot mat used on dark slides (stays light: a crop is paper)

Type
----
serif_cn / sans_cn / serif_en / sans_en / mono_en
title_pt / eyebrow_pt / body_pt / sub_pt / cite_pt / label_pt / cap_pt
rule_pt          hairline weight in points
accent_bar_in    width of the accent bar on a panel, in inches
dark_ratio       how many dark slides per section (2 = divider + close)
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    key: str
    label_en: str
    label_cn: str
    blurb: str
    # surfaces
    bg: str
    bg_deep: str
    bg_soft: str
    # ink
    ink: str
    ink_soft: str
    # accents
    accent: str
    accent_soft: str
    accent2: str
    # rules
    rule: str
    # dark variant
    dark_bg: str
    dark_ink: str
    dark_ink_soft: str
    dark_rule: str
    mat_on_dark: str
    ink_on_mat: str          # text that sits ON the screenshot mat (not on the slide)
    # type
    serif_cn: str
    sans_cn: str
    serif_en: str
    sans_en: str
    mono_en: str
    title_pt: float = 26
    eyebrow_pt: float = 11
    body_pt: float = 14
    sub_pt: float = 15
    cite_pt: float = 11
    label_pt: float = 12
    cap_pt: float = 10.5
    # geometry
    rule_pt: float = 0.75
    accent_bar_in: float = 0.055
    dark_ratio: int = 2
    # notes surfaced to the human when they pick a style
    notes: str = ""

    def fonts(self):
        return {
            "serif_cn": self.serif_cn, "sans_cn": self.sans_cn,
            "serif_en": self.serif_en, "sans_en": self.sans_en,
            "mono_en": self.mono_en,
        }


THEMES = {
    "paper-warm": Theme(
        key="paper-warm",
        label_en="Warm Paper & Cinnabar",
        label_cn="暖纸朱砂",
        blurb="Scholarly editorial. Warm paper, near-black ink, cinnabar and ochre "
              "accents, serif titles. Reads like a printed monograph.",
        bg="F6F4EF", bg_deep="ECE7DD", bg_soft="F1ECE2",
        ink="1A1D23", ink_soft="55606A",
        accent="A63D2B", accent_soft="C98E7E", accent2="8A6D1F",
        rule="CFC8BA",
        dark_bg="1A1D23", dark_ink="E8E3D9", dark_ink_soft="9AA0A8", dark_rule="444A52",
        mat_on_dark="F1ECE2",
        ink_on_mat="1A1D23",
        serif_cn="Songti SC", sans_cn="Heiti SC",
        serif_en="Georgia", sans_en="Helvetica Neue", mono_en="Menlo",
        notes="The default. Safe for a humanities or translation-studies audience. "
              "Screenshots sit on a warm mat, so it forgives a low-contrast crop.",
    ),
    "minimal-white": Theme(
        key="minimal-white",
        label_en="Minimal White",
        label_cn="极简白",
        blurb="Pure white, one signal-blue accent, hairline rules, no panels. "
              "Maximum whitespace; content does all the work.",
        bg="FFFFFF", bg_deep="F2F2F3", bg_soft="F5F5F6",
        ink="0F0F10", ink_soft="595959",
        accent="0057B8", accent_soft="7FA8D0", accent2="8A8A8A",
        rule="E3E3E4",
        dark_bg="0F0F10", dark_ink="F5F5F5", dark_ink_soft="8E8E8E", dark_rule="2A2A2C",
        mat_on_dark="F5F5F6",
        ink_on_mat="0F0F10",
        serif_cn="Songti SC", sans_cn="PingFang SC",
        serif_en="Helvetica Neue", sans_en="Helvetica Neue", mono_en="Menlo",
        title_pt=26, eyebrow_pt=11, body_pt=14, sub_pt=15,
        cite_pt=11, label_pt=12, cap_pt=10.5,
        rule_pt=0.5, accent_bar_in=0.04,
        notes="For a talk where the deck is a backdrop, not a document. Drop "
              "decorative panels entirely; keep only hairlines.",
    ),
    "journal-serif": Theme(
        key="journal-serif",
        label_en="Journal Serif",
        label_cn="学术期刊",
        blurb="Times/Georgia on white with a single dark-red accent. Dense "
              "citation bars, tight leading, zero decoration -- a journal article "
              "that happens to be slides.",
        bg="FFFFFF", bg_deep="F7F5F1", bg_soft="FBF9F5",
        ink="000000", ink_soft="3F3F3F",
        accent="990F0F", accent_soft="B06A6A", accent2="1F3A5F",
        rule="D8D4CC",
        dark_bg="1A1A1A", dark_ink="F2F2F2", dark_ink_soft="9C9C9C", dark_rule="3A3A3A",
        mat_on_dark="FBF9F5",
        ink_on_mat="000000",
        serif_cn="Songti SC", sans_cn="Heiti SC",
        serif_en="Times New Roman", sans_en="Helvetica Neue", mono_en="Courier New",
        title_pt=24, eyebrow_pt=10.5, body_pt=14, sub_pt=14.5,
        cite_pt=11, label_pt=11.5, cap_pt=10.5,
        rule_pt=0.75, accent_bar_in=0.05,
        notes="For a seminar or a methods talk where the audience is reading the "
              "citations. Titles sit lower (24pt) so a long Chinese title still fits.",
    ),
    "slate-dark": Theme(
        key="slate-dark",
        label_en="Slate Dark",
        label_cn="冷灰深色",
        blurb="Deep slate slides, cyan and amber accents, crop mats kept light so "
              "paper still reads as paper. Built for projectors in bright rooms.",
        bg="1E252C", bg_deep="262E36", bg_soft="2A323A",
        ink="E8EDF2", ink_soft="A7B2BC",
        accent="4EA8DE", accent_soft="8CC6EC", accent2="E8A33D",
        rule="39424C",
        dark_bg="141A20", dark_ink="EAF0F5", dark_ink_soft="93A0AB", dark_rule="2E373F",
        mat_on_dark="F2F4F6",
        ink_on_mat="3B4650",
        serif_cn="Songti SC", sans_cn="PingFang SC",
        serif_en="Georgia", sans_en="Helvetica Neue", mono_en="Menlo",
        notes="Screenshots must stay large: a white crop on a dark slide reads as "
              "a lit panel, and a small one turns to mush. Give every crop a light mat.",
    ),
    "blueprint": Theme(
        key="blueprint",
        label_en="Blueprint",
        label_cn="蓝图理性",
        blurb="Cool blue-grey surfaces, navy accent with a copper second series, "
              "monospaced labels. Reads as a technical document.",
        bg="F4F7FA", bg_deep="E6EDF4", bg_soft="EEF3F8",
        ink="0E2233", ink_soft="4A5C6B",
        accent="1B5FA8", accent_soft="7FA9D4", accent2="C2703D",
        rule="C9D6E2",
        dark_bg="0E2233", dark_ink="E8F0F7", dark_ink_soft="94A8B8", dark_rule="24415A",
        mat_on_dark="EEF3F8",
        ink_on_mat="0E2233",
        serif_cn="Songti SC", sans_cn="PingFang SC",
        serif_en="Helvetica Neue", sans_en="Helvetica Neue", mono_en="Menlo",
        notes="Good for a methods or pipeline talk. Mono labels for axes, stages "
              "and IDs; serif only for the title.",
    ),
    "kraft": Theme(
        key="kraft",
        label_en="Kraft Vellum",
        label_cn="牛皮纸",
        blurb="Recycled-kraft surfaces, rust and olive accents, mono labels. "
              "Textured and archival; good for archival or book-history work.",
        bg="E8E0D1", bg_deep="DCD2BE", bg_soft="F0E9DC",
        ink="3A3026", ink_soft="5F5343",
        accent="8C4A2F", accent_soft="C09078", accent2="4A6741",
        rule="C8BCA6",
        dark_bg="2E2820", dark_ink="EDE4D4", dark_ink_soft="A79C89", dark_rule="4A4136",
        mat_on_dark="F0E9DC",
        ink_on_mat="3A3026",
        serif_cn="Songti SC", sans_cn="Heiti SC",
        serif_en="Palatino", sans_en="Avenir Next", mono_en="Courier New",
        notes="Warm, bookish, less clinical than paper-warm. Not for a clinical "
              "or regulatory audience -- the texture reads informal.",
    ),
    "ink-wash": Theme(
        key="ink-wash",
        label_en="Ink Wash",
        label_cn="水墨留白",
        blurb="Near-white ground, ink-black type, a single seal-red accent and a "
              "blue-grey second series. Maximum whitespace, thin rules, quiet.",
        bg="FDFDFB", bg_deep="EFEDE7", bg_soft="F6F4EF",
        ink="1C1C1C", ink_soft="55534E",
        accent="8C1C13", accent_soft="C58F87", accent2="3B4A5A",
        rule="D8D4CC",
        dark_bg="17171A", dark_ink="EDECE8", dark_ink_soft="8D8C87", dark_rule="2E2E30",
        mat_on_dark="F6F4EF",
        ink_on_mat="1C1C1C",
        serif_cn="Songti SC", sans_cn="PingFang SC",
        serif_en="Georgia", sans_en="Helvetica Neue", mono_en="Menlo",
        notes="The quietest option. Works for close reading and close analysis, "
              "where a busy slide would fight the text.",
    ),
}

DEFAULT_THEME = "paper-warm"


def get(key):
    """Return a theme by key. Raises with the list of valid keys -- never a
    silent fallback, because a silent fallback means the deck ships in a style
    the human did not choose."""
    if key not in THEMES:
        raise KeyError(f"unknown theme {key!r}; choose one of: "
                       + ", ".join(sorted(THEMES)))
    return THEMES[key]


def keys():
    return sorted(THEMES)


def describe():
    """Human-readable catalogue used by the intake step."""
    out = []
    for k in keys():
        t = THEMES[k]
        out.append(f"{k:16} {t.label_en} / {t.label_cn}\n"
                   f"{'':16} {t.blurb}")
    return "\n".join(out)


# ----------------------------------------------------------------- contrast
def _srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.2126 * _srgb_to_lin(r) + 0.7152 * _srgb_to_lin(g)
            + 0.0722 * _srgb_to_lin(b))


def contrast_ratio(fg, bg):
    """WCAG contrast ratio between two hex colours."""
    l1, l2 = luminance(fg), luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def audit(min_body=4.5, min_secondary=4.5):
    """Contrast audit for every theme. Returns (rows, failures).

    Thresholds follow WCAG AA for normal text. The body floor of 4.5:1 is the
    one that matters: a projector eats contrast, and secondary text (captions,
    citation bars) is the first thing to disappear.
    """
    rows, fails = [], []
    for k in keys():
        t = THEMES[k]
        checks = [
            ("ink on bg", t.ink, t.bg, min_body),
            ("ink_soft on bg", t.ink_soft, t.bg, min_secondary),
            ("accent on bg", t.accent, t.bg, 3.0),
            ("ink on bg_deep", t.ink, t.bg_deep, min_body),
            ("ink_soft on bg_deep", t.ink_soft, t.bg_deep, min_secondary),
            ("dark_ink on dark_bg", t.dark_ink, t.dark_bg, min_body),
            ("dark_ink_soft on dark_bg", t.dark_ink_soft, t.dark_bg, min_secondary),
            ("accent_soft on dark_bg", t.accent_soft, t.dark_bg, 3.0),
            ("ink_on_mat on mat_on_dark", t.ink_on_mat, t.mat_on_dark, min_body),
            ("mat vs slide bg", t.mat_on_dark, t.dark_bg, 1.25),
        ]
        for name, fg, bg, need in checks:
            r = contrast_ratio(fg, bg)
            ok = r >= need
            rows.append((t.key, name, fg, bg, round(r, 2), need, ok))
            if not ok:
                fails.append(rows[-1])
    return rows, fails


if __name__ == "__main__":
    rows, fails = audit()
    print(f"{'theme':16} {'pair':26} {'ratio':>6} {'need':>5}  ok")
    for k, name, fg, bg, r, need, ok in rows:
        print(f"{k:16} {name:26} {r:6.2f} {need:5.1f}  {'PASS' if ok else 'FAIL'}")
    print()
    print(f"{len(rows) - len(fails)}/{len(rows)} contrast pairs pass")
    raise SystemExit(1 if fails else 0)
