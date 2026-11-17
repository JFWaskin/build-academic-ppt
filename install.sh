#!/usr/bin/env bash
# Install build-academic-ppt, trying several download routes in turn.
#
# Why not a single command: GitHub's reachability from mainland China is
# uneven -- the main site, codeload, the API and the raw CDN each fail at
# different times, and a proxy that works today may be gone next month. So
# this installer tries every route in order and stops at the first one that
# produces a valid package. It prints which route worked, so a failed
# install is diagnosable instead of mysterious.
#
# Usage
#   ./install.sh                     install for Claude Code and MiniMax Code
#   ./install.sh --check             only verify the download, do not install
#   ./install.sh --uninstall         remove it again
#
# Environment
#   BUILD_ACADEMIC_PPT_REPO   owner/name of a mirror repo (e.g. your Gitee
#                             mirror) to try FIRST
#   BUILD_ACADEMIC_PPT_REF    branch or tag (default: main)
#   BUILD_ACADEMIC_PPT_DIR    where to install (default: ~/.claude/skills)
#   BUILD_ACADEMIC_PPT_MCODEX_DIR
#                             second install location (default: ~/.minimax/skills)
#   BUILD_ACADEMIC_PPT_MIRRORS
#                             newline-separated mirror prefixes, tried in order
#   BUILD_ACADEMIC_PPT_TIMEOUT
#                             seconds per attempt (default: 45)
set -u

REPO="${BUILD_ACADEMIC_PPT_REPO:-JFWaskin/build-academic-ppt}"
REF="${BUILD_ACADEMIC_PPT_REF:-main}"
SKILL_NAME="build-academic-ppt"
DEST_BASE="${BUILD_ACADEMIC_PPT_DIR:-$HOME/.claude/skills}"
MCODEX_DIR="${BUILD_ACADEMIC_PPT_MCODEX_DIR:-$HOME/.minimax/skills}"
TIMEOUT="${BUILD_ACADEMIC_PPT_TIMEOUT:-45}"
CHECK_ONLY=0
UNINSTALL=0

for a in "$@"; do
  case "$a" in
    --check) CHECK_ONLY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --help|-h) sed -n '2,28p' "$0"; exit 0 ;;
  esac
done

say() { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }

# ---------------------------------------------------------------- uninstall
if [ "$UNINSTALL" -eq 1 ]; then
  step "removing $SKILL_NAME"
  for d in "$DEST_BASE/$SKILL_NAME" "$MCODEX_DIR/$SKILL_NAME"; do
    if [ -d "$d" ]; then
      mv "$d" "$d.backup.$(date +%Y%m%dT%H%M%S)" && say "  moved $d to a timestamped backup"
    fi
  done
  say "done. backups are kept; delete them yourself when you are sure."
  exit 0
fi

# ---------------------------------------------------------------- download
WORK="$(mktemp -d "${TMPDIR:-/tmp}/bdp.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
TARBALL="$WORK/pkg.tar.gz"
USED_ROUTE=""

# A mirror prefix means <prefix>/<owner>/<repo>/archive/refs/heads/<ref>.tar.gz
DEFAULT_MIRRORS="https://ghfast.top/https://github.com
https://gh-proxy.com/https://github.com
https://ghproxy.net/https://github.com
https://github.moeyy.xyz/https://github.com
https://hub.gitmirror.com/https://github.com"
MIRRORS="${BUILD_ACADEMIC_PPT_MIRRORS:-$DEFAULT_MIRRORS}"

try_url() {
  local url="$1" label="$2"
  say "  trying $label"
  if curl -fsSL --connect-timeout 8 --max-time "$TIMEOUT" -o "$TARBALL.part" "$url"; then
    # a proxy that returns an HTML error page is worse than no answer
    if tar -tzf "$TARBALL.part" >/dev/null 2>&1; then
      mv "$TARBALL.part" "$TARBALL"
      USED_ROUTE="$label"
      say "  ok -- $label"
      return 0
    fi
    say "  failed -- not a valid tarball (blocked, or an error page?)"
  else
    say "  failed -- timeout or connection refused"
  fi
  rm -f "$TARBALL.part"
  return 1
}

step "downloading $SKILL_NAME"
say "repo: $REPO  ref: $REF"

# 0. an operator-provided mirror repo (a Gitee mirror, say) wins outright
if [ "$REPO" != "JFWaskin/build-academic-ppt" ]; then
  try_url "https://codeload.github.com/$REPO/tar.gz/refs/heads/$REF" "codeload (mirror repo)"
fi

# 1. GitHub directly
if [ -z "$USED_ROUTE" ]; then
  try_url "https://codeload.github.com/$REPO/tar.gz/refs/heads/$REF" "codeload.github.com (direct)"
fi
if [ -z "$USED_ROUTE" ]; then
  try_url "https://github.com/$REPO/archive/refs/heads/$REF.tar.gz" "github.com archive (direct)"
fi

# 2. proxies, in order
if [ -z "$USED_ROUTE" ]; then
  while IFS= read -r m; do
    [ -z "$m" ] && continue
    try_url "$m/$REPO/archive/refs/heads/$REF.tar.gz" "proxy $m" && break
  done <<EOF
$MIRRORS
EOF
fi

# 3. jsDelivr's CDN: a different network path from GitHub entirely, and it
#    has a mainland node. It serves files one at a time, so the file list
#    comes from its data API first.
if [ -z "$USED_ROUTE" ]; then
  say "  trying jsDelivr CDN"
  LIST="$WORK/files.json"
  if curl -fsSL --connect-timeout 8 --max-time "$TIMEOUT" \
       -o "$LIST" "https://data.jsdelivr.com/v1/packages/gh/$REPO@$REF?structure=flat" \
     && python3 - "$LIST" > "$WORK/paths.txt" 2>/dev/null <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
prefix = "skills/build-academic-ppt/"
for f in data.get("files", []):
    p = f.get("name", "").lstrip("/")      # jsDelivr lists paths with a leading /
    # the flat listing carries name/hash/size, no "type" field
    if p.startswith(prefix) and "size" in f:
        print(p)
PY
  then
    PKGDIR="$WORK/pkg/skills/$SKILL_NAME"
    mkdir -p "$PKGDIR"
    ok=1
    while IFS= read -r p; do
      rel="${p#skills/$SKILL_NAME/}"
      mkdir -p "$PKGDIR/$(dirname "$rel")"
      if ! curl -fsSL --connect-timeout 8 --max-time "$TIMEOUT" \
            -o "$PKGDIR/$rel" "https://cdn.jsdelivr.net/gh/$REPO@$REF/$p"; then
        ok=0; break
      fi
    done < "$WORK/paths.txt"
    if [ "$ok" -eq 1 ] && [ -f "$PKGDIR/SKILL.md" ]; then
      USED_ROUTE="jsDelivr CDN"
      say "  ok -- jsDelivr CDN"
    else
      say "  failed -- jsDelivr"
      rm -rf "$WORK/pkg"
    fi
  else
    say "  failed -- jsDelivr (no file list)"
  fi
fi

# 4. git, as a last resort -- shallow, so it is small and fast
if [ -z "$USED_ROUTE" ]; then
  say "  trying git clone --depth 1"
  if git clone --depth 1 --quiet "https://github.com/$REPO.git" "$WORK/clone" 2>/dev/null; then
    if [ -f "$WORK/clone/skills/$SKILL_NAME/SKILL.md" ]; then
      cp -R "$WORK/clone" "$WORK/pkg"
      USED_ROUTE="git clone --depth 1 (direct)"
      say "  ok -- git clone"
    fi
  else
    say "  failed -- git clone"
  fi
fi

if [ -z "$USED_ROUTE" ]; then
  say ""
  say "Every download route failed."
  say ""
  say "Point the installer at a mirror you control and try again, e.g. a Gitee mirror:"
  say "  BUILD_ACADEMIC_PPT_REPO=<owner>/<repo> ./install.sh"
  say ""
  say "Or download the tarball by hand and run install.sh from the extracted folder."
  exit 1
fi

say ""
say "downloaded via: $USED_ROUTE"

# ---------------------------------------------------------------- extract
step "unpacking"
PKG="$WORK/pkg"
if [ ! -d "$PKG" ]; then
  mkdir -p "$PKG"
  tar -xzf "$TARBALL" -C "$PKG" --strip-components=1 || exit 1
fi
SKILL_SRC="$PKG/skills/$SKILL_NAME"
if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  say "the package does not contain skills/$SKILL_NAME/SKILL.md -- wrong archive?"
  exit 1
fi
say "  ok"

# ---------------------------------------------------------------- verify
step "verifying the package"
for f in SKILL.md references/intake.md references/styles.md references/authoring-rules.md \
         references/design-system.md references/qa-protocol.md \
         scripts/deck_kit.py scripts/themes.py scripts/brief.py scripts/qa_deck.py \
         scripts/pdf_shots.py scripts/ocr_shots.py scripts/selftest.py \
         scripts/style_previews.py; do
  if [ ! -f "$SKILL_SRC/$f" ]; then
    say "  MISSING $f"
    exit 1
  fi
done
say "  all expected files present"

if command -v python3 >/dev/null 2>&1; then
  if ! python3 - "$SKILL_SRC" <<'PY'
import ast, os, sys
root = sys.argv[1]
bad = []
for dirpath, dirnames, filenames in os.walk(os.path.join(root, "scripts")):
    dirnames[:] = [d for d in dirnames if d != "__pycache__"]
    for fn in filenames:
        if fn.endswith(".py"):
            p = os.path.join(dirpath, fn)
            try:
                ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError as e:
                bad.append(f"{fn}: {e}")
if bad:
    print("\n".join(bad))
    sys.exit(1)
PY
  then
    say "  the scripts do not parse -- the download is damaged"
    exit 1
  fi
  say "  every script parses"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  step "download verified (--check, nothing installed)"
  exit 0
fi

# ---------------------------------------------------------------- install
step "installing"
for base in "$DEST_BASE" "$MCODEX_DIR"; do
  [ -z "$base" ] && continue
  mkdir -p "$base"
  dest="$base/$SKILL_NAME"
  if [ -d "$dest" ]; then
    bak="$dest.backup.$(date +%Y%m%dT%H%M%S)"
    say "  backing up the existing copy to $(basename "$bak")"
    mv "$dest" "$bak"
  fi
  cp -R "$SKILL_SRC" "$dest"
  find "$dest" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
  say "  installed -> $dest"
done

# ---------------------------------------------------------------- deps
step "dependency check"
MISSING=0
if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import pptx, fitz, PIL, lxml" >/dev/null 2>&1; then
    say "  [ok]      python3 + python-pptx + PyMuPDF + Pillow + lxml"
  else
    say "  [missing] python packages: pip install python-pptx pymupdf pillow lxml"
    MISSING=1
  fi
else
  say "  [missing] python3"; MISSING=1
fi
if command -v soffice >/dev/null 2>&1; then
  say "  [ok]      soffice (rendering for QA)"
else
  say "  [missing] soffice: brew install --cask libreoffice"; MISSING=1
fi
if command -v pdftoppm >/dev/null 2>&1 && command -v pdftotext >/dev/null 2>&1; then
  say "  [ok]      poppler (pdftoppm, pdftotext)"
else
  say "  [missing] poppler: brew install poppler"; MISSING=1
fi
if command -v tesseract >/dev/null 2>&1; then
  say "  [ok]      tesseract (scanned sources)"
else
  say "  [optional] tesseract: brew install tesseract  (only for scanned PDFs)"
fi

# ---------------------------------------------------------------- selftest
if [ "$MISSING" -eq 0 ] && command -v python3 >/dev/null 2>&1; then
  step "self-test"
  python3 "$DEST_BASE/$SKILL_NAME/scripts/selftest.py" 2>&1 | tail -3
  say ""
  say "Installed and verified."
fi

cat <<EOF

Next
  1. restart the agent so it picks the skill up
  2. ask for a deck, e.g.:
       用 $SKILL_NAME 把我的论文 PDF 做成 20 页中文汇报 PPT，
       先问我主题、要点、研究问题和风格，给我看样式样张。
  3. to install from a mirror you control (a Gitee mirror, say):
       BUILD_ACADEMIC_PPT_REPO=<owner>/<repo> ./install.sh
EOF
exit 0
