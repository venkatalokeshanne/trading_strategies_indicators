# Strategy Selector — Backtesting Backend

## Goal
Day trader, US stocks, morning session. The user has ~1000 TradingView strategies (repo: https://github.com/venkatalokeshanne/trading_strategies_indicators). Each loses over a month because each only works in some conditions.
This project is **pure backtesting**. The user gives a date or date range; the system **trades it historically** and outputs backtest results. No signals, no trade-plan output, no live trading, no frontend.

For each day in the range, at a checkpoint (`premarket` = at the 09:30 open with pre-market info, or `open+5/10/15`), using only information available then:
1. pick 1–3 stocks from the universe (~69 symbols in `config/watchlists.yaml`: IBKR lists Traded, AI Core, AI Beta),
2. pick the strategy + timeframe (5/10/15m) for each, or abstain,
3. execute (simulate) the trade with Pine-faithful fills and costs, flat by EOD,
and report whether this process is profitable out-of-sample.

Output of `python -m src.cli backtest --from D1 --to D2`: ≤15-line summary + files in `runs/<id>/` (`summary.json`, `daily.csv`, `trades.csv`, `picks.csv`, `equity.csv`) vs baselines.

## Session protocol (every session)
1. Read `docs/STATE.md`, then ONLY the assigned ticket(s) `docs/tickets/Txx-*.md`. Never read the whole repo.
2. Do the ticket inside its scope. 2–3 tickets per session max.
3. Run the ticket's acceptance check for real (real data/APIs, not mocks). A ticket is marked done in STATE.md ONLY after that check passes; if it can't run, say so and leave the ticket in progress.
4. Rewrite `docs/STATE.md` (≤40 lines: done, decisions, next ticket, problems).
5. Commit `Txx: <what>`.

## Code rules
- Least code that solves the ticket. No speculative features, no abstraction used once. Reuse the TradingView repo's `pinelib` — do NOT rewrite engine, indicators, broker or metrics.
- Tests ONLY where a bug silently costs money: lookahead/gating, EOD flatten, cost mapping, walk-forward splits. Nothing else.
- One-line comments only where the reason isn't obvious.
- Never print DataFrames/long logs. Summaries ≤15 lines; detail to `runs/`.
- Deps: pandas, numpy, pyarrow, duckdb, requests, pyyaml, typer, plus `pip install -e $PINE_REPO_PATH/python` (pinelib). scikit-learn only if a ticket needs it.

## Token discipline
- Don't re-read files you just wrote; don't echo big files.
- Inspect with head/grep/DuckDB queries.
- Pine conversion: ONE script at a time, using the repo's own skill (see below). `progress/progress.json` in the TV repo + our `data/catalog.json` are the status sources; never re-triage or re-convert done items.
- Long jobs: write script → run → read only its summary.

## Existing assets in the TV repo (use them)
- `python/pinelib/`: Pine-faithful bar-by-bar engine (`ta.*` exact seeding, `request.security`, broker emulator with commission/slippage/pyramiding, metrics). `pinelib.runner.run(ScriptClass, bars, params=, symbol=, timeframe=, strategy_overrides=)` → `RunResult` (broker trades, metrics).
- `python/strategies/*.py`: ~27 strategies already converted (FULL), same id/slug as `TradingView/strategies/`. 1022 strategies still pending.
- `.claude/skills/pine-to-python/` (SKILL.md, LESSONS.md, reference/translation.md): the conversion procedure. Read LESSONS.md first in every conversion session. Converted files are committed to the TV repo (`python/strategies/`), not to this repo.
- `TrendSpider/`: JavaScript derived from the Pine scripts. Pine is the source of truth for conversion; use TrendSpider JS only as a hint, not as a source.
- `python/tradesearch/`: a separate TradeSearcher-style backend (repaint audit, scoring). Reuse `repaint.py` ideas for the no-lookahead check if useful; don't depend on its API/DB.

## Day-trade adapter (our only engine code)
pinelib runs a script bar by bar over a continuous series (warm-up matters: EMA200 etc.). So per (strategy, symbol, timeframe, checkpoint-gate) run once over the whole period, then split trades by day. The adapter:
- gates entries: no `strategy.entry/order` before the checkpoint time of that day (wrapper over `script.strategy`),
- flattens at the EOD cutoff (`close_all` on last bar of the day) and blocks overnight carry,
- maps costs to `strategy_overrides` (commission + slippage ticks by liquidity tier),
- limits entries per day, runs processes in parallel, writes per-day PnL/trades to DuckDB.
Checkpoint gates default to two: `open` (09:30) and `open+10`; add 5/15 only if T13 shows value (each gate multiplies compute).
Compute is the bottleneck (~0.5–2 s per 20k-bar run). Prioritize variants, cache results by (script hash, params, symbol, tf, gate, data hash), parallelize per core.

## Non-negotiable correctness
1. **No lookahead.** Features/decisions at checkpoint C use only data < C. Signals follow pinelib/Pine fill rules (next bar open). Learning for day D uses only days < D.
2. **Costs always on**; slippage depends on liquidity tier (QBTS/IONQ ≠ AAPL). Never report gross alone.
3. **Day trading**: flat by EOD; no overnight.
4. **America/New_York**, regular hours, calendar-aware. Pre-market data only used for features.
5. **Walk-forward only** for anything learned. Expanding or rolling train window strictly before each test day. Parameter search on train only.
6. **Multiple-testing guard**: best-of-1000-strategies × 69-stocks finds lucky winners. Use hierarchical shrinkage (symbol+variant+regime → variant+regime → variant), minimum samples, count candidates considered, judge only out-of-sample days.
7. A converted strategy that is not parity-verified (see below) gets lower weight/flag in results.

## Known biases (print in every report)
- Watchlists were curated today from stocks that already moved → hindsight bias; results optimistic. Control: also run on a neutral subset (QQQ + mega-caps) and report both.
- New tickers (INFQ, SPCX, SKHY, PSQL…) have short history; excluded from learning until min-history met.
- Twelve Data bars ≠ TradingView bars (pinelib notes this). Parity vs TradingView is checked on data from the same vendor where possible.

## Intelligence rules
- A weak result is information, not a stop. Test across conditions (trend/chop, gap/flat, vol, events, timeframes) before judging a strategy.
- Don't be too strict: soft scoring over hard filters; hard filters starve trade counts.
- Abstaining is a valid pick.
- Simple first; add complexity only if it beats the simpler version out-of-sample.

## Architecture (this repo)
```
src/
  data/       twelvedata client (multi-key), parquet cache, calendar, quality
  adapter/    pinelib day-trade adapter (gate, EOD flat, costs, per-day extraction)
  pine/       catalog (triage/priority), conversion status helpers
  features/   per symbol-day features per checkpoint, market context, events, regimes
  selector/   stock ranker, strategy selector, walk-forward backtest, baselines
  store/      DuckDB: runs, daily_pnl, trades, features, picks
  cli.py      typer: data | pine | run | backtest | report
  service.py  (later) plain functions for a future API/UI
config/       default.yaml, watchlists.yaml
data/         cache (gitignored), catalog.json (committed)
runs/         outputs (gitignored)
docs/         STATE.md, PLAN.md, tickets/
```
Future frontend: all logic = plain functions returning DataFrames/dicts; CLI/API are thin wrappers; results are in DuckDB + files.

## Data
- Twelve Data, `.env` `TWELVEDATA_API_KEYS` (comma list, 6 keys; never commit). Rotate keys, per-key rate-limit backoff, resumable, fetch only missing ranges.
- 1-min bars (+pre-market if plan allows) as parquet per symbol/month; 5/10/15m resampled from 1m.
- Record plan limits and history depth in STATE.md during T02.
