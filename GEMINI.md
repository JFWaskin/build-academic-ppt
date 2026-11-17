# build-academic-ppt — Gemini CLI

This repository is a portable **skill**, not a Claude Code plugin. The skill
lives in `skills/build-academic-ppt/` and is plain files: a `SKILL.md` with
YAML frontmatter, a `references/` folder, and Python scripts.

**Read `AGENTS.md` in the repository root first** — it is the full guide
(workflow, the mandatory intake brief, the seven visual styles, the
non-negotiable content rules, the QA loop, and the tool mapping for every
harness).

## Gemini CLI notes

- Run the scripts with the shell tool, from `skills/build-academic-ppt/scripts/`.
- The skill's scripts need `python-pptx`, `PyMuPDF`, `Pillow` and `lxml`:
  `pip install python-pptx pymupdf pillow lxml`.
- `ocr_shots.py` prefers **macOS Vision** for Chinese scans; on other
  platforms it falls back to tesseract (`brew install tesseract` /
  `apt install tesseract-ocr tesseract-ocr-chi-sim`).
- The QA protocol asks for a **reviewer that did not write the deck**. Spawn a
  sub-agent for that; the step is mandatory, not optional.

## Install

```bash
gemini extensions install https://github.com/JFWaskin/build-academic-ppt
```

or link the skill directly:

```bash
gemini skills link skills/build-academic-ppt --consent
```

or use the repository installer, which detects the harnesses present on the
machine:

```bash
./install.sh
```
