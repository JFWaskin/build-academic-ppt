# Installing build-academic-ppt for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation

Add the plugin to the `plugin` array in your `opencode.json` (global or
project-level):

```json
{
  "plugin": ["build-academic-ppt@git+https://github.com/JFWaskin/build-academic-ppt.git"]
}
```

Restart OpenCode. The plugin registers the repository's `skills/` directory,
so `build-academic-ppt` becomes available.

Verify by asking: "list your skills" or "what does build-academic-ppt do?".

OpenCode uses its own plugin install. If you also use Claude Code, Codex, or
another harness, install build-academic-ppt separately for each one — or run
the repository's `./install.sh`, which detects the harnesses present on the
machine and copies the skill into each of them.

## Manual install (no plugin machinery)

```bash
mkdir -p ~/.config/opencode/skills
cp -R skills/build-academic-ppt ~/.config/opencode/skills/
```

## Migrating from the old symlink-based install

If you previously installed with `git clone` and symlinks:

```bash
rm -f ~/.config/opencode/plugins/build-academic-ppt.js
rm -rf ~/.config/opencode/skills/build-academic-ppt
```

## Note on reachability

The `git+https://` plugin URL needs GitHub to be reachable. If it is not, use
the repository's `./install.sh`, which tries several download routes in turn
(GitHub direct, mirrors, the jsDelivr CDN, a shallow git clone) and verifies
the package before installing it.
