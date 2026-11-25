# Intake protocol

The deck is the deliverable; the brief is what makes the deliverable correct.
This file is the protocol for getting a brief that is good enough to build on.

## Why a gate at all

A deck is a *selection*: which claims, which passages, which order, which
length, which register. Every one of those is a guess unless the human made
it. Guessing produces a deck that is 80% right and needs a full rewrite to fix
the other 20% — and the human usually cannot tell which 20% until they have
read it.

So: ask, before building. The gate exists so that "I asked" is a fact about
the process rather than a memory.

## The fields

| key | meaning | required | default |
|---|---|---|---|
| `title` | 主题 / central claim, in one sentence | **yes** | derived |
| `key_points` | the 3–5 points that must land, in priority order | **yes** | derived |
| `research_question` | the question the material answers | **yes** | derived |
| `sources` | the evidence base (PDF / DOCX paths) | **yes** | auto-detected |
| `style` | visual style key | no | `paper-warm` |
| `length` | target slide count | no | 20 |
| `audience` | who reads it | no | 本领域研究生与研究者 |
| `occasion` | where it is presented | no | 组会 / 学术报告 |
| `language` | zh / en / bilingual | no | follow the source |
| `citation_style` | reference format | no | APA 7th, full entries |

## Asking

**Read first, then ask — and ask in one batch, in the human's language.** A
questionnaire split across four messages is a questionnaire that gets
abandoned after the second one. Anything the sources already answer does not
need a question; it needs a confirmation.

```bash
python3 scripts/brief.py derive            # fill what the sources answer
python3 scripts/brief.py questions --lang zh
```

The script prints the questions still unanswered and increments the round.
Round 1 prints everything; round 2 prints only what is still open (the
required fields plus `style` and `length`).

When you present the questions, keep these three rules:

1. **Say what each answer changes.** "大概多少页（默认 20；页数多了我会合并而不是加页）" tells the human the default is safe to ignore.
2. **Offer the default inline.** A human who has no opinion should be able to answer "默认就行".
3. **Do not ask what you can read.** If the source document already states the research question, do not ask — derive it, then put it back as a confirmation: "材料里的研究问题是「……」，对吗？"

## The research question

This is the field that most often gets faked, so it gets its own rules.

### Judge what you were given

| What the human said | What it is | What to do |
|---|---|---|
| An explicit question in the source's own words | the research question | use it verbatim, mark `derived` |
| A topic ("城市更新中的功能主义") | a topic, not a question | derive the question from the source; confirm it back to them |
| A claim ("功能主义无法解释语篇层的偏移") | a finding, not a question | derive the question that the finding answers |
| A vague phrase ("我想讲讲我的研究") | neither | ask again (round 2), then derive from what they gave you |

**A topic is not a research question.** A research question asks something the
material answers: what is compared, against what, and what would count as an
answer. If you cannot state the question as a question, you have a topic — say
so and derive the question.

### Deriving one from a source

Read in this order and stop at the first hit:

1. **The abstract** — often states the question outright.
2. **The introduction's last paragraph** — the classic "本文试图回答……".
3. **The conclusion's first sentence** — often restates what was answered.
4. **The title plus the method** — combine them: "在〈X〉的 Y 分析框架下，Z 是否……"

`brief.py derive` automates 1–3 with a pattern set. It is a **draft**: read
the result, fix it if the source states the question more precisely, then record
it with `--source derived`.

If nothing in the source states a question, write one from what the material
actually does, and mark it `derived`. A research question you synthesised from
the source's own argument is defensible; one you invented from the topic alone
is not.

### After two rounds

Round 2 is the last chance to ask. After it:

- Derive whatever the sources support.
- Mark it `derived` (evidence-based) or `default` (a working assumption).
- **State every one of them in the delivery.** A list of assumptions is cheap
  to read and cheap to correct; a wrong deck is not.

Never invent a research question to fill the gap. If the sources genuinely do
not support one, write the brief with the question as "未明确" and say so —
an honest gap is more useful than a fabricated question.

## Recording

```bash
python3 scripts/brief.py record --key title --value "城市更新的三种解释框架" --source given
python3 scripts/brief.py record --key key_points --value '["偏移可分层定位","证据强度随路径而变"]' --source given
python3 scripts/brief.py status
```

`--source` is one of:

- `given` — the human said it.
- `derived` — read out of the source documents.
- `default` — a documented working assumption, used only after two rounds.

`brief.py summary` prints the brief as markdown, including an **Assumptions**
section listing every `derived` and `default` field. Paste that section into
the delivery message.

## The gate

```bash
python3 scripts/brief.py check
```

Exit 0 means every required field is filled. Exit 1 prints what is missing and
what to do next. **Do not start building while this fails.** The check is
cheap; a rewrite is not.

## Sourcing

If the human named files, use them. If they named none, `brief.py derive`
auto-detects PDFs and DOCX files next to the work. Do not silently build from
the wrong corpus: if more than one candidate document is found and the human
has not said which, that is a question for round 1.
