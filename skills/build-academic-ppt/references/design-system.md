# Design system

Layout rules that hold across all seven styles. Colours, type sizes and fonts
come from `scripts/themes.py` — read the values there, not here, so the
registry stays the single source of truth.

## Geometry

16:9, 13.333 × 7.5in. Margins 0.85in. Footer baseline 7.04in — keep content
above **6.95in**.

```
ML = MR = 0.85in          CW = 11.633in (content width)
FOOTER_Y   = 7.04in       CONTENT_BOTTOM = 6.95in
```

## Layout recipes

**Standard content** — eyebrow, title, hairline, 2-line citation bar, optional
italic lead, then content. `Deck.content()` returns the y content starts; do
not hardcode it, because the citation bar wraps to a variable number of lines.

**Screenshot-left** — crop ~6.1in wide, text right. `valign="top"` so a short
crop does not float with a hole under it.

**Screenshot-band** — full-width strip, ideal for aspect ratios > 3:1 (a
three-line journal crop). Cap the height so a tall crop cannot push the
caption into the footer.

**Two-column** — crop top-left, short summary below it, critique column right,
separated by a 0.012in vertical rule. Give the columns a real gutter (~0.4in)
and keep the rule clear of both text boxes.

**Cards / panels** — flat rectangles, the theme's `bg_deep` fill, a 0.055in
accent bar on the left edge. Never rounded corners, never shadows. `panel()`
does this.

**Stat rows** — a row of big numbers with labels under them. **Every value in
the row shares one font size**, chosen as the largest size at which no value
wraps. `stat_row()` computes it. A row where each tile picks its own size is
a row where `≈48,700` wraps to `48,7 / 00` and the second line lands on the
label.

## Type

| Role | Size |
|---|---|
| Slide title | 24–26pt (per style) |
| Section eyebrow | 10.5–11pt, letterspaced (`spc`), uppercase |
| Lead / subhead | 14.5–15pt italic |
| **Body** | **14pt floor** |
| Label | 11.5–12pt |
| Citation bar | 11pt |
| Caption | 10.5pt |
| Footer | 9pt |

Serif for titles and citations, sans for body. Line spacing 1.15–1.25 for
body; 1.24 for citations; tight 1.0 for single-line labels.

**Never set `cap="all"` globally.** It turns `García et al.` into `GARCIA ET
AL.` mid-sentence. Apply letter-spacing to eyebrows only.

**Never leave out `lang`.** A run with no `lang` attribute is laid out as
en-US: a Chinese paragraph with no spaces becomes one unbreakable word and
overruns the box, and Chinese quotation marks render as corner brackets.
`deck_kit.txt()` writes `lang="zh-CN"` / `altLang="en-US"` on every run.

## Screenshots

- Thin hairline frame with the theme's mat fill, 0.045in outside the image.
- Fit to the box preserving aspect; never stretch.
- Caption below, 10.5pt, secondary ink: `原文 P<page>：<what to look at>（高亮处）`.
- The caption tells the reader what the highlight *proves*, not where it is.
- A crop that ends mid-sentence at the frame edge is normal and fine — it reads
  as a genuine screenshot. A crop that is 80% reference list is not.

## Anti-patterns — these read as machine-generated

- Gradients, glassmorphism, drop shadows, rounded 12px+ card stacks
- Icon-in-coloured-circle next to every heading
- Emoji anywhere
- A coloured underline or rule directly beneath the title
- A centred body paragraph (centre titles only)
- Uniform 4-column "feature grid" applied to content that is not a feature list
- Three coloured panels of identical width carrying prose
- A decorative element that encodes nothing

## Contrast

Captions and citation bars are the most likely thing to become unreadable on
a washed-out projector. Keep secondary text at the theme's `ink_soft`
(~5.2–7.2:1), not light grey (~3.4:1).

`python3 scripts/themes.py` audits every theme against WCAG AA and exits
non-zero on a failure. Run it after touching a palette. It checks: ink on bg,
secondary ink on bg and on panels, accent on bg, the dark-slide set, and the
screenshot mat — including that the mat stays visibly distinct from the slide
background and that text on the mat is legible (a light crop on a dark slide
needs a *dark* ink on the mat, not the slide's light ink).

## House style

If the human has an existing deck whose look you should match, read its
tokens off the file rather than inventing a new style: sample the background
fill, the title font and size, and the accent from a rendered slide, then add
that as a theme in `themes.py` and run the contrast audit on it.
