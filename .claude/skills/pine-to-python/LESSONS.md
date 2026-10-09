# Lessons — Python conversions (and the engine under them)

Read in full before converting. When a new mistake is found: fix it, add an entry here with
its rule and an automated check (lint, test, or progress gate), and commit as
`Lesson P<n>: …` in the same commit. The TrendSpider skill's LESSONS (L1–L18) still apply
where relevant — especially L9 (check the artefact, not the exit code) and L10 (never
validate code against itself).

## P0 — Validate against an independent implementation
**What happened.** The first Python run of "Simple Long Only Bot" looked fine. Only the
comparison with a separately written simulation showed 3 missing entries — exposing a real
broker bug (P2).
**Rule.** FULL requires the same entry/exit bars as an independent re-implementation of the
rules, written from the Pine source.
**Check.** `progress.py` only accepts `--py-status FULL` with `--py-validation independent`.

## P1 — Python `/` raises on zero; Pine returns na
**Rule.** `div(a, b)` for every division whose divisor is not a non-zero constant.
**Check.** Lint ERROR on bare `/` with a non-constant divisor.

## P2 — `x * 100 / 100` is not always `x` (found in the broker)
**What happened.** `strategy.close` at 100 % computed `total * 100 / 100`, one ulp short;
rounding to the quantity step then left a 1e-9 phantom position open, so the strategy
thought it was still long and skipped later entries.
**Rule.** Handle the 100 % case exactly; never leave a sub-step residual open.
**Check.** Broker regression test `test_full_close_with_fractional_qty_leaves_nothing_open`.

## P3 — Python built-ins that differ from Pine's math
`round()` rounds half to EVEN (Pine rounds ties up); `max(nan, 3)` depends on argument
order (Pine → na); `math.*` raises on domain errors (Pine → na).
**Check.** Lint ERROR on `round(`; WARN on builtin `max`/`min` with 2+ args and on `math.`.

## P4 — `and`/`or` short-circuit vs Pine v5
Pine v5 evaluates BOTH operands, so a `ta.*` call on the right side runs every bar; Python
skips it → that call site loses history. Pine v6 short-circuits like Python.
**Check.** Lint ERROR for a `ta.*`/`S()` call on the right of `and`/`or` when Pine ≤ v5.

## P5 — Conditional calls change history
A `ta.*` call inside an `if` only advances on bars where the branch runs — in Pine too.
Keep the call where Pine has it; never move a call into or out of a block.
**Check.** Lint WARN on `ta.*`/`S()` inside a block (confirm it matches the Pine source).

## P6 — pandas 3 datetime resolution
`date_range(...).asi8 // 1_000_000` is no longer milliseconds (pandas 3 defaults to µs).
**Rule.** Convert with `.as_unit("ms").asi8`.
**Check.** Fixed in runner and tests; grep for `asi8 //` before committing.

## P7 — Windows console encoding
Printing `→` or `≤` to a cp1252 console crashes a run (seen again 2026-10-09).
**Rule.** Tools reconfigure stdout to UTF-8; ad-hoc scripts set `PYTHONIOENCODING=utf-8`.
**Check.** All tools call `reconfigure(encoding="utf-8")`.

## P8 — Data-provider quirks
Yahoo `range=max` silently returns QUARTERLY bars for daily requests; Yahoo and Binance
return the still-forming current bar.
**Rule.** Daily+ via explicit `period1/period2`; drop incomplete bars.
**Check.** `data._complete_only`, and bar counts printed by the pipeline.

## P9 — Sub-viable backtests and exploding Sharpe
Pine's default sizing (1 contract) on $1M "profits" 0.0 % and makes monthly Sharpe explode
(−62). Faithful per backtest, but must not drive rankings.
**Rule.** The quality gate needs ≥ 1 % net profit; symbol-level aggregates use eligible
backtests only.
**Check.** `scoring.GATE["min_net_profit_percent"]`; test_quality_gate.

## P10 — A reversal deleted the new entry's exit order (found in the broker)
**What happened.** "Fast Scalper with Stops" reverses short→long and places
`strategy.exit(..., "Long", stop=…)` on the same bar. Closing the short ran the
"drop exits with no position" clean-up while the long was between "removed from pending"
and "opened", so its stop vanished and the trade ran stopless. The independent check
(247 vs 248 trades) exposed it.
**Rule.** Exits are pruned only after all fills of a bar step are complete.
**Check.** Broker regression test `test_exit_for_the_new_entry_survives_a_reversal`, and the
independent checks in `python/checks/` (run with `tools/run_checks.py`).
