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

## 3. `new` is banned outright [VERIFIED]

`Using "new" in scripts is not currently allowed`. That rules out `new Array`, `new Map`,
`new Set`, `new Date`, `new Error`, `new RegExp` and any class instantiation.

| Instead of | Use |
|---|---|
| `new Array(n).fill(v)` | `series_of(v)` (chart-length, mutable) or a loop with `push` |
| `new Map()`, `new Set()` | plain object `{}` / array with `includes` |
| `new Date(t)` | `time_of(t)`, or `library('moment-timezone')` |
| `new RegExp(s)` | a regex literal `/.../` |
| `new Foo(...)` | a factory function returning an object literal |

## 4. Built-in names are reserved [VERIFIED]

Declaring a local with the same name as any built-in global throws
`"X" is a reserved identifier which can't be assigned`. Pine scripts are full of such names:

`open high low close volume time hl2 hlc3 ohlc4 sma ema wma rsi atr vwap stdev variance
highest lowest sum shift line fill paint input current constants market indicators request
library assert`

— and more. This list is **not exhaustive**. Rename defensively: `atrVal`, `rsiVal`,
`emaFast`, `vwapLine`, `src`. If the editor raises the error for a name not listed here,
add it to this file.

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

## 11. JavaScript syntax support [VERIFY]

The sandbox parser's support for newer syntax — `??`, `?.`, class fields, `Array.prototype.at`,
`replaceAll` — is not confirmed. Write plain ES2017-style code: ternaries instead of `??`,
explicit guards instead of `?.`, `arr[arr.length - 1]` instead of `.at(-1)`. When you confirm
a feature works, record it here.

## 12. Saving can fail on TrendSpider's side [VERIFIED observed 2026-09-22]

On that date the scripting service returned **HTTP 500** to every attempt to *save a new*
custom indicator (`POST /custom_scripting_webserver/1/scripts`), including a two-line test
script — while **APPLY** worked and drew the indicator as an unsaved draft labelled
"Current indicator". If Save fails with "Failed to create the indicator", it is not your
code: the draft still proves the script runs. Tell the user, and keep the file in this repo
so it can be pasted again once saving works.

## 13. Signal names can collide with TrendSpider's built-ins [VERIFIED]

Built-in indicators expose signals with generic names (e.g. "EMA Crossover Signals").
Prefix yours with the script's short name so the user picks the right one in the
Strategy Tester's picker.

## 14. Local development loop [VERIFIED]

The editor can poll a file from a local server ("Connect to local dev server"), serving
`trendspider_indicator.js` at `http://localhost:8000/` with CORS enabled, and re-apply it on
every save. Port 8000 may already be in use by another local app — use whatever port the
editor accepts. [VERIFY whether the port is configurable]
