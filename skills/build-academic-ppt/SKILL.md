---
name: build-academic-ppt
description: Build or revise academic presentation decks from papers, monographs, reports and scanned sources — every claim traceable to a highlighted passage in the real source, with full bibliographic citations, real screenshots, and a visual style chosen deliberately from seven tested styles. Use when asked to turn 论文/文献/报告/书 into a PPT or 幻灯片/演示文稿/导读, to 讲解/综述/评议 a body of academic writing, to add 截图/原文截图/高亮 to a deck, to size deck text (e.g. 正文至少14pt), to pick or change a deck's visual style, to fix an existing academic deck whose screenshots do not match its claims, or to edit a deck the user has already hand-edited — work from their latest saved file, never regenerate over it.
---

# Build academic decks

Turn academic source documents into a slide deck where **every claim is
traceable to a highlighted passage in the actual source**. The screenshots are
evidence, not decoration.

## Gate 0 — the brief comes first

**Do not write a single line of deck code until the brief is complete.** A deck
built on a guessed research question is not a deliverable, it is a guess with a
file extension.

The order matters: **read the sources first, then ask.** Anything the sources
already answer does not need a question — it needs a confirmation.

```bash
python3 scripts/brief.py derive            # read the sources, fill what they answer
python3 scripts/brief.py questions         # print the questionnaire for this round
python3 scripts/brief.py record --key title --value "..." --source given
python3 scripts/brief.py status            # what is still missing
python3 scripts/brief.py check             # GATE: exit 0 only when complete
```

Four fields are **required**: `title` (主题), `key_points` (核心要点),
`research_question` (研究问题), `sources` (源材料). The rest — `style`,
`length`, `audience`, `occasion`, `language`, `citation_style` — have
documented defaults.

**Ask about a derived field as a confirmation, not as an open question.** If
the source states the research question, put it back to the human as "材料里的
研究问题是「……」，对吗？" — one click, and the deck cannot end up answering a
question the human did not intend.

### The two-round rule

| Round | What you do |
|---|---|
| 1 | Ask every unanswered question, **in one batch**. Wait for the answer. |
| 2 | Ask **again** — only what is still unanswered, and only if round 1 was missing, empty or unusable. |
| 3+ | The human has had two chances. Derive the rest from the sources and mark it `default`. List every assumption in the delivery. |

Never skip round 1 because the request looks obvious. Never invent a research
question: it is either **given**, **stated in the source** (derive it and mark
`derived`), or **assumed** (only after two rounds, and only from evidence).

`brief.py defaults` refuses to run before round 2 — that refusal is the
mechanism, not an obstacle.

Full protocol, including how to judge whether a stated question is really the
research question: `references/intake.md`.

## Mode A or Mode B — pick before writing any code

**A. New deck.** Nothing exists yet. Build with `scripts/deck_kit.py`.

**B. Edit an existing deck.** The user has a file. **Always mode B when a
deck already exists**, even if you wrote the generator that made it.

> A regeneration script silently destroys hand edits. Before running anything in
> mode B: `ls -laT` the target and compare **time and size** against your last
> write. If it changed, the user edited it — that file is the only valid
> baseline. `cp` a timestamped backup first. Edit with `deck_kit.swap_pic` /
> `deck_kit.replace_text` on the live file. Never re-run the generator.

## Choose the visual style deliberately

Seven styles ship with the skill, each a complete system (surfaces, two
accents, type pairing, type scale, rules) — not a colour swap:

| key | name | reads as |
|---|---|---|
| `paper-warm` | 暖纸朱砂 / Warm Paper & Cinnabar | a printed monograph |
| `minimal-white` | 极简白 / Minimal White | content-only, maximum whitespace |
| `journal-serif` | 学术期刊 / Journal Serif | a journal article that happens to be slides |
| `slate-dark` | 冷灰深色 / Slate Dark | a talk in a bright room |
| `blueprint` | 蓝图理性 / Blueprint | a technical document |
| `kraft` | 牛皮纸 / Kraft Vellum | archival, bookish |
| `ink-wash` | 水墨留白 / Ink Wash | close reading, quiet |

**Show the previews when you ask.** `assets/previews/*.jpg` (and
`assets/previews/all-styles.jpg` for the contact sheet). Ask in the user's
language; if they describe a look ("简洁", "白底", "像论文") rather than naming a
style, map it yourself and say which style you picked — see
`references/styles.md`.

If the human declines to choose after two rounds: take `paper-warm` unless they
described a look that maps elsewhere, and state the choice.

## Workflow

1. **Inventory sources.** `pdfinfo` + `pdftotext` every PDF. A text layer is
   required for precise crops; scanned pages need `scripts/ocr_shots.py` and a
   different approach.
2. **Read the sources properly.** Extract text, build a per-page map
   (`pdftotext -layout` split on `\f`). You cannot choose highlights you have
   not read.
3. **Outline.** Decide the spine before any rendering. Group by argument or
   theme, not one-slide-per-paper unless the corpus is genuinely one-paper-each.
   **Default to about 20 slides.** More content means merging, not padding.
4. **Locate the passage each slide will claim.** For every slide, name the exact
   sentence that supports it, and confirm it exists (`pdf_shots.py probe`).
   **If you cannot point to a supporting passage, the slide is not
   evidence-based — cut it or rewrite the claim.**
5. **Generate screenshots** with `scripts/pdf_shots.py` (see below).
6. **Build the deck** with `scripts/deck_kit.py`.
7. **QA loop** — mandatory, and it is a loop, not a step. See
   `references/qa-protocol.md`.

## Non-negotiable content rules

- **Full bibliographic citation on every content slide** — authors, year, full
  title, journal/publisher, volume/issue, DOI. Not a short tag.
- **A screenshot on every content slide**, captioned with the source page
  number. Cover, dividers and closing are exempt.
- **The highlight must be the passage that supports the slide's claim.** A crop
  of the right paper's *conclusion* under a slide about its *method* is wrong
  even though it looks fine. Audit every screenshot against its slide text.
- **Body text ≥ 14pt.** Captions, labels and footers may go lower; body prose
  may not. If the content does not fit at 14pt, the fix is **more slides**,
  never smaller type.
- **English concepts get a Chinese gloss**: `主成分分析（PCA）`,
  `功能性近红外光谱（fNIRS）`, `风格多元宇宙（stylistic multiverse）`. Do this
  for concepts the audience may not know, not for proper nouns (Paivio,
  Culpeper).
- **Emphasis is bold.** Use `**bold**` for anything that must stand out. Do
  not use 「」 or "" as an emphasis device.
- **No vague quantity summaries.** "两套模型" tells the reader nothing. Write
  "两套模型（Kloss & Schmidt 的可读性模型、Barnstone 的翻译单位模型）" —
  the specific content, in parentheses.
- **Use the source's own wording** wherever a passage carries the argument.
  Quote it rather than paraphrasing it into your own words.
- **Never assert a quotation you cannot locate in the source.** If a quote on a
  slide is not in the PDF you hold, flag it to the user — do not silently keep it.

## Screenshots — `scripts/pdf_shots.py`

```bash
# which pages contain a phrase
python3 pdf_shots.py probe paper.pdf "functional asymmetry" "dual code"

# crop + highlight; jobs.json: [{name,page,needles,ctx,pad,occ?,col?,x0?,x1?}]
python3 pdf_shots.py shots paper.pdf jobs.json outdir/
```

It handles the traps that make naive crops unusable:

- `fitz.Rect.__and__` returns an **empty but truthy** Rect — test `.is_empty`.
- CJK PDFs report a whole paragraph as one "line" — spans are re-clustered by
  vertical centre.
- Two-column articles bleed the far column into the crop — clustering is
  column-aware and crop edges anchor to the highlighted column.
- Vertical journal mastheads, running heads, and half-cut lines at the crop edge.
- **A phrase that appears several times** — the old build silently took the
  first (the abstract, not the passage you meant). Now every ambiguity is
  reported; pick with `occ` (occurrence index) or `col` (`left` / `right`).
- **A highlight that lands outside the crop** — the crop is produced without
  any highlight, and nothing complains. Now the crop is rejected, and the
  output is checked for amber pixels before it is written.

The run also writes `manifest.json` next to the images, carrying the page
number of every crop. **Read page numbers from the manifest** — never hardcode
`P52` in the build script; changing the source's font reflows the pages.

For a passage you cannot isolate automatically, measure the page and pass
explicit `x0`/`x1` (that path still clusters per column):

```bash
python3 -c "
import fitz; d=fitz.open('p.pdf'); p=d[11]
print([(round(b[0],1),round(b[2],1),round(b[1],1),' '.join(b[4].split())[:30])
       for b in sorted(p.get_text('blocks'), key=lambda b:b[0])])"
```

**Always look at the rendered crop** before using it. A crop can be technically
correct and still useless — 80% reference list, or the right sentence in a crop
dominated by bibliography.

Scanned sources (no text layer): `scripts/ocr_shots.py` — see
`references/qa-protocol.md`.

## Deck construction — `scripts/deck_kit.py`

```python
import sys
sys.path.insert(0, "/path/to/skills/build-academic-ppt/scripts")
from deck_kit import Deck, txt, shot, fits, theme, ML, CW
from pptx.util import Inches

d = Deck(theme_key="paper-warm", footer="功能性与翻译研究 · 文献评议")
s, y = d.content(eyebrow="证据结构", title="三个证据层级",
                 cite="Li, D., Wu, K. (2025). Title. Publisher. DOI 10.xxxx/yyyy.")
txt(s, ML, y, CW // 2, Inches(1.4),
    [[("研究问题", {"bold": True, "color": theme().accent})],
     [("译文在哪些可指认的语言层级与原文发生偏移？", {})]], size=14, line=1.25)
shot(s, "_shots/x.png", ML + CW // 2, y, CW // 2, Inches(2.1),
     caption="原文 P52：textual panorama 的界定（高亮处）", valign="top")
d.save("deck.pptx")
```

`deck_kit` exports `ML`, `MR`, `CW`, `SLIDE_W`, `SLIDE_H`, `IN()` and `E()`
for geometry. Import them rather than hardcoding numbers.

Call `fits(tag, paras, width_in, box_h_in, …)` before each `txt()` that goes
into a bounded region. `d.save(path)` prints every predicted overflow **and**
runs a geometry check (text over a screenshot, text escaping its frame, text
over text, content past the margin, content slide without a screenshot or a
citation).

### The defects that geometry checks exist for

**Text boxes do not clip.** A box sized for one line lets the wrapped line 2
escape and overprint whatever sits below it. Each box is *individually* in
bounds, so a per-box geometry check passes while the slide is unreadable.

**A run without `lang` does not wrap Chinese.** python-pptx writes runs with no
`lang` attribute, so a Chinese paragraph with no spaces is laid out as one
unbreakable word and runs off the right edge. `deck_kit` writes
`lang="zh-CN"` / `altLang="en-US"` on every run. If you see Chinese text
overrunning a box, check `lang` before narrowing anything.

**Units.** `est_height()` returns **inches**; `Inches()` / `IN()` return
**EMU**. `txt()` refuses a float where EMU is required — that guard exists
because a table cell given `3.5` instead of `Inches(3.5)` becomes a
zero-width box, one character per line, the whole table stacked on itself.
Use `E(...)` for computed EMU values.

## Before shipping

- [ ] `python3 scripts/brief.py check` passed; assumptions listed in the delivery.
- [ ] Every content slide has a full citation + a screenshot.
- [ ] Every screenshot's highlight supports **that slide's** claim.
- [ ] Body text ≥ 14pt.
- [ ] English concepts glossed; emphasis is bold; no vague quantity summaries.
- [ ] `python3 scripts/qa_deck.py deck.pptx` clean.
- [ ] A **fresh-eyes** visual review of the rendered JPEGs — a subagent that has
      not written the deck. Assume it will find something; a clean first pass
      means nobody looked hard enough.
- [ ] User's own edits preserved (mode B): diff against the backup.

## References

- `references/intake.md` — the intake protocol: what to ask, how to judge a
  research question, how to derive one from a source, what to do after two
  unanswered rounds.
- `references/styles.md` — the seven styles, when each one fits, and how to map
  a described look onto a style.
- `references/authoring-rules.md` — content rules with worked examples:
  citations, screenshots, emphasis, glosses, length, wording.
- `references/design-system.md` — layout recipes, anti-patterns, contrast.
- `references/qa-protocol.md` — the QA loop, the defect catalogue, and how to
  brief a visual reviewer.
