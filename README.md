# build-academic-ppt

Build an academic presentation deck in which **every claim is traceable to a
highlighted passage in the actual source document**. The screenshots are
evidence, not decoration.

Designed for Claude Code, and usable from any agent that can run Python.

---

## What it does

- **Asks before it builds.** A mandatory intake brief: the topic, the key
  points, the research question, the sources, the visual style, the length.
  Two rounds of questions; after that it derives the rest from the sources
  and lists every assumption.
- **Seven visual styles**, each a complete system — surfaces, two accents,
  type pairing, type scale — not a colour swap. All contrast-audited to
  WCAG AA, all rendered as previews.
- **Crops that carry their evidence.** A phrase that appears three times no
  longer resolves silently to the first occurrence; a crop whose highlight
  would fall outside the frame is refused rather than produced.
- **A mechanical gate that sees what it used to miss**: text printed on top of
  a screenshot, text escaping its own frame, crops with no highlight, slides
  missing a citation, type below the floor.
- **Two modes**: build a new deck, or edit one the human has already
  hand-edited — in which case their file is the only valid baseline.

## The seven styles

![seven styles](skills/build-academic-ppt/assets/previews/all-styles.jpg)

| key | name | reads as |
|---|---|---|
| `paper-warm` | 暖纸朱砂 / Warm Paper & Cinnabar | a printed monograph |
| `minimal-white` | 极简白 / Minimal White | content-only, maximum whitespace |
| `journal-serif` | 学术期刊 / Journal Serif | a journal article that happens to be slides |
| `slate-dark` | 冷灰深色 / Slate Dark | a talk in a bright room |
| `blueprint` | 蓝图理性 / Blueprint | a technical document |
| `kraft` | 牛皮纸 / Kraft Vellum | archival, bookish |
| `ink-wash` | 水墨留白 / Ink Wash | close reading, quiet |

Regenerate the previews after editing a palette:

```bash
python3 skills/build-academic-ppt/scripts/style_previews.py --sheets
```

## Install

### 中国大陆：一行命令，自动降级

GitHub 在境内的可达性不稳定，而且主站、codeload、API、raw CDN 各坏各的，
某个镜像今天能用下周可能就没了。所以安装器**按顺序试遍所有通道**，
谁先成功用谁，并打印出实际走的是哪条：

**先取整包，再从包内运行安装器**——不要单独去取 `install.sh`：

```bash
mkdir -p /tmp/bdp && cd /tmp/bdp && \
( curl -fsSL --connect-timeout 8 --max-time 60 -o pkg.tgz \
    https://codeload.github.com/JFWaskin/build-academic-ppt/tar.gz/refs/heads/main \
  || curl -fsSL --connect-timeout 8 --max-time 60 -o pkg.tgz \
    https://github.com/JFWaskin/build-academic-ppt/archive/refs/heads/main.tar.gz \
  || curl -fsSL --connect-timeout 8 --max-time 60 -o pkg.tgz \
    https://ghfast.top/https://github.com/JFWaskin/build-academic-ppt/archive/refs/heads/main.tar.gz \
  || curl -fsSL --connect-timeout 8 --max-time 60 -o pkg.tgz \
    https://cdn.jsdelivr.net/gh/JFWaskin/build-academic-ppt@main/install.sh ) \
  && tar -xzf pkg.tgz && cd build-academic-ppt-main && ./install.sh
```

**为什么先取整包**：`raw.githubusercontent.com` 的 CDN 在推送之后可能**几分钟内还在发旧版**
（实测过：raw 发的是修复前的 install.sh，而 codeload 已经是新的）。从整包里运行
安装器，安装器和 skill 包必然是同一版本，也省掉一次网络往返。

如果连 codeload 都进不去，**先手动拿到整包或 install.sh**，再本地运行；也可以指向
你自己的码云镜像：

```bash
BUILD_ACADEMIC_PPT_REPO=<你在码云上的镜像>/<仓库名> ./install.sh
```

安装器依次尝试：

| 顺序 | 通道 |
|---|---|
| 1 | `codeload.github.com` 直连 |
| 2 | `github.com/…/archive` 直连 |
| 3 | 代理镜像（ghfast.top / gh-proxy.com / ghproxy.net / moeyy / gitmirror） |
| 4 | **jsDelivr CDN**（与 GitHub 不同的网络路径，有境内节点） |
| 5 | `git clone --depth 1` |

下载后会**校验包完整性**（文件齐全 + 每个脚本能解析），校验不过就换下一条路，
不会把一个坏包装进去。

装好后两个位置都会有：

- `~/.claude/skills/build-academic-ppt/` —— Claude Code
- `~/.minimax/skills/build-academic-ppt/` —— MiniMax Code

常用参数：

```bash
./install.sh --check        # 只验证下载，不安装
./install.sh --uninstall    # 卸载（旧版会留时间戳备份）
```

### 作为 Claude Code 插件

```
/plugin install build-academic-ppt --marketplace JFWaskin/build-academic-ppt
```

这条路线依赖 Claude Code 的 marketplace 机制，需要访问 `api.github.com`，
**境内可能失败**——请优先用上面那条一键命令。

### 只要 skill 目录

```bash
git clone --depth 1 https://github.com/JFWaskin/build-academic-ppt.git
cp -R build-academic-ppt/skills/build-academic-ppt ~/.claude/skills/
```

### How to use it

[`skills/build-academic-ppt/references/user-guide.md`](skills/build-academic-ppt/references/user-guide.md)
is the walkthrough for the person using the skill: what to prepare, the five
steps, a worked example dialogue, how to revise a deck they have already
hand-edited, and the common cases. Hand it over as-is.

## Other agent harnesses

The skill is **plain files** — a `SKILL.md` with YAML frontmatter, a
`references/` folder, and Python scripts. No Claude-specific tooling, no
network calls at build time, no API keys. Any harness that can load a skill
directory can load it.

| Harness | Entry point | Install |
|---|---|---|
| **Claude Code** | `.claude-plugin/plugin.json` + `marketplace.json` | `/plugin install build-academic-ppt --marketplace JFWaskin/build-academic-ppt`, or `./install.sh` |
| **MiniMax Code** | same skill directory | `./install.sh` (→ `~/.minimax/skills/`) |
| **Codex** | `.codex-plugin/plugin.json` (`"skills": "./skills/"`) | plugin manager, or `./install.sh` (→ `~/.codex/skills/`) |
| **Cursor** | `.cursor-plugin/plugin.json` | `/add-plugin build-academic-ppt`, or `./install.sh` |
| **Gemini CLI** | `gemini-extension.json` + `GEMINI.md` | `gemini extensions install <repo>`, or `./install.sh` |
| **Kimi Code** | `.kimi-plugin/plugin.json` + inline tool mapping | `/plugins` → marketplace, or `./install.sh` |
| **OpenCode** | `.opencode/plugins/build-academic-ppt.js` | add to the `plugin` array in `opencode.json`, or `./install.sh` |
| **pi** | `.pi/extensions/build-academic-ppt.ts` | marketplace, or `./install.sh` |
| **Devin** | `.devin-plugin/plugin.json` | `./install.sh` |
| **Hermes** | `.hermes-plugin/plugin.yaml` | `agy plugin install <repo>` |
| **Any harness reading `AGENTS.md`** | `AGENTS.md` in the repo root | point it at the repo |

`./install.sh` detects which of these are present on the machine and installs
into each of them; it never creates a directory for a harness that is not
installed.

The tool mapping (which tool is "ask the human", which is "dispatch a
fresh-eyes reviewer") is tabulated in `AGENTS.md`, and Kimi's is inlined in
its manifest. **The one thing every harness must be able to do is run a
separate reviewer that has not written the deck** — the QA loop depends on it.

## Requirements

| tool | needed for | install |
|---|---|---|
| Python 3.9+ | everything | — |
| `python-pptx` | building decks | `pip install python-pptx` |
| `PyMuPDF` | cropping and probing PDFs | `pip install pymupdf` |
| `Pillow` | images | `pip install pillow` |
| `lxml` | python-pptx dependency | `pip install lxml` |
| LibreOffice (`soffice`) | rendering for QA | `brew install --cask libreoffice` |
| `poppler` (`pdftoppm`, `pdftotext`) | rendering for QA | `brew install poppler` |
| `tesseract` | scanned sources only | `brew install tesseract` |

`install.sh` checks all of them and tells you what is missing.

## Use

In Claude Code, say what you want:

```
用 build-academic-ppt 把 ~/Documents/paper.pdf 和 notes.docx 做成一页 20 页的
中文汇报 PPT，先问我主题、要点、研究问题和风格。
```

The skill then:

1. Runs `brief.py questions` and asks you for everything it does not know.
2. Reads your sources, derives what it can, and asks again for what it cannot.
3. Proposes a style (with previews) and a length.
4. Builds the deck, crops the screenshots, and runs the QA gate.
5. Hands you the deck, the assumptions it made, and anything it could not
   verify.

### The intake brief on its own

```bash
cd skills/build-academic-ppt/scripts

python3 brief.py questions              # print the questionnaire (round 1)
python3 brief.py record --key title --value "…" --source given
python3 brief.py status                 # what is still missing
python3 brief.py check                  # GATE: exit 0 only when complete
python3 brief.py summary                # the brief, with assumptions listed
```

`brief.py check` is a gate. It exits non-zero while a required field is
missing, and `brief.py defaults` refuses to assume anything before the second
round of questions.

## Copy-paste prompts

**Install (as a plugin)** — paste into Claude Code:

```
/plugin marketplace add JFWaskin/build-academic-ppt
```

**Install (as a skill directory)** — in a terminal:

```bash
git clone https://github.com/JFWaskin/build-academic-ppt.git
cd build-academic-ppt && ./install.sh
```

**Use it** — paste into Claude Code:

```
用 build-academic-ppt 把 ~/Documents/paper.pdf 和 notes.docx 做成一页 20 页的中文汇报 PPT。
先问我主题、核心要点、研究问题和视觉风格，给我看样式样张。
每页要真实截图和完整引注，正文至少 14pt。
```

**Use it on an existing deck** — paste into Claude Code:

```
用 build-academic-ppt 修改 ~/Documents/deck.pptx。
那个文件我手改过，不要重新生成，要在我的版本上改。
先确认要改哪几页，改完告诉我你改了什么、没改什么。
```

**Check the installation** — in a terminal:

```bash
python3 ~/.claude/skills/build-academic-ppt/scripts/selftest.py
```

## Build a deck directly

```python
import sys
sys.path.insert(0, "skills/build-academic-ppt/scripts")
from deck_kit import Deck, txt, shot, theme, ML, CW
from pptx.util import Inches

d = Deck(theme_key="journal-serif", footer="功能性与翻译研究 · 文献评议")
s, y = d.content(eyebrow="证据结构", title="三个证据层级",
                 cite="Li, D., Wu, K. (2025). Title. Publisher. DOI 10.xxxx/yyyy.")
txt(s, ML, y, CW // 2, Inches(1.4),
    [[("研究问题", {"bold": True, "color": theme().accent})],
     [("译文在哪些可指认的语言层级与原文发生偏移？", {})]], size=14, line=1.25)
shot(s, "_shots/x.png", ML + CW // 2, y, CW // 2, Inches(2.1),
     caption="原文 P52：textual panorama 的界定（高亮处）", valign="top")
d.save("deck.pptx")     # prints every predicted overflow, then runs the
                        # geometry check
```

Crop the screenshots first:

```bash
python3 pdf_shots.py probe paper.pdf "functional asymmetry" "dual code"
python3 pdf_shots.py shots paper.pdf jobs.json _shots/
```

`jobs.json` is a list of `{name, page, needles, ctx, pad}` — plus optional
`occ` (which occurrence of the phrase) and `col` (`left` / `right`). The run
writes `manifest.json` next to the images with the page number of every crop:
read the page number from there, never hardcode it.

## Keeping it current

A skill installed by copying files is tracked by no package manager, so
nothing else would tell you that `~/.claude/skills` is three revisions
behind — and the failure is quiet: the deck still builds, it just uses the
old rules.

```bash
python3 skills/build-academic-ppt/scripts/version_check.py     # report
python3 skills/build-academic-ppt/scripts/version_check.py --upgrade
bash    skills/build-academic-ppt/scripts/auto_upgrade.sh       # check, upgrade, verify, roll back
```

`auto_upgrade.sh` upgrades, runs the self-test on the new copy, and **rolls
back to the previous one if it fails** — a broken release can never leave the
machine with a broken skill.

The check compares a hash over the **whole package** (every file, sorted by
path), not just `SKILL.md`: a release can change the scripts and leave
`SKILL.md` byte-identical, and a check that only watched the latter would
say "current" while the behaviour on disk was old.

Everything is fetched **pinned to a commit sha**, resolved before the
download. A branch URL is served from a CDN cache that can lag a push by
minutes — measured: both codeload and jsDelivr served the previous tarball
right after a push — and a version check that reads a cached file reports
"current" when a new version exists.

## Test

```bash
python3 skills/build-academic-ppt/scripts/selftest.py
```

32 checks covering the theme registry and its contrast audit, the theme switch,
the `lang` attribute on every run, the unit guards, the geometry check, the
stat row, the brief gate, research-question derivation, crop highlighting and
ambiguity, the OCR backends, the user guide, the VERSION stamp, and the QA
gate on both a clean and a broken deck.

## 中文说明

**它做什么**：把论文、专著、报告或扫描件做成学术汇报 PPT，要求**每一页的论断都能追溯到
原文中被高亮的段落**。截图是证据，不是装饰。

**先问再做**：动代码之前必须先完成一份简报（brief）——主题、核心要点、研究问题、源材料、
视觉风格、篇幅。问两轮；两轮后仍未回答的，就从源材料推导，并在交付说明里列出每一条假设。
`brief.py check` 是硬闸门：必填项没齐就退出非零。

**七种风格**：`paper-warm`（暖纸朱砂）、`minimal-white`（极简白）、`journal-serif`（学术期刊）、
`slate-dark`（冷灰深色）、`blueprint`（蓝图理性）、`kraft`（牛皮纸）、`ink-wash`（水墨留白）。
每套都有完整的配色、双强调色、字体搭配与字号档，全部通过 WCAG AA 对比度审计，
并附样张（`assets/previews/`）。

**中文不折行**：python-pptx 生成的 run 缺 `lang` 属性，中文会被当成一个不可断的长词冲出
文本框。`deck_kit.txt()` 给每个 run 写上 `lang="zh-CN"`，这是中文 PPT 版面崩坏的头号根因。

**不要覆盖用户改过的文件**：如果 deck 已经存在，一律走「编辑模式」——先比对修改时间与文件
大小，改动过就以那个文件为唯一基线，先备份，再在原文件上改，绝不重跑生成脚本。

## License

MIT — see [LICENSE](LICENSE).
