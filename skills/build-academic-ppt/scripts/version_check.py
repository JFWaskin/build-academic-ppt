#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
version_check -- is the installed skill still current, and can it be brought
up to date?

Why this exists: a skill installed by copying files is not tracked by any
package manager. Nothing tells you that the copy in ~/.claude/skills is three
revisions behind the repository, and the failure mode is quiet -- the deck
still builds, it just uses the old rules.

The check compares the installed copy against the remote on two axes:

  * the VERSION file            -- a human-readable version number
  * the sha256 of SKILL.md      -- the thing that actually decides behaviour

Both are fetched over the same resilient routes the installer uses, including
the jsDelivr CDN, which has a mainland node and is a completely different
network path from GitHub.

  python3 version_check.py            # report
  python3 version_check.py --json     # machine-readable
  python3 version_check.py --upgrade  # bring every install up to date

Exit codes
  0  every install is current
  1  at least one install is behind (or an upgrade was applied)
  2  the remote could not be reached -- the state is unknown
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.abspath(os.path.join(HERE, ".."))
SKILL_NAME = "build-academic-ppt"
REPO = os.environ.get("BUILD_ACADEMIC_PPT_REPO", "JFWaskin/build-academic-ppt")
REF = os.environ.get("BUILD_ACADEMIC_PPT_REF", "main")
TIMEOUT = int(os.environ.get("BUILD_ACADEMIC_PPT_TIMEOUT", "45"))

# The harness skill directories this skill installs into. A path is only
# checked when the harness is actually present on the machine.
HARNESSES = [
    ("Claude Code", "~/.claude/skills"),
    ("MiniMax Code", "~/.minimax/skills"),
    ("Codex", "~/.codex/skills"),
    ("OpenCode", "~/.config/opencode/skills"),
    ("Cursor", "~/.cursor/skills"),
    ("Gemini CLI", "~/.gemini/skills"),
    ("Kimi Code", "~/.kimi/skills"),
]

MIRRORS = [
    "https://ghfast.top/https://github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://github.moeyy.xyz/https://github.com",
]


def say(msg):
    print(msg, flush=True)


# ----------------------------------------------------------------- remote
def _curl(url, binary=False):
    try:
        r = subprocess.run(["curl", "-fsSL", "--connect-timeout", "8",
                            "--max-time", str(TIMEOUT), url],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", errors="ignore")


def _package_from_tarball(blob, label):
    """{relpath: bytes} for the whole skill package inside a tarball."""
    try:
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        files = {}
        marker = f"/skills/{SKILL_NAME}/"
        for m in tf.getmembers():
            if not m.isfile() or marker not in "/" + m.name:
                continue
            rel = m.name.split(marker, 1)[1]
            if any(part in SKIP_NAMES for part in rel.split("/")):
                continue
            files[rel] = tf.extractfile(m).read()
        tf.close()
        if files:
            return files, label
    except Exception:
        pass
    return None, None


def _package_from_jsdelivr(sha):
    """The whole package from jsDelivr, file by file.

    jsDelivr has a mainland node and is not GitHub at all, which makes it the
    most reliable route from inside China -- but it serves one file per
    request, so the file list comes from its data API first.
    """
    listing = _curl(f"https://data.jsdelivr.com/v1/packages/gh/{REPO}@{sha}"
                    f"?structure=flat")
    if not listing:
        return None, None
    try:
        entries = json.loads(listing).get("files", [])
    except Exception:
        return None, None
    marker = f"/skills/{SKILL_NAME}/"
    files = {}
    for e in entries:
        name = e.get("name", "")
        if marker not in "/" + name:
            continue
        rel = name.split(marker, 1)[1]
        if any(part in SKIP_NAMES for part in rel.split("/")):
            continue
        blob = _curl(f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/"
                     f"skills/{SKILL_NAME}/{rel}", binary=True)
        if blob is None:
            continue
        files[rel] = blob
    if files:
        return files, f"jsDelivr CDN @ {sha[:8]}"
    return None, None


def remote_package(sha=None):
    """Return ({relpath: bytes}, label) for the remote package, or (None, None).

    Everything is fetched PINNED to a commit sha when one is known. A branch
    URL is served from a CDN cache that can lag a push by minutes -- both
    codeload and jsDelivr were measured serving a stale tarball right after
    a push -- and a version check that reads a cached file reports "current"
    when a new version exists. That is the worst possible failure for this
    tool, so the branch path is only used when the sha cannot be resolved.
    """
    bust = str(int(time.time()))
    if sha:
        # one request, the whole package
        blob = _curl(f"https://codeload.github.com/{REPO}/tar.gz/{sha}",
                      binary=True)
        if blob:
            files, label = _package_from_tarball(
                blob, f"codeload.github.com @ {sha[:8]}")
            if files:
                return files, label
        # the China-friendly route: jsDelivr, file by file
        files, label = _package_from_jsdelivr(sha)
        if files:
            return files, label
        # then the proxies
        for m in MIRRORS:
            blob = _curl(f"{m}/{REPO}/archive/{sha}.tar.gz", binary=True)
            if blob:
                files, label = _package_from_tarball(
                    blob, f"proxy {m}")
                if files:
                    return files, label

    # branch fallback, cache-busted
    blob = _curl(f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/"
                 f"{REF}?cb={bust}", binary=True)
    if blob:
        files, label = _package_from_tarball(blob, "codeload (branch)")
        if files:
            return files, label
    for m in MIRRORS:
        blob = _curl(f"{m}/{REPO}/archive/refs/heads/{REF}.tar.gz?cb={bust}",
                      binary=True)
        if blob:
            files, label = _package_from_tarball(blob, f"proxy {m}")
            if files:
                return files, label
    return None, None


def remote_commit():
    """Best-effort commit sha of the remote branch."""
    try:
        r = subprocess.run(["git", "ls-remote",
                            f"https://github.com/{REPO}.git", REF],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=TIMEOUT)
        if r.returncode == 0:
            m = re.match(rb"([0-9a-f]{40})", r.stdout.strip())
            if m:
                return m.group(1).decode()
    except Exception:
        pass
    return None


# ----------------------------------------------------------------- local
def sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


SKIP_NAMES = ("INSTALL.json", ".DS_Store", "__pycache__")


def package_hash(files):
    """One hash for a whole package.

    Comparing SKILL.md alone is not enough: a release can change the scripts
    and leave SKILL.md byte-identical, and the check would then say "current"
    while the behaviour on disk is old. The hash covers every file, sorted by
    path, so the path itself is part of the identity.
    """
    h = hashlib.sha256()
    for rel in sorted(files):
        if any(part in SKIP_NAMES for part in rel.split("/")):
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(files[rel])
        h.update(b"\0")
    return h.hexdigest()


def local_package(root):
    """{relpath: bytes} for an installed or checked-out package."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]
        for fn in filenames:
            if fn in SKIP_NAMES:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                out[rel] = open(full, "rb").read()
            except OSError:
                pass
    return out


def local_state(base):
    d = os.path.join(os.path.expanduser(base), SKILL_NAME)
    sk = os.path.join(d, "SKILL.md")
    if not os.path.isfile(sk):
        return None
    ver = ""
    vf = os.path.join(d, "VERSION")
    if os.path.isfile(vf):
        ver = open(vf, encoding="utf-8").read().strip()
    stamp = {}
    sf = os.path.join(d, "INSTALL.json")
    if os.path.isfile(sf):
        try:
            stamp = json.load(open(sf, encoding="utf-8"))
        except Exception:
            pass
    return {"dir": d, "version": ver,
            "sha": package_hash(local_package(d)), "stamp": stamp}


# ----------------------------------------------------------------- upgrade
def upgrade():
    """Download the package and run the installer from inside it."""
    work = tempfile.mkdtemp(prefix="bdp_up_")
    tgz = os.path.join(work, "pkg.tgz")
    sha = remote_commit()
    pin = sha or "refs/heads/" + REF
    urls = [
        f"https://codeload.github.com/{REPO}/tar.gz/{pin}",
        f"https://github.com/{REPO}/archive/{pin}.tar.gz",
    ] + [f"{m}/{REPO}/archive/{pin}.tar.gz" for m in MIRRORS]
    got = False
    for u in urls:
        blob = _curl(u, binary=True)
        if blob:
            open(tgz, "wb").write(blob)
            got = True
            break
    if not got:
        say("  upgrade: could not download the package")
        return False
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(work)
    root = os.path.join(work, f"{REPO.split('/')[-1]}-{(sha or REF)}")
    installer = os.path.join(root, "install.sh")
    if not os.path.isfile(installer):
        say("  upgrade: the package has no install.sh")
        return False
    r = subprocess.run(["bash", installer],
                       env={**os.environ, "BUILD_ACADEMIC_PPT_COMMIT": sha or ""},
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    say(r.stdout.decode("utf-8", "ignore"))
    return r.returncode == 0


# ----------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--upgrade", action="store_true")
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args(argv)

    installs = []
    for name, base in HARNESSES:
        st = local_state(base)
        if st:
            installs.append((name, st))

    if not installs:
        say("build-academic-ppt is not installed on this machine")
        return 2

    remote_sha = None if args.no_network else remote_commit()
    if remote_sha:
        say(f"remote commit: {remote_sha}")
    remote_pkg, remote_label = (None, None) if args.no_network \
        else remote_package(remote_sha)
    remote = None
    if remote_pkg:
        ver = remote_pkg.get("VERSION", b"")
        remote = {"VERSION": ver.decode("utf-8", "ignore").strip()
                  if isinstance(ver, bytes) else ver,
                  "SKILL.md": remote_pkg.get("SKILL.md", b""),
                  "source": remote_label,
                  "hash": package_hash(remote_pkg)}
    if remote is None and not args.no_network:
        say("could not reach the remote -- the state is UNKNOWN")
        say("  (this is a network verdict, not a verdict on the install)")
        return 2

    if remote:
        say(f"remote {remote['VERSION'] or '(no VERSION)'}  "
            f"(fetched via {remote['source']})")
    say("")

    rows = []
    behind = 0
    remote_sha_short = (remote_sha or "")[:8]
    for name, st in installs:
        if remote is None:
            status = "unknown"
        elif st["sha"] == remote["hash"]:
            status = "current"
        else:
            status = "behind"
            behind += 1
        rows.append({"harness": name, "dir": st["dir"], "version": st["version"],
                     "status": status, "installed_at": st["stamp"].get("installed_at", ""),
                     "commit": st["stamp"].get("commit", "")[:8],
                     "remote_commit": remote_sha_short})

    if args.json:
        print(json.dumps({"remote": remote["VERSION"] if remote else None,
                          "remote_commit": remote_sha,
                          "remote_source": remote["source"] if remote else None,
                          "installs": rows, "behind": behind}, ensure_ascii=False,
                         indent=2))
    else:
        for r in rows:
            mark = {"current": "ok    ", "behind": "BEHIND", "unknown": "?     "}[r["status"]]
            say(f"  {mark}  {r['harness']:<15} v{r['version'] or '?':<8} "
                f"{r['dir']}")
        say("")
        if behind:
            say(f"{behind} of {len(rows)} install(s) are behind.")
        else:
            say(f"all {len(rows)} install(s) are current.")

    if args.upgrade and behind:
        say("")
        say("upgrading ...")
        if not upgrade():
            return 2
        say("upgrade applied; re-run this command to confirm.")

    return 1 if behind else 0


if __name__ == "__main__":
    raise SystemExit(main())
