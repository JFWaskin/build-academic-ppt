# Authoring rules

The rules that decide whether a deck is *true* and *usable*, independent of
how it looks. Each one is written as a rule plus a worked example, because
"be specific" is not actionable and "name the model, not the count" is.

## 1. Cite in full, on every content slide

Authors, year, **full title**, journal or publisher, volume and issue, DOI.
Not a short tag, not "[Smith 2024]".

> Smith, J. A., & Lee, R. (2024). Functional asymmetry in translation
> evaluation. *Journal of Translation Studies*, 18(2), 114–139.
> https://doi.org/10.1234/jts.2024.018

Cover, dividers and the closing slide are exempt — they are not making a
claim.

## 2. Every content slide carries a screenshot, and the highlight proves the slide's claim

A screenshot is evidence, not decoration. The caption names what the
highlighted passage *proves*:

> 原文 P52：textual panorama 的界定（高亮处）

Not "原文 P52" alone, and not a caption that describes the crop's position
instead of its content.

**The crop must contain the passage the slide is about.** A crop of the right
paper's *conclusion* under a slide about its *method* is wrong even though it
looks fine. Audit each screenshot against its slide text.

## 3. Body text ≥ 14pt

Captions (10.5pt), labels (12pt) and footers (9pt) may go lower. Body prose
may not.

If the content does not fit at 14pt, the fix is **more slides**, never
smaller type. When the slide count is capped, the fix is to cut the least
important claim — not to squeeze the important one.

## 4. English concepts get a Chinese gloss

`主成分分析（PCA）`, `功能性近红外光谱（fNIRS）`,
`风格多元宇宙（stylistic multiverse）`.

Gloss concepts the audience may not know. Do **not** gloss proper nouns
(Paivio, Culpeper, House) — a gloss on a name is noise.

## 5. Emphasis is bold

If something must stand out, make it **bold**. Do not use 「」, "" or any other
bracket as an emphasis device — the reader has to decode what the brackets
mean, and the deck looks like a markup export.

```python
[[("研究问题", {"bold": True, "color": theme().accent})],
 [("译文在哪些可指认的语言层级与原文发生偏移？", {})]]
```

Bold sparingly: one or two bold phrases per slide. A slide where everything is
bold has no emphasis.

## 6. No vague quantity summaries

Do not write "两套模型" or "三个步骤". The reader cannot act on a count; they
can act on the content. Name it, in parentheses:

> 本次评议覆盖两套模型（Kloss & Schmidt 的可读性模型、Barnstone 的翻译单位模型）

> 全流程分三步（语料切分 → 偏移标注 → 证据分级）

This applies to headings, slide titles, body text and captions alike.

## 7. Use the source's own wording

Wherever a passage carries the argument, quote it. Paraphrasing an academic
claim into your own words loses the terms the field uses, and loses the
quotation marks that mark it as the source's claim rather than yours.

Read the DOCX/DOC/PDF programmatically and paste the wording verbatim. Trim
if you must — do not reword.

## 8. About 20 slides, and merging beats padding

The default target is **about 20 slides**. If the material supports 40, the
deck is not 40 slides — it is 20 slides that each carry two claims. Merge
adjacent passages on the same topic; keep the section headings from the source
as the eyebrow text.

Do not pad: a slide that repeats the previous slide in different words is
worse than a missing slide.

## 9. Never assert what you cannot locate

If a quotation on a slide is not in the file you hold, flag it to the user —
do not silently keep it, and do not "fix" it by guessing what the source
probably said. A fabricated citation in an academic deck is the single
worst failure this skill can produce.

## 10. State what you assumed

Every field the human did not answer, and every quote you could not locate,
goes in the delivery message — not in a footnote on the deck. A list of
assumptions costs one line to read and one line to correct.

## 11. Language and register

Match the source. A Chinese source with English concepts gets a Chinese deck
with glossed concepts. Keep the register of the material: a close reading
reads closely, a survey reads at arm's length. Do not inflate a tight
argument into a grand claim — the deck's authority comes from the evidence.
