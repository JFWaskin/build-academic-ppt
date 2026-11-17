# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-11-17

First public release. The skill began as a private toolkit used to build
evidence-based academic decks; this release adds the pieces that were missing
from the toolkit and hardened the pieces that were there.

### Added

- **An intake gate.** `scripts/brief.py` makes the build refuse to start
  until a brief exists. Required: `title`, `key_points`, `research_question`,
  `sources`. Optional with documented defaults: `style`, `length`, `audience`,
  `occasion`, `language`, `citation_style`.
  - A two-round protocol: round 1 asks everything in one batch, round 2 asks
    again what is still open, and after that the agent derives the rest from
    the sources and records it as an assumption.
  - `brief.py defaults` refuses to assume anything before the second round.
  - `brief.py derive` extracts a title, key points and an explicitly stated
    research question from PDF and DOCX sources.
  - `brief.py summary` prints the brief with an **Assumptions** section, so
    every derived or defaulted field can be stated in the delivery.
- **Seven visual styles** in `scripts/themes.py`: `paper-warm`,
  `minimal-white`, `journal-serif`, `slate-dark`, `blueprint`, `kraft`,
  `ink-wash`. Each carries a complete token set (surfaces, two accents,
  hairline, dark-slide variant, mat, type pairing, type scale) rather than a
  colour swap.
  - `python3 scripts/themes.py` audits every style against WCAG AA and exits
    non-zero on a failure.
  - `scripts/style_previews.py` renders one sample slide per style and a
    contact sheet, so "which style?" can be answered by looking.
- **`scripts/selftest.py`** — 20 checks covering the theme registry and its
  contrast audit, the theme switch, the `lang` attribute on every run, the
  unit guards, the geometry check, the stat row, the brief gate,
  research-question derivation, crop highlighting and ambiguity, and the QA
  gate against both a clean and a broken deck.
- **`scripts/ocr_shots.py`** — the scanned-source path: tesseract TSV, words
  clustered into visual lines, normalised fuzzy matching, a crop taken over
  the text column's x-range, and an amber highlight verified before the image
  is written.
- **A per-slide manifest.** `Deck.save()` writes `<deck>.manifest.json` with
  each slide's kind, citation and screenshot count, so `qa_deck.py` can tell a
  content slide (which owes a citation and a screenshot) from a divider.

### Fixed

- **Chinese did not wrap.** python-pptx writes runs with no `lang` attribute,
  so a Chinese paragraph with no spaces was laid out as one unbreakable word
  and ran off the right edge. `deck_kit.txt()` now writes `lang="zh-CN"` and
  `altLang="en-US"` on every run. This one root cause explained three
  unrelated-looking defects: text overrunning the margin, text sitting on top
  of a screenshot, and Chinese quotation marks rendering as corner brackets.
- **A theme switch changed nothing.** Colours and typefaces were bound as
  default arguments, which capture their value at definition time. They now
  resolve from the active theme at call time.
- **Inch/EMU confusion.** `est_height()` returns inches; `Inches()` returns
  EMU. `txt()` now refuses a float where EMU is required, which is the
  zero-width table cell, one-character-per-line, whole-table-stacked bug.
  `E(...)` casts a computed EMU value.
- **`est_height()` under-reported.** A paragraph given as a bare string was
  read as its first character, so the estimate came out about five times too
  small. It now raises. `width_factor` handles Latin text being set wider
  than the estimate assumes, and the citation bar measures at 0.85.
- **The highlight could vanish.** `search_for()` finds a phrase anywhere on
  the page; if that occurrence fell outside the crop, the crop was still
  produced — with no highlight. Every crop is now verified for amber pixels
  and refused otherwise.
- **The wrong occurrence was highlighted.** A phrase appearing several times
  silently resolved to the first one. Ambiguity is now reported, and `occ` /
  `col` select the intended occurrence.
- **The QA gate had blind spots.** `qa_deck.py` v1 could not see text over a
  screenshot, text escaping its frame, a missing citation, or a crop with no
  highlight. It also flagged every text block sitting exactly on the right
  margin (hardcoded 898pt threshold), and reported 10.5pt captions as being
  under the floor because python-pptx truncates 10.5 to 10. The size now
  comes from the XML, and the margin allows 14pt of Chinese hanging
  punctuation.
- **The footer was hardcoded** to one project's wording. `Deck(footer=...)`
  now carries it.
- **A row of big numbers could wrap.** Each tile now shares one font size,
  the largest at which no value wraps.

### Changed

- The default length is about **20 slides**; more material means merging, not
  padding.
- Emphasis is **bold**. Brackets are not used as an emphasis device.
- Vague quantity summaries are replaced by the specific content, named in
  parentheses.

[1.0.0]: https://github.com/JFWaskin/build-academic-ppt/releases/tag/v1.0.0
