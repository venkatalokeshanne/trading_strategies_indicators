# 07 — TrendSpider sandbox traps

Rules of TrendSpider's scripting sandbox that are not obvious from the language, most of them
undocumented and found by running real scripts. Several fail **silently** or only **at
save time**, which is why they get their own file.

## 1. Metadata is frozen at save time [VERIFIED]

TrendSpider records the IDs of your outputs — derived from their **names** — from whatever
actually executes at the moment the user presses **Save**. Anything that did not run then is
ignored **forever**, even if it runs later.

- Every `paint()`, `fill()`, `paint_overlay()` and `register_signal()` call must execute
  **unconditionally**, in the **same order**, on **every** run.
- Never skip a paint inside `if`. Paint `constants.empty_series` (or a null-filled series)
  in the branch where there is nothing to show.
- Never build a name from an **input or data**: `` `SMA(${length})` `` changes when the user
  changes the input, orphaning the output. Use fixed names — `'SMA 1'`.
- Never paint a variable number of outputs. Pad to a fixed maximum (`04` shows the pattern).

## 2. Paint names and signal names share one namespace [VERIFIED]

`paint(x, {name: 'Green'})` followed by `register_signal(y, 'Green')` throws
`register_signal(): signal "Green" already exists`. Give signals distinct names —
`'Green light'`, `'Long Entry'`.

## The authoritative rules [VERIFIED — extracted from TrendSpider's validator]

§3, §4 and §11 below come from `validateScriptSyntax` in TrendSpider's own client engine,
captured by `tools/extract_engine_rules.js` into **`tools/trendspider_rules.json`**. The
lint loads that file, so it rejects exactly what TrendSpider rejects. When TrendSpider
changes, re-run `node tools/extract_engine_rules.js` (needs the local engine bundle) and
commit the new JSON.

The validator: wraps the script as `(async () => { … })()`, parses it with acorn at
`ecmaVersion: 2020`, then walks the tokens:

- a **banned keyword** (`import`, `new`, `this`) anywhere → error;
- a **banned name** (30 of them) as any name token → error;
- a **reserved identifier** (122 names) as the token directly after `function`, `const`,
  `let`, `class` or `var`, or as the single name directly before `=>` → error.

## 3. `new`, `this`, `import` and 30 names are banned [VERIFIED]

`Using "new" in scripts is not currently allowed`. That rules out `new Array`, `new Map`,
`new Set`, `new Date`, `new Error`, `new RegExp` and any class instantiation. `this` and
`import` are banned the same way.

Banned names (also as properties): `fetch`, `XMLHttpRequest`, `WebSocket`, `Request`,
`Worker`, `EventSource`, `BackgroundFetchManager`, `addEventListener`, `removeEventListener`,
`dispatchEvent`, `postMessage`, `EventTarget`, `onmessage`, `onmessageerror`, `onerror`,
`eval`, `Function`, `importScripts`, `require`, `setTimeout`, `setInterval`,
`setImmediate`, `requestAnimationFrame`, `Proxy`, `URL`, `WebAssembly`, `globalThis`,
`self`, `__proto__`, `prototype`.

| Instead of | Use |
|---|---|
| `new Array(n).fill(v)` | `series_of(v)` (chart-length, mutable) or a loop with `push` |
| `new Map()`, `new Set()` | plain object `{}` / array with `includes` |
| `new Date(t)` | `time_of(t)`, or `library('moment-timezone')` |
| `new RegExp(s)` | a regex literal `/.../` |
| `new Foo(...)` | a factory function returning an object literal |

## 4. Built-in names are reserved [VERIFIED]

Declaring a local with the same name as any built-in global throws
`"X" is a reserved identifier which can't be assigned`. The full set is the 122 names in
`tools/trendspider_rules.json → reservedIdentifiers`. The ones Pine scripts collide with
most often:

`open high low close volume time hl2 hlc3 ohlc4 sma ema wma rsi atr vwap stdev variance
highest lowest sum avg add sub mult div shift line fill paint input current constants market
options indicators request library assert momentum supertrend prices candles`

Rename by suffixing: `atrVal`, `rsiVal`, `multVal`, `lineLevel`, `supertrendPine`.

TrendSpider does **not** reject destructuring (`const [atr] = …`), a second name in a list
(`let a, atr`) or a multi-parameter arrow (`(x, atr) => …`). They still shadow the
built-in inside that scope; the lint warns.

## 5. Input titles have a length cap [VERIFIED]

A 35-character title failed with `input(): name is too lengthy`. The exact limit is
undocumented — keep titles under about 20 characters and move detail into the header comment.

## 6. Painting placement [VERIFIED]

- One script paints **either** overlay **or** lower pane, never both.
- A lower indicator that paints only colour clouds will not render.
- At most **70** output series per script.

## 7. Async data

`request.history` and every other `request.*` are asynchronous: `await` them. Top-level
`await` works. [VERIFIED] Check `.error` on the result and `assert` it, so a missing symbol
fails loudly instead of producing an empty chart.

## 8. Libraries [VERIFIED]

No `import` or `require`. Only these, through `library(name)`: `jstat`, `fft-js`,
`tinycolor2`, `binary-search-bounds`, `moment-timezone`, `lodash`, `papaparse`,
`fast-xml-parser`.

## 9. Determinism

The whole script re-runs on every edit, save and live update. `Math.random()` — and any
logic tied to the wall clock — produces different output each run. Never use them in
anything a signal depends on.

## 10. Execution limits [VERIFIED]

The script runs in a Web Worker with a time limit. Avoid nested loops over long histories.
`console.log` works for debugging; `debugger` needs
`localStorage.forceNoCustomScriptingWorkerTimeout = 1` in the browser console first.

## 11. JavaScript syntax support: ECMAScript 2020 [VERIFIED]

The parser is acorn with `ecmaVersion: 2020`.

| Allowed (ES2020 and earlier) | Fails to parse (ES2021+) |
|---|---|
| `??`, `?.`, `**`, spread, destructuring, arrow functions, template literals, `async`/`await`, `BigInt` literals | `??=`, `\|\|=`, `&&=` (logical assignment), `1_000` (numeric separators), class fields, `#private`, `static { }` blocks |

Methods are not syntax: `Array.prototype.at`, `String.prototype.replaceAll`,
`Object.hasOwn` parse fine and depend on the browser running the worker — assume a modern
Chrome but prefer the older form in shared code (`arr[arr.length - 1]`, `split/join`).
Node accepts everything above, so `node --check` passing is **not** proof; the lint
checks the ES2021+ forms itself (LESSONS L3).

## 12. Saving can fail on TrendSpider's side [VERIFIED observed 2026-09-22]

On that date the scripting service returned **HTTP 500** to every attempt to *save a new*
custom indicator (`POST /custom_scripting_webserver/1/scripts`), including a two-line test
script — while **APPLY** worked and drew the indicator as an unsaved draft labelled
"Current indicator". If Save fails with "Failed to create the indicator", it is not your
code: the draft still proves the script runs. Record it with
`progress.py set <id> --ts-saved no --ts-save-error "HTTP 500"`, keep the file in this repo,
and retry the save in a later session (`reference/09`, LESSONS L12).

## 13. Signal names can collide with TrendSpider's built-ins [VERIFIED]

Built-in indicators expose signals with generic names (e.g. "EMA Crossover Signals").
Prefix yours with the script's short name so the user picks the right one in the
Strategy Tester's picker.

## 14. Local development loop [VERIFIED]

The editor can poll a file from a local server ("Connect to local dev server"), serving
`trendspider_indicator.js` at `http://localhost:8000/` with CORS enabled, and re-apply it on
every save. Port 8000 may already be in use by another local app — use whatever port the
editor accepts. [VERIFY whether the port is configurable]
