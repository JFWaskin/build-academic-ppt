#!/usr/bin/env bash
# Install the build-academic-ppt skill into ~/.claude/skills and check that
# the dependencies it needs are present.
set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$REPO_DIR/skills/build-academic-ppt"
SKILL_NAME="build-academic-ppt"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "build-academic-ppt installer"
echo "  source : $SKILL_SRC"
echo "  target : $DEST/$SKILL_NAME"
echo

if [ ! -d "$SKILL_SRC" ]; then
  echo "ERROR: skill directory not found at $SKILL_SRC"
  exit 1
fi

mkdir -p "$DEST"
if [ -e "$DEST/$SKILL_NAME" ]; then
  BACKUP="$DEST/$SKILL_NAME.backup.$(date +%Y%m%dT%H%M%S)"
  echo "  existing skill found -> backing up to $BACKUP"
  mv "$DEST/$SKILL_NAME" "$BACKUP"
fi

cp -R "$SKILL_SRC" "$DEST/$SKILL_NAME"
find "$DEST/$SKILL_NAME" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
echo "  installed."
echo

echo "Dependency check:"
MISSING=0
have() { command -v "$1" >/dev/null 2>&1; }

py_ok=0
if have python3; then
  if python3 -c "import pptx, fitz, PIL, lxml" >/dev/null 2>&1; then
    echo "  [ok]      python3 + python-pptx + PyMuPDF + Pillow + lxml"
    py_ok=1
  else
    echo "  [missing] python packages: pip install python-pptx pymupdf pillow lxml"
    MISSING=1
  fi
else
  echo "  [missing] python3"
  MISSING=1
fi

if have soffice; then
  echo "  [ok]      soffice (rendering for QA)"
else
  echo "  [missing] soffice: brew install --cask libreoffice"
  MISSING=1
fi

if have pdftoppm && have pdftotext; then
  echo "  [ok]      poppler (pdftoppm, pdftotext)"
else
  echo "  [missing] poppler: brew install poppler"
  MISSING=1
fi

if have tesseract; then
  echo "  [ok]      tesseract (scanned sources)"
else
  echo "  [optional] tesseract: brew install tesseract   (only for scanned PDFs)"
fi

echo
if [ "$MISSING" -eq 0 ]; then
  echo "All required dependencies are present."
else
  echo "Some required dependencies are missing (see above)."
fi
echo
echo "Next:"
echo "  1. restart Claude Code so it picks the skill up"
echo "  2. run the self-test:  python3 \"$DEST/$SKILL_NAME/scripts/selftest.py\""
echo "  3. ask Claude Code to use the skill, e.g.:"
echo "     \"用 build-academic-ppt 把我的论文 PDF 做成 20 页中文汇报 PPT，"
echo "先问我主题、要点、研究问题和风格。\""

exit 0
