# Lessons — every mistake made so far, and what now stops it happening again

**Read this file in full before every conversion.** It is short on purpose. Each entry is
a mistake that was actually made while building or using this skill, the rule that
replaces the habit behind it, and the *mechanical* check that now catches it — so the
fix does not depend on anyone remembering.

## How this file is maintained (mandatory)

When a new mistake is found — by the lint, the oracle, TradingView parity, the live
TrendSpider test, or the user — do all of these **in the same commit**:

1. Fix the conversion.
2. Add an entry below: what happened, the rule, the check.
3. Add the check where it belongs: `tools/lint_trendspider.py` for anything visible in
   source; the SKILL.md checklist or a gate for anything that needs judgement.
4. Fix the reference file that let it through, if any.
5. Commit with a message starting `Lesson NN:` and push.

A lesson without a check is a reminder, and reminders are what failed the first time.
If no automated check is possible, say so in the entry and add a checklist line.

---

## L1 — Declaring a local with a reserved TrendSpider name

**What happened.** The Bollinger template declared `const mult = ...`. `mult` is a
TrendSpider built-in (series multiplication), and TrendSpider rejects the script. The
hand-written list of reserved names had 36 entries; the real list has **122**.

**Rule.** Never trust a hand-written list of platform names. The reserved set is
`tools/trendspider_rules.json → reservedIdentifiers`, extracted from TrendSpider's own
validator. Common traps: `mult`, `add`, `sub`, `div`, `sum`, `avg`, `current`, `market`,
`options`, `constants`, `line`, `fill`, `library`, `prices`, `candles`, `time`, `open`,
`high`, `low`, `close`, `volume`, `atr`, `rsi`, `ema`, `vwap`, `momentum`, `stdev`.
Suffix the Pine name instead: `multVal`, `atrVal`, `lineLevel`.

**Check.** Lint ERROR — reserved name directly after `const`/`let`/`var`/`function`/
`class`, or as the single parameter before `=>` (TrendSpider's exact rule). WARN for
destructuring and multi-parameter shadowing, which TrendSpider allows but which hides
the built-in.

## L2 — Using JavaScript TrendSpider forbids (`new`, `this`, `import`, timers, `eval`)

**What happened.** A reference example used `new Set(...)` for a session-day filter.
`new` is banned; the example would have been copied into conversions.

**Rule.** The banned keywords are `import`, `new`, `this`; the banned names are the 30 in
`trendspider_rules.json → bannedNames` (`fetch`, `eval`, `Function`, `setTimeout`, `URL`,
`Proxy`, `globalThis`, `prototype`, …). Use arrays with `includes`, object literals,
`Array.from({length:n}, …)`, `Array(n).fill(x)`.

**Check.** Lint ERROR on every banned keyword and banned name. Reference files are
linted by the same rules: any code block that is meant to be copied must pass.

## L3 — Guessing the language level instead of reading it

**What happened.** The skill first said `??` and `?.` were "unconfirmed" and swapped them
for ternaries; the lint warned on them. TrendSpider's parser is acorn with
`ecmaVersion: 2020`, where both are legal. The real limit — ES2021+ forms such as `??=`,
`||=`, `&&=`, `1_000`, `#private` — was not checked at all.

**Rule.** TrendSpider parses **ECMAScript 2020**. `??`, `?.`, `BigInt`, `**` are fine.
Logical assignment, numeric separators, class fields/private members/static blocks are
not. Node accepts all of them, so `node --check` passing proves nothing about these.

**Check.** Lint ERROR on ES2021+ syntax. The `??`/`?.` warnings were removed.

## L4 — Writing a hand-rolled indicator from memory

**What happened.** The first Supertrend draft referenced an undefined `trueRangeArr` and
used strict `>`/`<` where Pine's reference implementation uses band-ratchet conditions
`lower > prevLower || prevClose < prevLower`. It would have thrown, and once fixed would
still have flipped on different bars.

**Rule.** Every hand-rolled `ta.*` follows Pine's published reference implementation
line by line, with the source cited in a comment. Then it is proven numerically (L10).

**Check.** Oracle run must produce no runtime error (catches undefined names); level-4
parity catches wrong conditions. Not lintable — checklist line "hand-rolled functions
cite Pine's reference and were parity-checked".

## L5 — Saying two different things in two files

**What happened.** `str.replace_all → replaceAll` was listed as safe in the function map
while 07 called String method support unconfirmed.

**Rule.** One fact lives in one place. Other files link to it. When a fact changes,
`grep` the whole skill for the old claim before committing.

**Check.** Pre-commit step in SKILL.md §Record: `grep -rn "<old claim>" .claude/skills`.

## L6 — Assuming TrendSpider lacks a built-in

**What happened.** The skill told the converter to hand-roll Supertrend, CCI, MFI, TSI,
Williams %R, correlation and Stochastic RSI. TrendSpider has all of them. Hand-rolling
works, but costs time and adds risk.

**Rule.** Before hand-rolling, check `reservedIdentifiers` and the TrendSpider API table
in `02-function-map.md`. If a built-in exists, its formula and seeding must still be
compared with Pine's before substituting — a built-in with the same name is not
automatically the same calculation (see L7 and the seeding table).

**Check.** Checklist line. Not lintable.

## L7 — `pivot_high` / `pivot_low` look ahead

**What happened.** TrendSpider's `pivot_high(src, left, right)` writes the value **on the
pivot candle itself**. Pine's `ta.pivothigh` writes it `right` bars later, when the pivot
is confirmed. Proven on 3,000 AAPL daily bars: 167 of 167 pivots land exactly `right`
bars earlier in TrendSpider. A signal built on the bare call trades on information that
did not exist yet — a backtest that looks great and is fake.

**Rule.** `shift(pivot_high(src, l, r), r)` reproduces `ta.pivothigh(src, l, r)` exactly.
Treat every sparse "find" built-in (`fractal_high/low`, `zigzag_points`, `find_*`) as
look-ahead until proven otherwise on the oracle.

**Check.** Lint WARN on any of these not wrapped in `shift(`.

## L8 — A console encoding crash reported as success

**What happened.** The extractor died on a Cyrillic script title (`cp1252` console) and
the shell chain `cmd; echo done` printed "done" anyway. It was reported as finished.

**Rule.** Every Python tool sets UTF-8 on stdout/stderr. Never chain with `;` when the
result matters.

**Check.** All tools in `tools/` reconfigure stdout/stderr (grep for `reconfigure`).

## L9 — Trusting an exit code instead of the artefact

**What happened.** Same incident as L8: success was judged by the command returning,
not by the output existing.

**Rule.** "Done" means the artefact was checked: the converted file lints clean, the
oracle CSV exists and has rows, the TrendSpider save returned 2xx **and** the script
appears under its `_TV` name in the "Yours" list, the commit is on `origin/main`
(`git log origin/main -1`).

**Check.** The gates in SKILL.md step 9 each name the artefact to inspect.

## L10 — Validating code against itself

**What happened.** Nearly happened with the templates: running the template and calling
the numbers "right" proves only that it runs.

**Rule.** Numeric correctness needs an **independent** reference: TradingView's exported
values (best), or an independent implementation written separately (Python/pandas).
The Bollinger template was verified to 1.1e-13 over 8,943 values against independent
Python; that is the standard.

**Check.** `progress.py` refuses FULL/PARTIAL with validation `tv-parity` unless
`--parity-evidence` is on record; checklist line.

## L11 — Declaring "not convertible" too early

**What happened.** Breakeven-after-partial-exit was declared impossible in TrendSpider.
It is convertible with approach B (the state-machine strategy in `05-strategies.md`).
An earlier estimate called most strategies "hard to port"; the real figure is 96 % portable.

**Rule.** NOT CONVERTIBLE needs a named blocker that has been tried against both
approaches in 05 and the hand-roll recipes in 02. Write the attempted approach into the
header.

**Check.** Checklist line: "NOT CONVERTIBLE names the feature and the approach tried".

## L12 — Treating a TrendSpider server error as a code error (or the reverse)

**What happened.** Saving returned HTTP 500 from `POST /custom_scripting_webserver/1/scripts`
— even for a two-line script. That is TrendSpider's server, not the conversion.

**Rule.** Separate the two: if the editor's APPLY runs the script and paints with no
console error, the code is fine. A 5xx on save is recorded as
`trendspider_saved: false` with the status code, and retried in a later session. Never
"fix" working code to chase a server error. A 4xx with a message is a code problem.

**Check.** Live-test procedure (`reference/09-trendspider-live.md`) records APPLY result
and save status separately.

## L13 — Same name for a paint and a signal

**What happened.** A paint called `'Buy'` and `register_signal(..., 'Buy')` collided —
they share one namespace in TrendSpider and the second silently replaces the first.

**Rule.** Signals end in `Entry`/`Exit`/`Signal`; paints never do.

**Check.** Lint ERROR on a paint/signal name collision.

## L14 — Saved name and file disagree

**What happened.** (Preventive, added with the `_TV` convention.) TrendSpider saves a
script under its `describe_indicator` title. If that title doesn't match the header and
`progress.json`, the next session can't find what was saved.

**Rule.** The `describe_indicator` title **is** the TrendSpider name, ends in `_TV`, and is
copied verbatim into the header's `TrendSpider name` line and `progress.json`.

**Check.** Lint ERROR if the title lacks `_TV` or differs from the header line.

## L15 — Generating code through layers of shell escaping

**What happened.** Patching tools via a shell heredoc that ran Python that wrote Python:
`\n`, `\t` and `\1` were unescaped one layer too early, three times in one session —
string literals split across lines and a regex backreference became a control character.

**Rule.** Write and edit files with the editor tools (Write/Edit), never by code that
generates code through a shell. If a script must patch a file, put the script in its own
file first. After any automated edit, parse the result (`node --check` /
`python -c "import ast; ast.parse(...)"`) before running it.

**Check.** Process rule; the syntax gate in the lint catches it for converted scripts.

## L16 — A built-in with Pine's name but not Pine's numbers

**What happened.** Measured on the oracle (2026-10-08) against independent Pine-formula
implementations: `momentum(x, n)` is `x − x[n−1]` (Pine `ta.mom` is `x − x[n]`); `cmo`
returns Pine ÷ 100; `tsi` returns Pine × 100 and takes `(long, short)`; `alma` takes
`(n, sigma, offset)` and floors the offset; `cci` is Pine × 0.9999; `supertrend()` takes no
parameters and flips on different bars. Each would have produced a script that runs and
is wrong — and several move thresholds (CMO ±50 becomes ±0.5), so signals silently never fire.

**Rule.** Use the measured table in `02-function-map.md`. A built-in not yet in that table
is measured on the oracle before it is substituted for a Pine function.

**Check.** Lint WARN on every call to a measured trap built-in, naming the exact fix; the
warning is acknowledged with `// pine-parity: <name>` on the same line once handled.

## L17 — Browser selectors that assume exact text or exact classes

**What happened.** In the first real live test (2026-10-09) two snippets in
`ts_live_payload.py` failed against TrendSpider's real DOM: the preview legend's class is
`legend-item--custom_script_editor_study_model`, so the exact class selector
`.legend-item--custom_script_` found nothing; and a legend row's text is `"BOSC\n522.197"`,
so `startsWith("BOSC ")` found nothing. The remove snippet refused rather than guessing —
the safety check worked — but the tool reported a drawn indicator as missing. Separately,
coordinate clicks in the Strategy Tester raced its menu animations and landed on nothing.

**Rule.** In browser snippets, match classes with `[class*="…"]`, normalise whitespace
(`innerText.replace(/\s+/g, ' ')`) before comparing text, pick menu items by text **and**
proximity to their trigger, and use DOM clicks, never coordinates, in TrendSpider menus.
A snippet that can click something destructive must refuse unless it matches exactly one
target.

**Check (L17).** All `ts_live_payload.py` snippets follow these rules; the `tester` mode wires the
Strategy Tester entirely by DOM. Every new snippet is proven once on the live page before
it is relied on (reference/09).

## L18 — A fact recorded loosely ("seeds from the first value")

**What happened.** Reference 02 said TrendSpider's `ema` "seeds from the first value". The
independent check for 7YZu94L1 then disagreed with the engine (67 vs 81 entries). Measured
exactly: `ema(x, n)` is **null for the first n−1 bars and starts from the value at bar
n−1** (max diff 6e-14). The loose wording sent the check — and could send a hand-rolled
EMA — the wrong way. Pine's own seed is still unconfirmed, but the trades agreed from bar
3 × n on either way.

**Rule.** Record engine behaviour as the exact formula you measured, with the test that
proved it, never as a paraphrase. When an independent check disagrees, find out *which
side* is wrong before touching the conversion — here the conversion was right and the
reference was vague.

**Check.** Every seeding entry in 02's table states its measured formula and test;
`progress.py` requires parity evidence for `tv-parity`; comparisons exclude 3 × the longest
recursive length, stated in the header.

## L19 — Long input titles are a runtime error, not a style issue
**What happened.** I6NhpUws kept the Pine input title "Volume moving average length (visual
only)" (42 chars). APPLY failed: `input(): name is too lengthy`. A 25-char title worked.
**Rule.** Input titles must be <= 30 characters; shorten and note it under Deviations.
**Gate.** lint_trendspider.py: title > 30 chars is an ERROR (21-30 stays a warning).

## L20 — Meaningful TrendSpider names; check saves through the API
**What happened.** Z1PSDV3J's Pine title is "My script" → saved as "My script_TV", meaningless
in the user's list. Separately, the editor's search list did not show some saved names, so a
save looked failed and was repeated: "Volume with Alert_TV" ended up saved three times.
**Rule.** The TrendSpider name is the Pine title + "_TV", unless that title is generic — then
use the TradingView listing title. The same name goes into progress (`--ts-name`). Verify a
save via `GET /authentication/1/api?path=/custom_scripting_webserver/1/scripts` (id + title),
never via the search box, and never click Save twice.
**Gate.** progress.py refuses generic names (my script / strategy / untitled ...).

## L21 — TrendSpider-AI drafts: negative shift = look-ahead; names are case-insensitive
**What happened.** (1) BaznTxS6's AI draft wrote Pine `high[2]` as `shift(high, -2)`, which
reads two bars into the FUTURE. (2) TOzt8Wxp had a plot "Buy Signal" and a signal "BUY Signal":
APPLY failed with `signal "BUY Signal" already exists` — paint and signal names share one
case-insensitive namespace.
**Rule.** Pine `x[n]` is `shift(x, n)` (positive). Never reuse a name, in any letter case,
between paint() and register_signal().
**Gate.** lint_trendspider.py: `shift(x, -n)` is an ERROR; the paint/signal collision check
compares names case-insensitively.
