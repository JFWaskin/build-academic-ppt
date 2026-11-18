# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] — 2026-11-18

### Fixed

- **The version check compared the wrong thing.** It compared the sha256 of
  `SKILL.md`, so a release that changed only the scripts read as "current"
  while the behaviour on disk was old. It now compares a hash over the WHOLE
  package (every file, sorted by path, path included in the identity), and
  both sides of the comparison are computed the same way.
- **The remote side was fetched as two files** while the local side was the
  whole package, so the two hashes were never comparable. The remote package
  is now taken as a whole: one tarball, or -- the China-friendly route -- file
  by file from jsDelivr's data API.
- **The auto-upgrade script treated a successful upgrade as a failure**,
  because `version_check.py --upgrade` returns 1 to mean "an upgrade was
  applied". The verification step never ran.

## [1.1.0] — 2026-11-18

### Added

- **`scripts/version_check.py`** — reports, per harness, whether the installed
  copy is current. It compares two axes: the `VERSION` file and the sha256 of
  `SKILL.md`, which is what actually decides behaviour. A skill installed by
  copying files is tracked by no package manager, so nothing else would tell
  you that `~/.claude/skills` is three revisions behind — and the failure is
  quiet: the deck still builds, it just uses the old rules.
- **`scripts/auto_upgrade.sh`** — check, upgrade, verify, and (if the new
  copy fails the self-test) roll back. The order matters: a copy that fails
  the self-test never survives.
- **`VERSION` inside the skill package**, and an `INSTALL.json` stamp written
  by the installer (version, commit, install time, which route served it).

### Fixed

- **The download could serve a stale package.** A branch URL
  (`refs/heads/main`) is served from a CDN cache that lags a push by minutes —
  measured: both codeload and jsDelivr served the previous tarball minutes
  after the push, and a version check reading a cached file would have
  reported "current" when a new version existed. The installer and the version
  check now **resolve the commit first and fetch pinned to it**; a commit sha
  is immutable, so it cannot be stale. Branch URLs remain as a fallback, with
  a cache-busting query.

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
- **`scripts/ocr_shots.py`** — the scanned-source path. The default backend is
  **macOS Vision**, because on a Chinese scan tesseract's `chi_sim` returns
  garbled text while Vision reads it correctly, and Vision is about five
  times faster warm (0.7 s vs 3.5 s per page). Tesseract remains the
  fallback for machines without pyobjc (`--backend tesseract`).
- **A per-slide manifest.** `Deck.save()` writes `<deck>.manifest.json` with
  each slide's kind, citation and screenshot count, so `qa_deck.py` can tell a
  content slide (which owes a citation and a screenshot) from a divider.
- **A plugin icon and a marketplace manifest**, so the repository installs
  with one line: `/plugin install build-academic-ppt --marketplace
  JFWaskin/build-academic-ppt`.

### Fixed

- **The OCR path died on a real Chinese scan.** Three separate causes, each
  of which surfaced as an unrelated `UnicodeDecodeError`: tesseract writes
  progress to stderr in a local encoding that is not valid UTF-8; leptonica
  cannot open a file through a symlinked directory such as `/tmp` (which
  points at `/private/tmp`) when handed the symlinked absolute path; and
  `PIL.Image.tobytes()` returns raw pixels rather than an encoded image, so
  Vision was handed a zero-dimensioned image. All three are fixed, and an
  empty result with a message on stderr now reports the message instead of
  returning silence.
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
- **`pdf_shots.py` was slow on image-heavy documents.** It read the page with
  `get_text("dict")`, which does a per-character layout analysis and is up to
  two orders of magnitude slower than `get_text("words")` on a document with
  full-page images. It now uses the fast mode and clusters the words on their
  vertical centre, with the column taken from the block number.
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
