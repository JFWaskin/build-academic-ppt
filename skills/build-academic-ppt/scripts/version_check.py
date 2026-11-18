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


def remote_files():
    """Return {'VERSION': text, 'SKILL.md': bytes, 'source': label} or None.

    Tries the jsDelivr CDN first (it has a mainland node and is not GitHub),
    then codeload, then the proxies.
    """
    base = f"https://cdn.jsdelivr.net/gh/{REPO}@{REF}/skills/{SKILL_NAME}"
    version = _curl(f"{base}/VERSION")
    skill = _curl(f"{base}/SKILL.md", binary=True)
    if version and skill:
        return {"VERSION": version.strip(), "SKILL.md": skill,
                "source": "jsDelivr CDN"}
    if skill and not version:
        # the remote is reachable but predates the version stamp
        return {"VERSION": "", "SKILL.md": skill, "source": "jsDelivr CDN",
                "no_version": True}

    for prefix in ["", *MIRRORS]:
        url = (f"{prefix}/" if prefix else "") + \
            f"{REPO}/archive/refs/heads/{REF}.tar.gz"
        blob = _curl(url, binary=True)
        if not blob:
            continue
        try:
            tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
            ver = None
            sk = None
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.name.endswith(f"/skills/{SKILL_NAME}/VERSION"):
                    ver = tf.extractfile(m).read().decode("utf-8", "ignore").strip()
                elif m.name.endswith(f"/skills/{SKILL_NAME}/SKILL.md"):
                    sk = tf.extractfile(m).read()
            tf.close()
            if sk:
                label = ("codeload.github.com" if not prefix
                         else f"proxy {prefix}")
                return {"VERSION": ver or "", "SKILL.md": sk, "source": label,
                        "no_version": ver is None}
        except Exception:
            continue
    return None


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
    return {"dir": d, "version": ver, "sha": sha256(open(sk, "rb").read()),
            "stamp": stamp}


# ----------------------------------------------------------------- upgrade
def upgrade():
    """Download the package and run the installer from inside it."""
    work = tempfile.mkdtemp(prefix="bdp_up_")
    tgz = os.path.join(work, "pkg.tgz")
    urls = [
        f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/{REF}",
        f"{REPO}/archive/refs/heads/{REF}.tar.gz".join(["https://github.com/", ""]),
    ] + [f"{m}/{REPO}/archive/refs/heads/{REF}.tar.gz" for m in MIRRORS]
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
    root = os.path.join(work, f"{REPO.split('/')[-1]}-{REF}")
    installer = os.path.join(root, "install.sh")
    if not os.path.isfile(installer):
        say("  upgrade: the package has no install.sh")
        return False
    r = subprocess.run(["bash", installer], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
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

    remote = None if args.no_network else remote_files()
    if remote is None and not args.no_network:
        say("could not reach the remote -- the state is UNKNOWN")
        say("  (this is a network verdict, not a verdict on the install)")
        return 2
    if remote and remote.get("no_version"):
        say("the remote has no VERSION file -- it predates the version stamp")
        say("comparing content hashes instead")
    if remote:
        say(f"remote {remote['VERSION'] or '(no VERSION)'}  "
            f"(fetched via {remote['source']})")
    say("")

    rows = []
    behind = 0
    for name, st in installs:
        if remote is None:
            status = "unknown"
        elif st["sha"] == sha256(remote["SKILL.md"]):
            status = "current"
        else:
            status = "behind"
            behind += 1
        rows.append({"harness": name, "dir": st["dir"], "version": st["version"],
                     "status": status, "installed_at": st["stamp"].get("installed_at", ""),
                     "commit": st["stamp"].get("commit", "")})

    if args.json:
        print(json.dumps({"remote": remote["VERSION"] if remote else None,
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
