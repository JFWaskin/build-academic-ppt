# build-academic-ppt

Build or revise an **academic presentation deck** from papers, monographs,
reports and scanned sources, where every claim is traceable to a highlighted
passage in the actual source. The screenshots are evidence, not decoration.

This repository is a **portable skill**, not a Claude Code plugin. The skill
itself is one directory:

```
skills/build-academic-ppt/
├── SKILL.md              the instructions the agent reads
├── references/           intake, styles, authoring rules, design system, QA
├── scripts/              python-pptx / PyMuPDF / OCR toolkit
└── assets/previews/      one sample slide per visual style
```

Everything it needs is in that directory: **no Claude-specific tooling, no
network calls at build time, no API keys**. The scripts are plain Python
(`python-pptx`, `PyMuPDF`, `Pillow`, `lxml`) plus the usual command-line
tools for rendering.

---

## Gate 0 — the brief comes first

**Do not write a line of deck code until the brief is complete.** A deck built
on a guessed research question is a guess with a file extension.

```bash
cd skills/build-academic-ppt/scripts
python3 brief.py derive       # read the sources, fill what they answer
python3 brief.py questions    # print the questionnaire for this round
python3 brief.py record --key title --value "..." --source given
python3 brief.py status
python3 brief.py check        # GATE: exit 0 only when complete
```

Required: `title` (主题), `key_points` (核心要点), `research_question`
(研究问题), `sources`. The rest have documented defaults.

**Ask, then derive.** Round 1 asks everything unanswered in one batch. Round 2
asks again what is still open. After two rounds the agent derives the rest
from the sources and lists every assumption in the delivery. `brief.py
defaults` refuses to assume before the second round — that refusal is the
mechanism.

If the source already states the research question, derive it and put it back
as a **confirmation** ("材料里的研究问题是「……」，对吗？"), not as an open
question.

## Visual styles

Seven complete styles — surfaces, two accents, hairline, dark variant, type
pairing, type scale — not colour swaps:

| key | name | reads as |
|---|---|---|
| `paper-warm` | 暖纸朱砂 / Warm Paper & Cinnabar | a printed monograph |
| `minimal-white` | 极简白 / Minimal White | content-only, maximum whitespace |
| `journal-serif` | 学术期刊 / Journal Serif | a journal article that happens to be slides |
| `slate-dark` | 冷灰深色 / Slate Dark | a talk in a bright room |
| `blueprint` | 蓝图理性 / Blueprint | a technical document |
| `kraft` | 牛皮纸 / Kraft Vellum | archival, bookish |
| `ink-wash` | 水墨留白 / Ink Wash | close reading, quiet |

Show `assets/previews/*.jpg` when asking. `python3 scripts/themes.py` audits
every style against WCAG AA.

## Non-negotiable content rules

- **Full bibliographic citation on every content slide.**
- **A screenshot on every content slide**, captioned with the source page.
- **The highlight must be the passage that supports that slide's claim.**
- **Body text ≥ 14pt.** If it does not fit, add slides — never shrink type.
- **English concepts get a Chinese gloss** (`主成分分析（PCA）`).
- **Emphasis is bold**, never 「」 or quotes.
- **No vague quantity summaries**: name the things, not the count.
- **Use the source's own wording.** Never assert a quotation you cannot locate.

## Workflow

1. Inventory the sources (`pdfinfo`, `pdftotext`); OCR a scan with
   `scripts/ocr_shots.py` (macOS Vision by default, tesseract elsewhere).
2. Read the sources properly and build a per-page map.
3. Outline — **about 20 slides** by default; merge, do not pad.
4. For every slide, name the exact sentence that supports it.
5. Crop the screenshots (`scripts/pdf_shots.py`), verifying the highlight.
6. Build the deck (`scripts/deck_kit.py`).
7. **QA loop** — mandatory, and it is a loop: fit report → geometry check →
   render → `scripts/qa_deck.py` → fresh-eyes visual review → fix → re-render.

## Editing an existing deck

**Always work from the human's file.** `ls -laT` it and compare **time and
size** against your last write; if it changed, they edited it, and that file
is the only valid baseline. Back it up with a timestamp, then edit in place.
**Never re-run a generator over it.**

## Teaching a user how to use this

`skills/build-academic-ppt/references/user-guide.md` is the walkthrough for
the person using the skill: what to prepare, the five steps, a worked
example dialogue, how to revise a deck they have already hand-edited, and the
common cases. Hand that file over when someone asks how to use this — do not
improvise a shorter version.

## Tool mapping

The skill is written against a Claude Code–shaped tool surface. On other
harnesses the equivalent is:

| in the skill | Claude Code | Codex | Cursor | Gemini CLI | Kimi | OpenCode | pi |
|---|---|---|---|---|---|---|---|
| run the scripts | Bash | shell | terminal | shell | Bash | Bash | Bash |
| read / write a file | Read / Write | read / write | read / write | read_file / write_file | Read / Write | read / write | read / write |
| **ask the human a question** | plain text | plain text | plain text | plain text | `AskUserQuestion` | plain text | plain text |
| **dispatch a fresh-eyes reviewer** | `Task` (verifier) | a subagent | a sub-agent | a sub-agent | `Agent` (`explore`) | a sub-agent | a sub-agent |
| track multi-step work | `TodoWrite` | plan | plan | plan | `TodoList` | plan | plan |

The one thing every harness must be able to do is **run a separate reviewer
that has not written the deck** — the QA protocol depends on it.

## Installing

```bash
./install.sh          # installs into every harness found on this machine
./install.sh --check  # verify the download without installing
```

The installer tries several download routes in turn (GitHub direct, mirrors,
the jsDelivr CDN, a shallow git clone) so it still works when GitHub is
unreachable, and it verifies the package before installing it.

## Keeping it current

```bash
python3 skills/build-academic-ppt/scripts/version_check.py   # report
bash    skills/build-academic-ppt/scripts/auto_upgrade.sh     # upgrade, verify, roll back
```

`auto_upgrade.sh` upgrades, runs the self-test on the new copy, and rolls
back to the previous one if it fails. The comparison is a hash over the
**whole package**, and the remote is fetched **pinned to a commit sha** --
a branch URL is served from a CDN cache that can lag a push by minutes, and
a version check that reads a cached file reports "current" when a new
version exists.

## Self-test

```bash
python3 skills/build-academic-ppt/scripts/selftest.py
```

32 checks, each one a behaviour that used to be broken.

## License

MIT.
