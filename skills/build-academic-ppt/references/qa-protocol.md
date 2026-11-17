# QA protocol

Assume the deck has defects. Your own build is the least reliable view of it —
you see the intent, not the pixels. Budget for at least **two full cycles**.

## The loop

```
build → fit report → geometry check → render → mechanical check → fresh-eyes
      → fix → re-render → re-check affected slides only
```

Do not stop at the first clean pass. On a 20-slide deck, a single round of
visual review typically surfaces 3–8 real defects; two rounds is the norm.

## 1. Fit report + geometry check (build time)

`Deck.save()` prints `OVERFLOW tag needs X" vs box Y"` for every text block
predicted not to fit, then runs the geometry check and prints
`CHECK slide N kind detail`.

The geometry check catches what a per-box bounds check cannot:

| check | what it catches |
|---|---|
| `text-over-image` | text printed on top of a screenshot (pictures are topmost) |
| `text-overflows-frame` | text taller than its own box — boxes do not clip |
| `text-over-text` | two text frames intersecting |
| `past-right-margin` | content past the margin |
| `below-content-band` | content below 6.95in |
| `content-slide-without-screenshot` | the rule every content slide owes |
| `content-slide-without-citation` | the other rule every content slide owes |

Fix these before rendering — they are the cheapest defects to fix and the most
disruptive when missed.

## 2. Render

```bash
soffice --headless --convert-to pdf --outdir /tmp/qa deck.pptx
pdftoppm -jpeg -r 110 /tmp/qa/deck.pdf /tmp/qa/s
```

LibreOffice's line breaking differs from PowerPoint's. If the user will present
from PowerPoint, spot-check the tightest slides there too.

## 3. Mechanical check

```bash
python3 scripts/qa_deck.py deck.pptx
python3 scripts/qa_deck.py deck.pptx --keep        # keep the JPEGs
python3 scripts/qa_deck.py deck.pptx --require-highlight
```

It flags: content in the footer band, text outside the right margin,
intersecting text pairs, text over a screenshot, text escaping its frame, type
below the floor, placeholder leftovers, slides missing a screenshot, content
slides missing a citation, and (with `--require-highlight`) crops whose
highlight has vanished.

Two of its thresholds are deliberate and should not be "fixed":

- **The right margin allows 14pt of overflow.** Chinese hanging punctuation
  puts a full stop past the margin by design. Use `--strict-margin` when you
  want the hard edge.
- **The type floor reads `sz` from the XML.** python-pptx's `font.size.pt`
  truncates 10.5 to 10 (integer division), which turns every 10.5pt caption
  into a false positive.

## 4. Fresh-eyes visual review

Give a subagent the JPEGs and a defect list to hunt for. It must not know what
you intended — that is the whole point.

Ask it to check, and to report severity (CRITICAL / MEDIUM / MINOR):

- text overprinting other text
- text overlapping a screenshot, its caption, or a card border
- a fixed-height box letting a wrapped line escape onto content below
- a citation bar's second line colliding with the lead line or a heading
- screenshots whose highlighted passage does not support that slide's claim
- crops dominated by reference lists, headers or unrelated content
- cramped gaps (<0.2in), misaligned columns, a thin rule running through text
- low-contrast or too-small text

Tell it explicitly: a crop ending mid-line at the frame edge is **not** a
defect, and screenshots of a journal's own layout (green author highlighting,
vertical mastheads) are authentic, not errors.

Expect to iterate. Verify each reported fix by re-rendering *that slide* — a
fix frequently creates a new overflow one element down.

## Scanned sources (no text layer)

`pdf_shots.py` relies on the text layer. When a PDF has none, use
`scripts/ocr_shots.py`. It OCRs the page and crops the rendered image:

```bash
python3 scripts/ocr_shots.py probe book.pdf 52 "占全书比例超出"
python3 scripts/ocr_shots.py shots book.pdf jobs.json outdir/
```

**The default backend is macOS Vision**, and it should stay the default: on a
Chinese scan, tesseract's `chi_sim` returns garbled text, while Vision reads
it correctly. Vision is also about five times faster warm (0.7 s vs 3.5 s per
page). Its **first** call takes around 25 s while the language model
initialises — that is not a hang. Use `--backend tesseract` on a machine
without pyobjc, or for a language Vision has no pack for.

Two rules that survive any backend:

1. **The renderer must match the corpus renderer.** If you build the OCR
   corpus with `pdftoppm` and crop with PyMuPDF, the two produce different
   text for the same page and the needle will appear to be missing. Use
   PyMuPDF for both.
2. **Use short, distinctive needles.** OCR splits long phrases, so a whole
   sentence often will not match.

The pipeline, in order: OCR the page → cluster the words into visual lines
(tesseract: by block/par/line, then merged by vertical centre, because OCR
splits one printed line into fragments) → match the needle against those
lines with a normalised fuzzy match → crop over the matched line's x-range
but take the **text column's** x-range, so a neighbouring line is not sliced
in half at the frame edge → draw the amber highlight → verify amber pixels
are actually present before the image is written.

## Defect catalogue

| Symptom | Cause | Fix |
|---|---|---|
| Wrapped line overprints the block below | Text box does not clip; box sized for fewer lines than the text wraps to | `fits()` at build time; reserve height for the real line count |
| One systemic collision on ~20 slides | A shared component (citation bar) sized for 1 line while it wraps to 2 | Fix the component, not each slide |
| Chinese runs off the right edge | Run has no `lang` attribute → laid out as one unbreakable en-US word | `deck_kit.txt()` writes `lang="zh-CN"`; check it before narrowing boxes |
| Latin rendered `GARCIA ET AL.` mid-sentence | `cap="all"` applied to every run | Remove it; letterspace eyebrows only |
| Citation bar hidden behind a screenshot | Both full-width, drawn in z-order | Narrow the bar or move the image |
| Label wraps mid-word (`NEURA`/`L`) | Label textbox too narrow | Widen the box |
| Whole-page crop from one highlighted phrase | `Rect.__and__` truthiness — every line "matched" | Test `.is_empty` |
| Crop with no highlight at all | The needle's occurrence lies outside the crop rectangle | The crop is now rejected; widen `ctx`/`pad` or pass explicit `x0`/`x1` |
| Crop highlights the wrong occurrence | The phrase appears several times on the page | Pass `occ` (index) or `col` (`left`/`right`) |
| Crop 80% reference list | Column bleed / too much context | Column-aware crop; explicit `x0`/`x1`; `ctx: 1` |
| Screenshot shrinks to a grey smudge | Aspect ratio badly matched to a small box | Give it a proper slot; regenerate at a tighter crop |
| Table collapses into one character per line | A cell width given in inches (float) instead of EMU | `Inches(...)` / `IN(...)`; `txt()` now rejects floats |
| A number wraps and lands on its label | Each tile chose its own font size | `stat_row()` — one shared size for the whole row |
| Elements stack on top of each other | A container helper returned a *height* instead of the bottom y | Return the bottom y |
| Cited quote not in the source | Fabricated or misremembered | Locate it or flag to the user |
| Regenerator wiped the user's edits | Ran the old build script | Diff mtime **and size** first; back up; edit the live file |

## Briefing the user

State what you changed and what you deliberately left alone. Flag anything you
could not verify — an unattributable quotation, a half-typed note, a figure
whose aspect does not fit. Never silently "fix" a phrase you do not understand;
ask what was meant.
