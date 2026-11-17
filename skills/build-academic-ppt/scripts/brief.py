#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brief -- the intake gate for a deck build.

The rule this enforces: **do not start building until the brief is complete.**
A deck built on a guessed research question is not a deliverable, it is a
guess with a file extension. The previous version of this skill had no intake
step at all, and the result was decks with the wrong emphasis, the wrong
length and the wrong visual register -- none of which the author could fix
without a rewrite.

Two-round rule
--------------
Round 1: ask every unanswered question, in one batch.
Round 2: ask again -- only what is still unanswered, and only if the answers
         in round 1 were missing, empty or unusable.
Round 3+: the human has had two chances. Derive the rest from the sources and
         mark it `default` (assumption). Every assumption is listed in the
         delivery, so the human can correct one field instead of rewriting the
         deck.

Never invent a research question. It is either given by the human, stated in
the source document, or derived from the source and labelled as derived.

Commands
--------
  brief.py questions [--lang zh|en]   print the questionnaire for this round
  brief.py record --key K --value V [--source given|derived|default]
  brief.py derive                     auto-derive from the source documents
  brief.py status                     what is missing, what is assumed
  brief.py defaults                   fill the rest from defaults (round >= 2)
  brief.py check                      gate: exit 0 only when the brief is full
  brief.py summary                    markdown brief for the build script

The brief lives in `.deck-brief.json` next to the work (override with --file).
"""
import argparse
import json
import os
import re
import sys

BRIEF_NAME = ".deck-brief.json"


# ------------------------------------------------------------------ fields
class Field:
    def __init__(self, key, zh, en, question_zh, question_en, required=False,
                 default=None, derive=None):
        self.key = key
        self.zh = zh
        self.en = en
        self.question_zh = question_zh
        self.question_en = question_en
        self.required = required
        self.default = default
        self.derive = derive        # key of the derivation routine, if any


FIELDS = [
    Field("title", "主题 / 标题", "Topic / title",
          "这份演示要讲什么？用一句话说出主题或中心命题。",
          "What is this presentation about? Give the topic or central claim in one sentence.",
          required=True, derive="title"),
    Field("key_points", "核心要点", "Key points",
          "最想传达的 3–5 个要点是什么？请按重要性排序。",
          "Which 3–5 points must land? List them in priority order.",
          required=True, derive="key_points"),
    Field("research_question", "研究问题", "Research question",
          "这份材料要回答的研究问题是什么？（若材料本身已提出问题，就用材料里的说法）",
          "What research question does this material answer? Use the question as the source states it.",
          required=True, derive="research_question"),
    Field("sources", "源材料", "Source material",
          "要用哪些文件作为证据来源？（PDF / DOCX 的路径或文件名）",
          "Which files are the evidence base? Give paths or file names.",
          required=True, derive="sources"),
    Field("style", "视觉风格", "Visual style",
          "选哪种视觉风格？（可用 preview 图或 style 名称）",
          "Which visual style? Pick from the previews or name a style.",
          default="paper-warm"),
    Field("length", "篇幅（页）", "Length (slides)",
          "大概多少页？（默认 20 页左右；内容多时优先合并而不是加页）",
          "Roughly how many slides? Default is about 20; merge rather than pad.",
          default="20"),
    Field("audience", "听众", "Audience",
          "谁会看？同学 / 导师 / 学术会议 / 公众？",
          "Who is the audience? Peers, adviser, conference, public?",
          default="本领域研究生与研究者（默认假设）"),
    Field("occasion", "场合", "Occasion",
          "什么场合讲？组会、答辩、对外讲座？",
          "What occasion? Lab meeting, defence, public talk?",
          default="组会 / 学术报告（默认假设）"),
    Field("language", "语言", "Language",
          "中文、英文还是双语？",
          "Chinese, English, or bilingual?",
          default="跟随源材料（默认假设）"),
    Field("citation_style", "引注格式", "Citation style",
          "引注格式？（默认 APA 7th：作者-年份，完整条目）",
          "Citation style? Default APA 7th (author-date, full entries).",
          default="APA 7th（完整条目）"),
]

BY_KEY = {f.key: f for f in FIELDS}
REQUIRED = [f for f in FIELDS if f.required]
DEFAULTS = {f.key: f.default for f in FIELDS if f.default is not None}


# ------------------------------------------------------------------ brief io
def load(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"round": 0, "answers": {}, "sources_of": {}, "history": []}


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def answered(brief, key):
    v = brief["answers"].get(key)
    return bool(v) and (not isinstance(v, str) or v.strip())


def missing(brief):
    return [f for f in REQUIRED if not answered(brief, f.key)]


# ------------------------------------------------------------------ derive
RQ_PATTERNS = [
    r"[^。.\n]{0,60}研究问题[^。.\n]{0,120}[?？。]",
    r"[^。.\n]{0,60}研究问题[^。.\n]{0,120}",
    r"[^。.\n]{0,60}本文(?:旨在|试图|关注|探讨|处理)[^。.\n]{0,120}[。.]",
    r"[^。.\n]{0,60}本研究(?:旨在|试图|关注|探讨|处理)[^。.\n]{0,120}[。.]",
    r"[^。.\n]{0,60}we (?:ask|investigate|examine|argue)[^.\n]{0,160}[.?]",
    r"[^.\n]{0,60}this (?:paper|study|article) (?:asks|examines|explores|argues)[^.\n]{0,160}[.?]",
    r"[^.\n]{0,60}research question[^.\n]{0,160}[.?]",
]

SECTION_HINTS = ("摘要", "abstract", "引言", "绪论", "introduction", "结论",
                 "conclusion", "讨论", "discussion", "方法", "method",
                 "研究问题", "问题意识", "框架", "小结")


def detect_sources(root="."):
    """Find candidate source documents next to the work."""
    exts = (".pdf", ".docx", ".md", ".txt")
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            if fn.lower().endswith(exts):
                hits.append(os.path.relpath(os.path.join(dirpath, fn), root))
    hits.sort(key=lambda p: (0 if p.lower().endswith((".pdf", ".docx")) else 1, p))
    return hits[:20]


def _pdf_text(path):
    try:
        import fitz
    except ImportError:
        return ""
    out = []
    try:
        doc = fitz.open(path)
        for pno in range(min(6, doc.page_count)):
            out.append(doc[pno].get_text("text"))
        doc.close()
    except Exception:
        pass
    return "\n".join(out)


def _docx_text(path):
    try:
        import docx
    except ImportError:
        return ""
    out = []
    try:
        d = docx.Document(path)
        for p in d.paragraphs[:400]:
            if p.text.strip():
                out.append(p.text.strip())
    except Exception:
        pass
    return "\n".join(out)


def read_text(path):
    if path.lower().endswith(".pdf"):
        return _pdf_text(path)
    if path.lower().endswith(".docx"):
        return _docx_text(path)
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()[:200000]
    except Exception:
        return ""


def derive_title(texts):
    """Best-effort topic line from the head of the sources."""
    for t in texts:
        for line in t.splitlines():
            s = line.strip()
            if 6 <= len(s) <= 80 and not s.startswith(("http", "DOI", "doi")):
                if any(ch in s for ch in "的了与和在对中"):   # CJK title-ish
                    return s
                if re.match(r"^[A-Z][\w\s\-:,]{8,79}$", s):
                    return s
    return ""


def derive_rq(texts):
    """Find an explicitly stated research question."""
    for t in texts:
        flat = re.sub(r"[ \t]+", " ", t)
        for pat in RQ_PATTERNS:
            m = re.search(pat, flat, re.I)
            if m:
                s = m.group(0).strip()
                if 10 <= len(s) <= 220:
                    return s
    return ""


def derive_key_points(texts):
    """Section headings and short declarative lines, as a starting skeleton."""
    points, seen = [], set()
    for t in texts:
        for raw in t.splitlines():
            s = raw.strip()
            if not s or len(s) > 60:
                continue
            if any(h in s.lower() for h in SECTION_HINTS):
                key = s[:30]
                if key not in seen:
                    seen.add(key)
                    points.append(s)
            if len(points) >= 8:
                return points
    return points


def _resolve(root, p):
    """Source paths are stored relative to the brief's root. Reading one has
    to resolve against that root -- otherwise the read fails in the CWD,
    returns nothing, and the derivation silently comes up empty."""
    if os.path.isabs(p):
        return p
    cand = os.path.join(root, p)
    if os.path.exists(cand):
        return cand
    return p


def derive_all(brief, root="."):
    """Fill derivable fields from the source documents."""
    srcs = brief["answers"].get("sources") or detect_sources(root)
    if srcs and not answered(brief, "sources"):
        brief["answers"]["sources"] = srcs
        brief["sources_of"]["sources"] = "derived"
    texts = []
    for p in srcs[:6]:
        t = read_text(_resolve(root, p))
        if t:
            texts.append(t)
    if not texts:
        return brief, []
    filled = []
    if not answered(brief, "title"):
        t = derive_title(texts)
        if t:
            brief["answers"]["title"] = t
            brief["sources_of"]["title"] = "derived"
            filled.append("title")
    if not answered(brief, "research_question"):
        q = derive_rq(texts)
        if q:
            brief["answers"]["research_question"] = q
            brief["sources_of"]["research_question"] = "derived"
            filled.append("research_question")
    if not answered(brief, "key_points"):
        kp = derive_key_points(texts)
        if kp:
            brief["answers"]["key_points"] = kp
            brief["sources_of"]["key_points"] = "derived"
            filled.append("key_points")
    return brief, filled


# ------------------------------------------------------------------ commands
def cmd_questions(args, brief):
    brief["round"] += 1
    save(args.file, brief)
    todo = [f for f in FIELDS if not answered(brief, f.key)]
    if brief["round"] > 1:
        todo = [f for f in todo if f.required or f.key in ("style", "length")]
    lang = args.lang
    print(f"# 第 {brief['round']} 轮提问 / Round {brief['round']}"
          + ("" if brief["round"] < 2 else "  (last round before assumptions)"))
    print()
    for i, f in enumerate(todo, 1):
        q = f.question_zh if lang == "zh" else f.question_en
        lbl = f.zh if lang == "zh" else f.en
        print(f"{i}. **{lbl}** — {q}")
    if brief["round"] >= 2:
        print()
        print("两轮之后仍未回答的项目将自动从源材料推导，并作为「假设」列在交付说明里。"
              if lang == "zh" else
              "After two rounds, unanswered items are derived from the sources and "
              "listed as assumptions in the delivery.")
    return 0


def cmd_record(args, brief):
    key = args.key
    if key not in BY_KEY:
        print(f"unknown key {key!r}; known: {', '.join(BY_KEY)}")
        return 2
    val = args.value
    if isinstance(val, str) and val.startswith("["):
        try:
            val = json.loads(val)
        except Exception:
            pass
    brief["answers"][key] = val
    brief["sources_of"][key] = args.source
    brief["history"].append({"round": brief["round"], "key": key,
                             "source": args.source})
    save(args.file, brief)
    print(f"recorded {key} ({args.source})")
    return 0


def cmd_derive(args, brief):
    brief, filled = derive_all(brief, args.root)
    save(args.file, brief)
    srcs = brief["answers"].get("sources") or []
    if srcs and not filled:
        # distinguish "nothing left to derive" from "the sources could not be
        # read" -- the second one is a silent failure if it is not said out loud
        readable = [p for p in srcs[:6] if read_text(_resolve(args.root, p))]
        if not readable:
            print("no source could be read from " + ", ".join(srcs))
            print("  -> check the paths, then run `brief.py derive` again")
            return 1
    print("derived: " + (", ".join(filled) if filled else "nothing new"))
    return 0


def cmd_defaults(args, brief):
    if brief["round"] < 2:
        print(f"refusing to assume: only {brief['round']} round(s) of questions so "
              f"far. Ask at least twice before deciding for the human.")
        return 1
    brief, filled = derive_all(brief, args.root)
    for f in FIELDS:
        if not answered(brief, f.key) and f.default is not None:
            brief["answers"][f.key] = f.default
            brief["sources_of"][f.key] = "default"
            filled.append(f.key)
    save(args.file, brief)
    still = missing(brief)
    print("filled: " + (", ".join(filled) if filled else "nothing"))
    if still:
        print("still missing and NOT derivable: " + ", ".join(f.key for f in still))
        print("  -> write these yourself, or say so in the delivery.")
    return 0


def cmd_status(args, brief):
    miss = missing(brief)
    print(f"brief file : {args.file}")
    print(f"round      : {brief['round']}")
    print()
    for f in FIELDS:
        v = brief["answers"].get(f.key)
        src = brief["sources_of"].get(f.key, "-")
        mark = "OK " if answered(brief, f.key) else ("!! " if f.required else "-- ")
        text = str(v).replace("\n", " / ") if v not in (None, "", []) else "-"
        if len(text) > 70:
            text = text[:70] + "..."
        print(f"{mark}{f.key:20} [{src:8}] {text}")
    print()
    if miss:
        print(f"MISSING required: {', '.join(f.key for f in miss)}")
        if brief["round"] == 0:
            print("  -> run `brief.py questions` and ask FIRST.")
        elif brief["round"] == 1:
            print("  -> ask once more (round 2), then `brief.py defaults`.")
        else:
            print("  -> run `brief.py defaults` (derives from sources) or `brief.py derive`.")
    else:
        print("brief is complete -- ready to build.")
    return 0


def cmd_check(args, brief):
    miss = missing(brief)
    if miss:
        print("BRIEF INCOMPLETE -- do not build the deck yet.")
        print("missing: " + ", ".join(f.key for f in miss))
        print(f"rounds asked: {brief['round']}")
        if brief["round"] < 2:
            print("next: brief.py questions  (then ask the human)")
        else:
            print("next: brief.py defaults  (derive the rest from the sources)")
        return 1
    print("BRIEF COMPLETE -- ready to build.")
    for f in REQUIRED:
        print(f"  {f.key:20} [{brief['sources_of'].get(f.key, 'given')}]")
    return 0


def cmd_summary(args, brief):
    print("# Deck brief\n")
    for f in FIELDS:
        v = brief["answers"].get(f.key)
        if v in (None, "", []):
            continue
        src = brief["sources_of"].get(f.key, "given")
        if isinstance(v, list):
            v = "\n".join(f"- {x}" for x in v)
        print(f"**{f.zh}** ({f.key}, source: {src})\n")
        print(v)
        print()
    assumed = [f.key for f in FIELDS
               if brief["sources_of"].get(f.key) in ("default", "derived")]
    if assumed:
        print("## Assumptions to state in the delivery\n")
        for k in assumed:
            print(f"- {k}: {brief['answers'].get(k)}")
        print()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=BRIEF_NAME, help="brief file path")
    ap.add_argument("--root", default=".", help="where to look for sources")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("questions"); p.add_argument("--lang", default="zh", choices=["zh", "en"])
    p.set_defaults(fn=cmd_questions)
    p = sub.add_parser("record")
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True)
    p.add_argument("--source", default="given", choices=["given", "derived", "default"])
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("derive"); p.set_defaults(fn=cmd_derive)
    p = sub.add_parser("defaults"); p.set_defaults(fn=cmd_defaults)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("check"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("summary"); p.set_defaults(fn=cmd_summary)

    args = ap.parse_args(argv)
    brief = load(args.file)
    return args.fn(args, brief)


if __name__ == "__main__":
    raise SystemExit(main())
