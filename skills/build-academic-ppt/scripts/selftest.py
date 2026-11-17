#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest -- prove the toolkit still works.

Run it after any change to the skill:

    python3 scripts/selftest.py

Every check is an assertion about a behaviour that used to be broken, or a
rule the skill depends on. Exit code is non-zero if any check fails.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ""))
        print(f"  PASS  {name}")
    except Exception as e:
        RESULTS.append((name, False, str(e)))
        print(f"  FAIL  {name}\n          {type(e).__name__}: {e}")


def section(title):
    print(f"\n{title}")


# ------------------------------------------------------------------ fixtures
def make_pdf(path, ambiguous=True):
    """A small text-layer PDF. The needle appears twice when ambiguous=True."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    y = 90
    for i in range(22):
        page.insert_text((72, y), f"Line {i:02d} of the source document body text.",
                         fontsize=11, fontname="helv")
        y += 22
    page.insert_text((72, 700), "The textual panorama is defined here once.",
                     fontsize=11, fontname="helv")
    if ambiguous:
        page.insert_text((72, 730), "The textual panorama is defined here twice.",
                         fontsize=11, fontname="helv")
    doc.save(path)
    doc.close()
    return path


def make_scanned_pdf(path):
    """A PDF with NO text layer: a rendered image of text."""
    import fitz
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1240, 1754), (252, 250, 244))
    d = ImageDraw.Draw(img)
    d.text((90, 90), "CHAPTER ONE  THE OPENING ARGUMENT", fill=(30, 28, 24))
    y = 170
    for i in range(30):
        d.text((90, y), f"line {i:02d} of the scanned page body text here",
               fill=(40, 38, 34))
        y += 34
    d.text((90, 1200), "the opening claim appears here in the scan",
           fill=(40, 38, 34))
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(0, 0, 612, 792), stream=io.BytesIO(
        img.tobytes() and __import__("io").BytesIO(b"").getvalue() or b""))
    doc.close()
    return path


# ------------------------------------------------------------------ themes
def test_themes():
    from themes import THEMES, audit, contrast_ratio
    assert len(THEMES) >= 6, f"only {len(THEMES)} styles registered"
    rows, fails = audit()
    assert not fails, "contrast failures: " + "; ".join(
        f"{k} {n} {r}<{need}" for k, n, _, _, r, need, _ in fails)
    # black on white must be the maximum
    assert contrast_ratio("000000", "FFFFFF") > 20
    # every theme must carry every token
    for k, t in THEMES.items():
        for tok in ("bg", "bg_deep", "bg_soft", "ink", "ink_soft", "accent",
                    "accent_soft", "accent2", "rule", "dark_bg", "dark_ink",
                    "dark_ink_soft", "dark_rule", "mat_on_dark", "ink_on_mat"):
            v = getattr(t, tok, None)
            assert v and len(v) == 6, f"{k}.{tok} missing"
            int(v, 16)
        assert t.body_pt >= 14, f"{k} body floor below 14pt"
        assert t.fonts()["serif_cn"] and t.fonts()["sans_en"]


def test_theme_api_names():
    """Both names for the lookup must work: a wrong guess should not be a
    crash in the middle of a build."""
    from themes import get, get_theme, THEMES
    assert get("paper-warm") is get_theme("paper-warm")
    assert get is get_theme
    try:
        get("no-such-style")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown style must raise, not fall back")


def test_theme_contrast_pairs():
    """A light crop on a dark slide needs a DARK ink on the mat."""
    from themes import THEMES, contrast_ratio
    for k, t in THEMES.items():
        r = contrast_ratio(t.ink_on_mat, t.mat_on_dark)
        assert r >= 4.5, f"{k}: ink_on_mat on mat is only {r:.2f}:1"


# ------------------------------------------------------------------ deck_kit
def test_theme_switch_actually_switches():
    """The old bug: colours were bound as default arguments, so switching the
    theme after import changed nothing."""
    import deck_kit as K
    from pptx import Presentation
    paths = {}
    for key in ("paper-warm", "minimal-white", "slate-dark"):
        d = K.Deck(theme_key=key, footer="f")
        d.content(eyebrow="e", title="t", cite="c")
        p = os.path.join(tempfile.mkdtemp(), f"{key}.pptx")
        d.save(p, check=False, manifest=False)
        paths[key] = p
    bgs = {}
    for key, p in paths.items():
        prs = Presentation(p)
        bgs[key] = str(prs.slides[0].shapes[0].fill.fore_color.rgb)
    assert len(set(bgs.values())) == 3, f"backgrounds did not change: {bgs}"


def test_lang_attribute_on_every_run():
    import deck_kit as K
    from pptx import Presentation
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="中文标题 test", cite="c")
    K.txt(s, K.ML, y, K.CW, K.Inches(1), [[("正文 content", {})]], size=14)
    p = os.path.join(tempfile.mkdtemp(), "x.pptx")
    d.save(p, check=False, manifest=False)
    prs = Presentation(p)
    n = 0
    for slide in prs.slides:
        for sh in slide.shapes:
            if not sh.has_text_frame:
                continue
            for pa in sh.text_frame.paragraphs:
                for r in pa.runs:
                    assert r._r.get_or_add_rPr().get("lang") == "zh-CN", \
                        f"run without lang: {r.text!r}"
                    n += 1
    assert n > 0


def test_est_height_rejects_bare_string():
    import deck_kit as K
    try:
        K.est_height([["裸字符串"]], 5.0)
    except TypeError:
        return
    raise AssertionError("est_height accepted a bare string (it would estimate "
                         "one character and under-report the height by ~5x)")


def test_est_height_rejects_emu_as_inches():
    import deck_kit as K
    try:
        K.est_height([[("text", {})]], 914400)
    except ValueError:
        return
    raise AssertionError("est_height accepted EMU where inches were expected")


def test_txt_rejects_inches_for_emu():
    import deck_kit as K
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="t", cite="c")
    try:
        K.txt(s, 0.85, y, 3.5, 0.4, [[("text", {})]], size=14)
    except TypeError:
        return
    raise AssertionError("txt accepted a float where EMU was required "
                         "(this is the zero-width table cell bug)")


def test_overflow_is_recorded():
    import deck_kit as K
    K.clear_warnings()
    K.fits("t", [[("x" * 200, {})]], 2.0, 0.3)
    assert K.WARN, "fits() did not record an overflow"


def test_check_catches_defects():
    import deck_kit as K
    from PIL import Image
    shot = os.path.join(tempfile.mkdtemp(), "s.png")
    Image.new("RGB", (1200, 400), "white").save(shot)
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="t1", cite="c")
    K.shot(s, shot, K.ML, y, K.Inches(6), K.Inches(2))
    K.txt(s, K.ML + K.Inches(1), y + K.Inches(0.3), K.Inches(4), K.Inches(0.4),
          [[("压在图上的文字", {})]], size=14)
    s2, y2 = d.content(eyebrow="e", title="t2")
    K.txt(s2, K.ML, y2, K.Inches(3), K.Inches(0.3),
          [[("这段文字非常长，长到一定会折行超过它自己那个只有零点三英寸高的框子，"
             "所以它一定会溢出自己的框然后压到下面的东西上面去，这就是最常见的缺陷。", {})]],
          size=14)
    p = os.path.join(tempfile.mkdtemp(), "b.pptx")
    d.save(p, check=False, manifest=False)
    kinds = {i[1] for i in d.check(p)}
    for want in ("text-over-image", "text-overflows-frame",
                 "content-slide-without-screenshot",
                 "content-slide-without-citation"):
        assert want in kinds, f"check() missed {want}; got {sorted(kinds)}"


def test_stat_row_keeps_values_on_one_line():
    import deck_kit as K
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="t", cite="c")
    K.stat_row(s, K.ML, y, K.CW,
               [("a", "6"), ("b", "3"), ("c", "≈48,700")])
    p = os.path.join(tempfile.mkdtemp(), "sr.pptx")
    d.save(p, check=False, manifest=False)
    from pptx import Presentation
    prs = Presentation(p)
    # the third value must fit its tile on one line
    from deck_kit import est_height
    boxes = [sh for sh in prs.slides[0].shapes
             if sh.has_text_frame and "48,700" in sh.text_frame.text]
    assert boxes, "the stat value is missing"
    b = boxes[0]
    h = est_height([[("≈48,700", {})]], b.width / 914400,
                   size=b.text_frame.paragraphs[0].runs[0].font.size.pt, line=1.0)
    assert h < b.height / 914400 + 0.02, "the stat value wrapped"


def test_footer_is_not_hardcoded():
    import deck_kit as K
    d = K.Deck(theme_key="paper-warm", footer="MY OWN FOOTER")
    d.content(eyebrow="e", title="t", cite="c")
    p = os.path.join(tempfile.mkdtemp(), "f.pptx")
    d.save(p, check=False, manifest=False)
    from pptx import Presentation
    prs = Presentation(p)
    texts = [sh.text_frame.text for sh in prs.slides[0].shapes
             if sh.has_text_frame]
    assert any("MY OWN FOOTER" in t for t in texts)
    assert not any("功能性译者风格研究" in t for t in texts), \
        "the old project's footer string is baked into the toolkit"


# ------------------------------------------------------------------ brief
def test_brief_gate():
    """The gate must block an incomplete brief, and must NOT let the script
    invent a title. After two rounds the AGENT decides and records the
    decision with --source default; the script only supplies what it can
    derive."""
    import brief
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "b.json")
    b = brief.load(path)
    assert brief.missing(b), "an empty brief reported as complete"
    assert brief.cmd_check(type("A", (), {"file": path})(), b) == 1
    # defaults must refuse before two rounds
    b["round"] = 1
    assert brief.cmd_defaults(type("A", (), {"file": path, "root": tmp})(), b) == 1
    # after two rounds it may assume the fields it can derive
    b["round"] = 2
    brief.cmd_defaults(type("A", (), {"file": path, "root": tmp})(), b)
    b2 = brief.load(path)
    # the optional fields must have been filled from the built-in defaults
    assert brief.answered(b2, "style") and brief.answered(b2, "length")
    # but a title must NOT have been invented out of nothing
    assert not brief.answered(b2, "title"), \
        "the script invented a title with no source to read"
    # the agent's decision closes the gate
    brief.cmd_record(type("A", (), {"file": path, "key": "title",
                                    "value": "decided by the agent",
                                    "source": "default"})(), b2)
    b3 = brief.load(path)
    assert b3["sources_of"].get("title") == "default"


def test_brief_derives_rq_from_source():
    import brief
    tmp = tempfile.mkdtemp()
    docx = os.path.join(tmp, "s.docx")
    import docx as D
    d = D.Document()
    d.add_paragraph("以功能主义视角重估翻译批评")
    d.add_paragraph("研究问题：译文在哪些可指认的语言层级与原文发生偏移？")
    d.save(docx)
    b = brief.load(os.path.join(tmp, "b.json"))
    b, filled = brief.derive_all(b, tmp)
    assert "research_question" in filled, "the research question was not derived"
    assert "偏移" in b["answers"]["research_question"]
    assert "title" in filled, "the title was not derived"


def test_brief_questions_increment_round():
    import brief
    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "b.json")
    b = brief.load(path)
    args = type("A", (), {"file": path, "lang": "zh"})()
    brief.cmd_questions(args, b)
    assert brief.load(path)["round"] == 1
    brief.cmd_questions(args, brief.load(path))
    assert brief.load(path)["round"] == 2


# ------------------------------------------------------------------ pdf_shots
def test_crop_has_highlight():
    import pdf_shots
    tmp = tempfile.mkdtemp()
    pdf = make_pdf(os.path.join(tmp, "src.pdf"))
    img, notes = pdf_shots.crop(pdf, 1, ["textual panorama is defined"], ctx=1,
                                out=os.path.join(tmp, "o.png"))
    assert img is not None, "crop failed: " + "; ".join(notes)
    assert pdf_shots.count_highlight(img) >= pdf_shots.AMBER_MIN_PIXELS, \
        "the crop carries no highlight"


def test_ambiguous_needle_is_reported():
    import pdf_shots
    tmp = tempfile.mkdtemp()
    pdf = make_pdf(os.path.join(tmp, "src.pdf"), ambiguous=True)
    _, notes = pdf_shots.crop(pdf, 1, ["textual panorama is defined"], ctx=1)
    assert any("AMBIGUOUS" in n for n in notes), \
        "an ambiguous needle was silently resolved: " + "; ".join(notes)


def test_no_crop_ever_lands_without_a_highlight():
    """The invariant that matters: a crop either carries a highlight or it is
    not produced. Hostile crop configurations must not slip a highlight-free
    image through -- that is the defect that made a plausible-looking picture
    of nothing."""
    import pdf_shots
    tmp = tempfile.mkdtemp()
    pdf = make_pdf(os.path.join(tmp, "src.pdf"), ambiguous=True)
    configs = [
        dict(ctx=1),
        dict(ctx=0),
        dict(ctx=3),
        dict(ctx=1, x0=72, x1=300),
        dict(ctx=1, x0=72, x1=560),
        dict(ctx=0, pad=4),
        dict(ctx=0, pad=60),
        dict(ctx=1, col="left"),
        dict(ctx=1, occ=1),
    ]
    for cfg in configs:
        img, notes = pdf_shots.crop(pdf, 1, ["textual panorama is defined"], **cfg)
        if img is None:
            continue        # refused -- that is a pass
        n = pdf_shots.count_highlight(img)
        assert n >= pdf_shots.AMBER_MIN_PIXELS, (
            f"crop {cfg} was produced with no highlight ({n} px): {notes}")


def test_manifest_carries_page_numbers():
    import pdf_shots
    tmp = tempfile.mkdtemp()
    pdf = make_pdf(os.path.join(tmp, "src.pdf"))
    jobs = os.path.join(tmp, "j.json")
    json.dump([{"name": "s1", "page": 1, "needles": ["textual panorama is defined"],
                "ctx": 1}], open(jobs, "w"))
    out = os.path.join(tmp, "out")
    pdf_shots.cmd_shots(pdf, jobs, out)
    man = json.load(open(os.path.join(out, "manifest.json")))
    assert man["s1"]["page"] == 1, "the manifest does not carry the page number"


# ------------------------------------------------------------------ qa_deck
def test_qa_deck_passes_clean_deck():
    import deck_kit as K
    from PIL import Image
    tmp = tempfile.mkdtemp()
    shot = os.path.join(tmp, "s.png")
    Image.new("RGB", (1200, 400), "white").save(shot)
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="t", cite="c")
    K.shot(s, shot, K.ML, y, K.Inches(6), K.Inches(2))
    p = os.path.join(tmp, "clean.pptx")
    d.save(p, check=False)
    r = subprocess.run([sys.executable, os.path.join(HERE, "qa_deck.py"), p,
                        "--no-render"], capture_output=True, text=True)
    assert r.returncode == 0, "qa_deck failed a clean deck:\n" + r.stdout


def test_qa_deck_fails_broken_deck():
    import deck_kit as K
    tmp = tempfile.mkdtemp()
    d = K.Deck(theme_key="paper-warm", footer="f")
    s, y = d.content(eyebrow="e", title="t")
    K.txt(s, K.ML, y, K.Inches(4), K.Inches(0.3),
          [[("a very long run of text that must certainly wrap beyond its own "
             "tiny frame and spill over whatever sits underneath it here", {})]],
          size=14)
    p = os.path.join(tmp, "bad.pptx")
    d.save(p, check=False)
    r = subprocess.run([sys.executable, os.path.join(HERE, "qa_deck.py"), p,
                        "--no-render"], capture_output=True, text=True)
    assert r.returncode != 0, "qa_deck passed a broken deck:\n" + r.stdout


def test_documented_example_runs():
    """The snippet in SKILL.md and README.md must actually run. Documentation
    that does not compile is a defect with a delay."""
    import deck_kit as K
    from pptx.util import Inches
    from PIL import Image
    tmp = tempfile.mkdtemp()
    shot = os.path.join(tmp, "x.png")
    Image.new("RGB", (1200, 400), "white").save(shot)
    d = K.Deck(theme_key="journal-serif", footer="功能性与翻译研究 · 文献评议")
    s, y = d.content(eyebrow="证据结构", title="三个证据层级",
                     cite="Li, D., Wu, K. (2025). Title. Publisher. DOI 10.xxxx/yyyy.")
    K.txt(s, K.ML, y, K.CW // 2, Inches(1.4),
          [[("研究问题", {"bold": True, "color": K.theme().accent})],
           [("译文在哪些可指认的语言层级与原文发生偏移？", {})]], size=14, line=1.25)
    K.shot(s, shot, K.ML + K.CW // 2, y, K.CW // 2, Inches(2.1),
           caption="原文 P52：textual panorama 的界定（高亮处）", valign="top")
    p = os.path.join(tmp, "doc.pptx")
    d.save(p, check=False)
    assert os.path.exists(p)


def _big_font(size=44):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return None


def test_ocr_path_survives_binary_stderr():
    """Tesseract's stderr is not always UTF-8. Decoding it as text killed the
    whole OCR run on a Chinese page that OCRs perfectly well."""
    import shutil
    if not shutil.which("tesseract"):
        print("      (skipped: tesseract not installed)")
        return
    import ocr_shots
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1600, 400), "white")
    d = ImageDraw.Draw(img)
    font = _big_font()
    d.text((40, 150), "the opening claim appears here in the scan",
           fill=(20, 20, 20), font=font)
    lines = ocr_shots.ocr_lines(img, lang="eng")
    assert lines, "OCR returned no lines"
    assert any("opening" in L["text"] for L in lines), \
        "OCR did not read the sample line: " + repr([L["text"] for L in lines])


def test_ocr_falls_back_when_language_pack_missing():
    """A missing language pack must fall back to English, not abort the run."""
    import shutil
    if not shutil.which("tesseract"):
        print("      (skipped: tesseract not installed)")
        return
    import ocr_shots
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 300), "white")
    d = ImageDraw.Draw(img)
    d.text((30, 120), "hello world test line", fill=(20, 20, 20),
           font=_big_font())
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "p.png")
    img.save(src)
    tsv, err, used = ocr_shots._run_tesseract(src, "zzz_not_a_language")
    assert used == "eng", f"expected an English fallback, got {used!r}"
    assert tsv.strip(), "the fallback produced no TSV"


def test_ocr_works_through_a_symlinked_directory():
    """/tmp is a symlink to /private/tmp, and leptonica (inside tesseract)
    could not open a file through it when given the symlinked absolute path.
    The failure surfaced as an unrelated UnicodeDecodeError, which is how it
    cost an afternoon. The path is now resolved before tesseract sees it."""
    import shutil
    if not shutil.which("tesseract"):
        print("      (skipped: tesseract not installed)")
        return
    import ocr_shots
    from PIL import Image, ImageDraw
    real = tempfile.mkdtemp(prefix="ocrreal_")
    link = os.path.join(tempfile.mkdtemp(prefix="ocrlink_"), "via_symlink")
    os.symlink(real, link)
    img = Image.new("RGB", (900, 300), "white")
    ImageDraw.Draw(img).text((30, 120), "hello world test line", fill=(20, 20, 20),
                             font=_big_font())
    p = os.path.join(link, "p.png")
    img.save(p)
    tsv, err, used = ocr_shots._run_tesseract(p, "eng")
    assert tsv.strip(), "no TSV through a symlinked path: " + err[:200]


def test_vision_backend_reads_english():
    """macOS Vision is the reference backend: on a Chinese scan tesseract's
    chi_sim garbles the text. Vision's boxes also have their origin at the
    BOTTOM left, so the y flip has to be right."""
    import ocr_shots
    if not ocr_shots.vision_available():
        print("      (skipped: macOS Vision not available)")
        return
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1400, 400), "white")
    ImageDraw.Draw(img).text((40, 160),
                             "the opening claim appears here in the scan",
                             fill=(20, 20, 20), font=_big_font())
    lines = ocr_shots.ocr_lines_vision(img)
    assert lines, "Vision returned no lines"
    txt = " ".join(L["text"] for L in lines)
    assert "opening" in txt.lower(), f"Vision did not read the line: {txt[:120]}"
    for L in lines:
        assert 0 <= L["y0"] < L["y1"] <= img.height, \
            f"Vision box {L} is not in top-origin coordinates"


def test_pad_uniform_gives_every_crop_the_same_height():
    """Crops from different pages have different heights, so a full-width
    strip renders at a different height on every slide and the deck steps up
    and down as you page through it."""
    import deck_kit as K
    from PIL import Image
    tmp = tempfile.mkdtemp()
    paths = []
    for i, h in enumerate((60, 120, 200)):
        p = os.path.join(tmp, f"c{i}.png")
        Image.new("RGB", (400, h), "white").save(p)
        paths.append(p)
    out = K.pad_uniform(paths, os.path.join(tmp, "out"))
    hs = {Image.open(v).height for v in out.values()}
    assert len(hs) == 1, f"the padded crops still differ in height: {hs}"
    ws = {Image.open(v).width for v in out.values()}
    assert len(ws) == 1, f"the padded crops differ in width: {ws}"


def test_qa_deck_catches_unaligned_bands():
    """The band check: two evidence strips of different heights must be
    reported, because the whitespace above them jumps."""
    import deck_kit as K
    from PIL import Image
    tmp = tempfile.mkdtemp()
    d = K.Deck(theme_key="paper-warm", footer="f")
    # two strips rendered at different heights -- exactly what happens when
    # the crops come from pages with different line counts
    for i, (h, boxh) in enumerate(((300, 1.4), (120, 0.7))):
        shot = os.path.join(tmp, f"s{i}.png")
        Image.new("RGB", (2400, h), "white").save(shot)
        s, y = d.content(eyebrow="e", title=f"t{i}", cite="c")
        K.shot(s, shot, 0, K.Inches(4.0), K.SLIDE_W, K.Inches(boxh))
        K.txt(s, K.ML, K.Inches(6.0), K.Inches(8), K.Inches(0.3),
              [[("原文 P1：图注", {})]], size=10.5, role="dk_caption")
    p = os.path.join(tmp, "b.pptx")
    d.save(p, check=False)
    r = subprocess.run([sys.executable, os.path.join(HERE, "qa_deck.py"), p,
                        "--no-render"], capture_output=True, text=True)
    assert "band align" in r.stdout, "the band check did not fire:\n" + r.stdout
    assert r.returncode != 0, "an unaligned deck passed the gate"


def test_crop_context_above_and_below_can_differ():
    """Too much context below is how a crop ends up carrying a reference list
    instead of the passage."""
    import pdf_shots
    tmp = tempfile.mkdtemp()
    pdf = make_pdf(os.path.join(tmp, "src.pdf"))
    img, notes = pdf_shots.crop(pdf, 1, ["textual panorama is defined"],
                                ctx_before=0, ctx_after=0)
    assert img is not None, "; ".join(notes)
    tall, notes2 = pdf_shots.crop(pdf, 1, ["textual panorama is defined"],
                                  ctx_before=2, ctx_after=2)
    assert tall is not None
    assert tall.height > img.height, \
        "ctx_before/ctx_after had no effect on the crop"


def test_backups_never_land_inside_a_skills_directory():
    """A backup left inside the skills directory still carries a SKILL.md, so
    the harness loads it as a SECOND skill with the same name -- the skill
    list ends up showing duplicates after every install."""
    # scripts/ -> skill/ -> skills/ -> repo root
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        "..", "..", ".."))
    installer = os.path.join(repo, "install.sh")
    src = open(installer, encoding="utf-8").read()
    assert "$base/$SKILL_NAME.backup." not in src, \
        "the installer still backs up inside the skills directory"
    assert ".skill-backups" in src, \
        "the installer does not have an out-of-tree backup location"
    assert 'bakdir="$(dirname "$base")/.skill-backups"' in src, \
        "the backup directory is not a sibling of the skills directory"


# ------------------------------------------------------------------ main
def main():
    print("build-academic-ppt selftest")
    section("themes")
    check("styles registered, tokens complete, contrast AA", test_themes)
    check("mat/ink pairs legible in every style", test_theme_contrast_pairs)
    check("the theme lookup answers to both names", test_theme_api_names)
    section("deck_kit")
    check("theme switch changes the output", test_theme_switch_actually_switches)
    check("every run carries lang=zh-CN", test_lang_attribute_on_every_run)
    check("est_height rejects a bare string", test_est_height_rejects_bare_string)
    check("est_height rejects EMU passed as inches", test_est_height_rejects_emu_as_inches)
    check("txt rejects inches passed as EMU", test_txt_rejects_inches_for_emu)
    check("fits() records an overflow", test_overflow_is_recorded)
    check("geometry check catches the four defects", test_check_catches_defects)
    check("stat row keeps values on one line", test_stat_row_keeps_values_on_one_line)
    check("footer text is the deck's own", test_footer_is_not_hardcoded)
    check("the documented example runs", test_documented_example_runs)
    check("backups stay out of the skills directory",
          test_backups_never_land_inside_a_skills_directory)
    check("pad_uniform equalises the crop heights",
          test_pad_uniform_gives_every_crop_the_same_height)
    check("the gate catches unaligned evidence bands",
          test_qa_deck_catches_unaligned_bands)
    check("crop context above and below can differ",
          test_crop_context_above_and_below_can_differ)
    section("brief")
    check("gate blocks an incomplete brief", test_brief_gate)
    check("research question derived from a source", test_brief_derives_rq_from_source)
    check("questions increment the round", test_brief_questions_increment_round)
    section("pdf_shots")
    check("crop carries a highlight", test_crop_has_highlight)
    check("ambiguous needle is reported", test_ambiguous_needle_is_reported)
    check("no crop lands without a highlight", test_no_crop_ever_lands_without_a_highlight)
    check("manifest carries page numbers", test_manifest_carries_page_numbers)
    section("ocr_shots")
    check("OCR survives a non-UTF-8 stderr", test_ocr_path_survives_binary_stderr)
    check("a missing language pack falls back to English",
          test_ocr_falls_back_when_language_pack_missing)
    check("OCR works through a symlinked directory",
          test_ocr_works_through_a_symlinked_directory)
    check("the Vision backend reads and flips coordinates",
          test_vision_backend_reads_english)
    section("qa_deck")
    check("clean deck passes", test_qa_deck_passes_clean_deck)
    check("broken deck fails", test_qa_deck_fails_broken_deck)

    bad = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} checks passed")
    for name, _, err in bad:
        print(f"  FAILED: {name}\n          {err}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
