# Visual styles

Seven styles ship with the skill. Each is a complete system — surfaces, two
accents, hairline colour, the dark-slide variant, the typeface pairing, the
type scale — not a colour swap. They are registered in `scripts/themes.py`, and
every one of them has been contrast-audited and rendered as a preview.

## Choosing

**Ask with the previews, not with names.** "Which style?" is unanswerable from
a list of names. Show `assets/previews/*.jpg` (one per style) or the contact
sheet `assets/previews/all-styles.jpg`.

If the human has already described a look in their own words, map it yourself
and tell them which style you picked — do not make them translate a feeling
into a key.

| they say | you pick |
|---|---|
| 简洁、白底、干净 | `minimal-white` |
| 像论文、正式、衬线 | `journal-serif` |
| 暖一点、书卷气、复古 | `kraft` or `paper-warm` |
| 深色、投影、演讲 | `slate-dark` |
| 理性、技术、流程、蓝色 | `blueprint` |
| 留白多、安静、细线 | `ink-wash` |
| 没说 / 无所谓 | `paper-warm`（after two rounds） |

## The seven

### `paper-warm` — 暖纸朱砂 / Warm Paper & Cinnabar

Warm paper `F6F4EF`, near-black ink `1A1D23`, cinnabar `A63D2B` and ochre
`8A6D1F`. Serif titles, sans body. The default, and the safest: the warm mat
around a crop forgives a low-contrast source, and the cinnabar reads as
scholarly without shouting.

*Fits:* translation studies, literary criticism, close reading, any humanities
audience. *Fails:* clinical or regulatory audiences — the warmth reads
informal.

### `minimal-white` — 极简白 / Minimal White

Pure white `FFFFFF`, one signal blue `0057B8`, hairline rules at 0.5pt, no
panels, no fills. Maximum whitespace.

*Fits:* a talk where the deck is a backdrop, not a document; a pitch to people
who read fast. *Fails:* decks that need panels to organise dense comparative
material — without fills, eight parallel items become a wall.

### `journal-serif` — 学术期刊 / Journal Serif

Times New Roman on white with a single dark red `990F0F` and a navy second
series `1F3A5F`. Titles sit at 24pt so a long Chinese title still fits; the
citation bar is the densest element in the deck.

*Fits:* seminars, methods talks, audiences that read the citations. *Fails:*
projected talks at a distance — Times at 14pt is thin on a bad projector.

### `slate-dark` — 冷灰深色 / Slate Dark

Deep slate `1E252C` slides, cyan `4EA8DE` and amber `E8A33D` accents, crop
mats kept light so a screenshot still reads as paper.

*Fits:* projection in a bright room; a deck with heavy imagery. *Fails:*
printed handouts — a dark deck costs a lot of ink and reads badly on paper.
**Give every crop a light mat and keep crops large**: a white crop on a dark
slide reads as a lit panel, and a small one turns to mush.

### `blueprint` — 蓝图理性 / Blueprint

Cool blue-grey surfaces `F4F7FA`, navy `1B5FA8` with a copper second series
`C2703D`, monospaced labels for axes, stages and IDs.

*Fits:* methods, pipelines, anything with stages, stages, stages. *Fails:*
literary material where the mono labels fight the prose.

### `kraft` — 牛皮纸 / Kraft Vellum

Recycled-kraft surfaces `E8E0D1`, rust `8C4A2F` and olive `4A6741`, mono
labels, serif titles.

*Fits:* archival work, book history, printed material, a bookish tone.
*Fails:* clinical, regulatory, or corporate audiences.

### `ink-wash` — 水墨留白 / Ink Wash

Near-white `FDFDFB`, ink black, one seal red `8C1C13`, blue-grey second
series. Very high whitespace, thin rules, quiet.

*Fits:* close reading and close analysis, where a busy slide fights the text.
*Fails:* dense comparative decks — it has no room for them.

## Structure inside a style

A style is not a licence to ignore the deck's own rules. Across all seven:

- **Two dark slides per section** (a divider and a close) so the deck breathes.
  Never all-dark: a screenshot on black is unreadable — except in
  `slate-dark`, where the slides are dark by design and the crop mat stays
  light.
- **One accent per idea.** The second accent (`accent2`) marks a *second
  series* — a second path, a second model, a contrast class. It is not
  decoration and it is not a rainbow.
- **Body text ≥ 14pt.** Every style's floor is the same; only the scale above
  the floor moves.
- **The crop mat is part of the style.** `bg_soft` on light slides,
  `mat_on_dark` on dark ones.
- **The footer is the deck's own.** `Deck(footer=...)` — never a string baked
  into the toolkit.

## Changing style later

`use_theme("minimal-white")` switches the active theme; `Deck(theme_key=…)`
sets it for one deck. Colours, sizes and typefaces resolve **at call time**, so
switching after import actually changes the output.

Rebuilding an existing deck in a new style is a **mode B** edit if the human
has touched the file — do not regenerate over their edits. If they want a
restyle, say what you will carry over (text, screenshots, citations) and what
you will drop (layout), and confirm before regenerating.
