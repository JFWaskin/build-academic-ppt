#!/usr/bin/env bash
# Check the installed skill against the remote and, if it is behind, bring it
# up to date -- then PROVE the new copy works before keeping it.
#
# The order matters: upgrade, verify, and only then keep it. A copy that
# fails the self-test is rolled back to the backup the installer took, so a
# bad push can never leave the machine with a broken skill.
#
#   ./auto_upgrade.sh          check, upgrade if needed, verify
#   ./auto_upgrade.sh --check  report only, change nothing
#
# Exit codes
#   0  everything is current (nothing to do)
#   1  an upgrade was applied and verified
#   2  the remote could not be reached -- the state is unknown
#   3  the upgrade failed the self-test and was rolled back
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="build-academic-ppt"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

say() { printf '%s\n' "$*"; }

HARNESS_DIRS="$HOME/.claude/skills
$HOME/.minimax/skills
$HOME/.codex/skills
$HOME/.config/opencode/skills
$HOME/.cursor/skills
$HOME/.gemini/skills
$HOME/.kimi/skills"

say "== build-academic-ppt upgrade check"
say "   when: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say ""

BEFORE="$(python3 "$HERE/version_check.py" --json 2>/dev/null)"
RC=$?
if [ "$RC" -eq 2 ]; then
  say "could not reach the remote -- the state is UNKNOWN"
  say "(a network verdict, not a verdict on the install)"
  exit 2
fi
if [ "$RC" -ne 0 ]; then
  say "an update is available:"
  printf '%s\n' "$BEFORE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print('   remote: %s @ %s' % (d.get('remote'), (d.get('remote_commit') or '')[:8]))
for i in d.get('installs', []):
    if i.get('status') == 'behind':
        print('   behind: %-16s %s' % (i['harness'], i['dir']))
"
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  say ""
  say "--check: nothing was changed"
  exit "$RC"
fi

if [ "$RC" -eq 0 ]; then
  say ""
  say "all installs are current -- nothing to do"
  exit 0
fi

say ""
say "upgrading ..."

# The installer backs up the existing copy before overwriting it. Keep the
# newest backup so a failed upgrade can be rolled back to it.
BACKUP=""
for d in "$HOME/.claude/.skill-backups" "$HOME/.minimax/.skill-backups" \
         "$HOME/.codex/.skill-backups" "$HOME/.config/opencode/.skill-backups" \
         "$HOME/.cursor/.skill-backups" "$HOME/.gemini/.skill-backups" \
         "$HOME/.kimi/.skill-backups"; do
  [ -d "$d" ] || continue
  last="$(ls -1d "$d"/$SKILL_NAME.* 2>/dev/null | sort | tail -1)"
  if [ -n "$last" ]; then BACKUP="$last"; break; fi
done

# version_check.py --upgrade returns:
#   0  nothing to do
#   1  an upgrade was applied
#   2  the upgrade could not be applied
python3 "$HERE/version_check.py" --upgrade
UP_RC=$?
if [ "$UP_RC" -eq 2 ]; then
  say "the upgrade could not be applied"
  exit 2
fi

say ""
say "verifying the new copy"
SELFTEST_LOG="$(mktemp)"
if python3 "$HOME/.claude/skills/$SKILL_NAME/scripts/selftest.py" >"$SELFTEST_LOG" 2>&1; then
  say "  self-test passed"
  tail -2 "$SELFTEST_LOG"
  say ""
  say "upgrade applied and verified."
  exit 1
fi

say "  the self-test FAILED after the upgrade"
tail -12 "$SELFTEST_LOG"
if [ -n "$BACKUP" ] && [ -d "$BACKUP" ]; then
  say ""
  say "rolling back to $BACKUP"
  STAMP="$(date +%Y%m%dT%H%M%S)"
  while IFS= read -r d; do
    [ -z "$d" ] && continue
    if [ -d "$d/$SKILL_NAME" ]; then
      mv "$d/$SKILL_NAME" "$d/$SKILL_NAME.failed.$STAMP" 2>/dev/null
    fi
    [ -d "$d" ] && cp -R "$BACKUP" "$d/$SKILL_NAME" 2>/dev/null
  done <<EOF
$HARNESS_DIRS
EOF
  say "rolled back. The remote version is broken -- do not upgrade to it."
  exit 3
fi
say ""
say "no backup was found to roll back to -- the install is now unverified."
exit 3
