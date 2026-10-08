# Trading strategies & indicators — Pine Script → TrendSpider

Hand-converting TradingView Pine Script indicators and strategies into TrendSpider custom
JavaScript, **one script at a time**, with every deviation written down. There is
deliberately no automatic converter: the two platforms disagree on execution model, time
units, day numbering, indicator seeding and position management, and most of those
disagreements produce code that runs and quietly returns wrong numbers.

## The skill

[`.claude/skills/pine-to-trendspider/`](.claude/skills/pine-to-trendspider/SKILL.md) is a
Claude skill holding the full procedure:

| File | Covers |
|---|---|
| `SKILL.md` | the procedure (steps 0–9 with done-gates), output format, and the final self-audit checklist |
| `LESSONS.md` | **every past mistake**, the rule replacing it and the check that now catches it — read first, every session |
| `reference/01-execution-model.md` | per-bar vs whole-array, `[n]`, `var`, `na`, recursion, library imports |
| `reference/02-function-map.md` | every `ta.*` / `math.*` / `str.*` mapping, seeding traps, hand-rolled equivalents |
| `reference/03-time-sessions-inputs.md` | ms vs s, `dayofweek` and `month` numbering, sessions, inputs |
| `reference/04-plotting-and-drawing.md` | plots, shapes, fills, drawing objects, the fixed-slot pattern |
| `reference/05-strategies.md` | the Strategy Tester model, fill timing, pyramiding, partial exits |
| `reference/06-higher-timeframe-and-data.md` | `request.security`, repainting, other symbols, alt-data |
| `reference/07-sandbox-traps.md` | TrendSpider rules that fail silently or only at save time |
| `reference/08-validation.md` | five validation levels, up to numeric parity with TradingView |
| `reference/09-trendspider-live.md` | the mandatory live test: run, save as `_TV`, confirm, restore the chart, Strategy Tester |
| `templates/` | a working indicator, a working strategy state machine, Pine-semantics helpers |

Facts are tagged **[VERIFIED]** (confirmed against TrendSpider's docs, its real engine, or a
live script) or **[VERIFY]** (check before relying on it). Confirming a [VERIFY] is worth
committing on its own.

**Using it.** In Claude Code, open this repository — the skill is picked up as a project
skill. Then ask: *"convert the next script"*. On claude.ai, zip the
`pine-to-trendspider` folder and upload it as a custom skill.

## Picking up where the last session stopped

```bash
git pull
python tools/progress.py stats        # where the backlog stands
python tools/progress.py next 5       # what to convert next
```

`progress/progress.json` is the shared state: every script's status (`pending`,
`in_progress`, `FULL`, `PARTIAL`, `NOT CONVERTIBLE`), validation level and deviations.
**Every conversion is committed and pushed immediately**, so nothing is lost between
sessions or accounts.

## Tools

These validate and track. None of them converts anything.

| Command | Purpose |
|---|---|
| `python tools/lint_trendspider.py <file.js \| file.md>` | TrendSpider's exact validator rules (from `tools/trendspider_rules.json`), ES2020 syntax, `_TV` name, every lintable lesson; `.md` files have their code blocks checked |
| `python tools/ts_live_payload.py apply\|find\|remove <file>` | browser snippets for the live TrendSpider test (`reference/09`) |
| `node tools/extract_engine_rules.js` | re-extract `trendspider_rules.json` from TrendSpider's engine (local bundle only) |
| `python tools/oracle_run.py <file> --bars <csv>` | run the script through **TrendSpider's own engine** and compare with TradingView exports (levels 3–4) |
| `python tools/progress.py sync / stats / next / set / check` | backlog bookkeeping; `set --status FULL\|PARTIAL` refuses until every done-gate passes |

`oracle_run.py` needs TrendSpider's captured scripting engine, which exists only on the
machine that captured it and is never committed. Elsewhere, validate against TradingView
exports instead (`reference/08-validation.md`, level 4).

## Layout

| Folder | Holds | In git |
|---|---|---|
| `TradingView/indicators/` | original Pine indicators (924) | yes |
| `TradingView/strategies/` | original Pine strategies (1,053) | yes |
| `TradingView/_meta/` | the extractor's title/author/URL records | yes |
| `TrendSpider/indicators/` | converted indicators, `<id>-<slug>.trendspider.js` | **yes** |
| `TrendSpider/strategies/` | converted strategies | **yes** |

A script's folder follows its own declaration (`indicator()` / `strategy()`), not the
TradingView listing it was collected from. A conversion keeps the original's id and slug.

## What is — and is not — in this repository

This repository is **public**. It contains the skill, references, templates, tools, the
progress log, the original Pine sources (`TradingView/`) and every conversion
(`TrendSpider/`). The sources were published openly on TradingView by their authors;
each one's author and URL are in `TradingView/_meta/` and `progress/progress.json`, and
every conversion credits its author and the licence the source declared. 75 % of the
sources declare no licence, so their authors' rights apply — they are kept here as the
reference for the conversions. Every conversion is also saved in the owner's TrendSpider
account under the same `<Title>_TV` name.

The validation outputs and market-data fixtures are excluded too, as is TrendSpider's
proprietary engine bundle (only the list of names and limits extracted from it,
`tools/trendspider_rules.json`, is committed).

## Backlog

| | Count |
|---|---|
| Pine scripts collected | 1,977 |
| Strategies | 1,053 |
| Indicators | 924 |
| Import a Pine library (needs the library's source) | 41 |

Queue order: strategies first, then indicators; within each, shortest source first, so the
simpler conversions harden the reference files before the hard ones.
