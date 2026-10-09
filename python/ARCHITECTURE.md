# TradeSearch backend — architecture

A backend that does what [TradeSearcher](https://tradesearcher.ai) does — every TradingView
strategy backtested across many symbols and timeframes, audited for repainting,
quality-gated, scored and ranked — built on a **Pine-faithful Python engine** so a converted
script produces the same trades Pine would on the same bars.

No UI. Everything below is logic, storage and an HTTP API for a frontend to call.

## What TradeSearcher does (and where each part lives here)

Collected 2026-10-09 from its public pages, docs (docs.tradesearcher.ai) and its open-source
agent client (github.com/vnguyen42/tradesearcher-agent-tools, MIT).

| TradeSearcher feature | Module |
|---|---|
| Run every strategy × symbol × timeframe (~20k bars, intrabar "bar magnifier" fills) | `tradesearch/pipeline.py` on `pinelib` |
| Repaint audit by replaying with truncated data ("No-repaint checks 8/8") | `tradesearch/repaint.py` |
| Quality gate: reject sub-viable runs before ranking ("eligible" backtests) | `tradesearch/scoring.py` |
| Robust Score 0–100 = Consistency · Backtests · Edge · Practicality | `tradesearch/scoring.py` |
| Metrics: net profit %, PF, Sharpe, Sortino, max DD, win rate, trades, risk/reward, avg trade, buy & hold, t-stat, p-value | `pinelib/metrics.py` |
| Search backtests (symbol, market, timeframe, strategy type, min Sharpe/PF, max DD, …; sort) | `tradesearch/search.py` |
| Best-for-symbol ranked shortlist (`rank`, `weightedScore`) | `tradesearch/search.py` |
| Backtest detail: trades, equity, drawdown and buy-and-hold curves, parameters | `tradesearch/api.py` |
| Strategy detail: indicators / entry / exit criteria, tags, averages across tests, repaint summary, source | `tradesearch/catalog.py` |
| Compare backtests | `tradesearch/search.py` |
| Symbol pages: backtests run, % beating buy & hold, medians, by strategy type, best timeframe | `tradesearch/aggregates.py` |
| Leaderboard: last 350 days, rebased equity vs BTC buy & hold | `tradesearch/aggregates.py` |
| Platform counters: analysed / eligible / symbols / strategies | `tradesearch/aggregates.py` |
| Strategy assistant ("find my strategy") | `tradesearch/assistant.py` |
| Free calculators (Kelly, risk of ruin, Monte Carlo, prop-firm, …) | `tradesearch/calculators.py` |
| Agent API + MCP server (7 tools, same names and parameters) | `tradesearch/api.py`, `tradesearch/mcp_server.py` |

Not public, so **designed here and documented, not copied**: the Robust Score's exact
weights, the 8 repaint checks' exact definitions, and the quality-gate thresholds.

## Layers

```
TradingView/{indicators,strategies}/*.pine      original sources (git)
        │  hand conversion, one script at a time (skill: pine-to-python)
        ▼
python/indicators/*.py, python/strategies/*.py   converted scripts — subclasses of pinelib.Script
        │
python/pinelib/        Pine runtime: bar-by-bar execution, na, history [n], var,
                       per-call-site state for every ta.* function, request.security,
                       arrays, drawings, plots, and the strategy broker emulator
        │
python/tradesearch/    data providers + cache, pipeline, repaint audit, quality gate,
                       scoring, search/rank, aggregates, assistant, calculators,
                       SQLite/Postgres storage, FastAPI app, MCP server
```

### Why a bar-by-bar runtime, not vectorised maths

Pine executes once per bar with history, `var` state and **separate state per call site**
(two `ta.ema` calls, or one UDF called from two places, never share state). Reproducing
that exactly in vectorised numpy means restructuring every script by hand — the main source
of silent conversion bugs. A runtime with Pine's execution model lets each script be
translated **line for line**. Cost: ~0.5–2 s per 20k-bar backtest in CPython; the pipeline
runs one process per core.

## pinelib execution model

| Pine | pinelib |
|---|---|
| script runs once per bar, at the bar's close | `Script.on_bar()` called by the runner for each bar |
| `na`, arithmetic propagates na | Python `nan` (propagates the same way); `na(x)`, `nz(x)` |
| `x / 0` → na | `div(a, b)` — Python `/` raises; the lint flags bare `/` with a non-constant divisor |
| `close`, `high`, … with `[n]` | `self.close` etc. are `Series`: behave as floats, `self.close[1]` is history |
| `expr[n]` on any value | `S(expr)[n]` — call-site-keyed history |
| script-level variable with history | `self.H('x').set(v)`, then `self.H('x')[1]` |
| `var x = …` | attribute set in `init()`, mutated in `on_bar()` |
| `ta.*` | `pinelib.ta.*` — stateful per call site, Pine's exact formulas and seeding |
| function called twice in one bar | recomputed from the previous bar's committed state (Pine's rollback) |
| `request.security(sym, tf, expr, lookahead)` | `self.security(sym, tf, fn, lookahead=…)` — expression evaluated on real HTF bars |
| `input.*` | `self.input.int(…)`, … in `init()`; overridable per backtest |
| plots, shapes, fills, alerts | recorded outputs |
| `line/box/label/table/polyline` | data objects with Pine's getters/setters and max-count GC (scripts read them back) |
| `strategy.*` | `self.strategy.*` → broker emulator |

### Broker emulator (Pine's rules)

- Orders created at a bar's close are processed on the next bar; market orders fill at its
  open (`process_orders_on_close=true`: at the same close).
- Intrabar path: open→high→low→close if the high is nearer the open than the low, else
  open→low→high→close; with bar magnifier, the lower-timeframe bars give the path.
- Stop/limit orders fill at their price, or at the open when the bar gaps through.
- `strategy.entry` honours pyramiding and reverses an opposite position; `strategy.order`
  does neither; `strategy.exit` brackets (profit/loss in ticks, limit/stop prices, trailing)
  are OCA-reduce per entry; `close`, `close_all`, `cancel`, `cancel_all`.
- Sizing: fixed / cash / percent_of_equity; commission: percent / cash per contract / cash per
  order; slippage in ticks on market and stop fills; FIFO or ANY close rule; margin calls.

### Metrics — TradingView's definitions, plus TradeSearcher's extras

Net profit (abs, %), gross profit/loss, profit factor, closed trades, winners/losers, percent
profitable, average trade/win/loss, ratio avg win / avg loss (TradeSearcher's "Risk
Reward"), largest win/loss, average bars in trade, max equity drawdown (close and intrabar),
max run-up, buy & hold return, Sharpe and Sortino (monthly returns, risk-free 2 %/yr),
commission paid, plus t-statistic and p-value of per-trade returns, and equity, drawdown and
buy-and-hold curves.

## Accuracy

Given **the same bars**, the target is identical trades to TradingView. Remaining sources of
difference, each listed in the script's header when it applies: data vendor (TradingView's
bars are the reference), facts still marked **[VERIFY]** in `pinelib` (each a single switch,
fixed in one place when confirmed against a TradingView export), and scripts whose behaviour
depends on realtime ticks (`calc_on_every_tick`, `varip`), which a historical backtest cannot
reproduce in Pine either.
