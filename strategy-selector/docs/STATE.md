# STATE (rewrite each session, ≤40 lines)
Done: T01-T14, T16, T17 (T15 ML selector skipped: no demonstrated edge). T06.2 bulk run done for the TOP 250 Atlas-ranked strategies (not all 631). T14 NOT rerun on the new window.
VERDICT: UNPROVEN / FRAGILE. Do NOT trade on this. Numbers below are after two bug fixes found this session and are still optimistic.
DAILY USE: `python -m src.cli picks --fetch` (after 09:40 ET; default k=6 stocks; `--date D --score` replays a past day). src/selector/live.py: per market regime take the 3 DIFFERENT strategies with best mean/std of $ per symbol-day (consistency, trained on days < today); stocks ranked by open+10 range/volume/gap; hard stop 1%; output runs/live/<date>.json.
 Walk-forward Apr-Oct 2026 (147 days, $10k/stock): k=2 +$32k, k=6 +$51k (worst day -$4.6k), k=8 +$68k (worst day -$6.2k), all 26 stocks +$159k; ~35-37% of days still red; every month positive. Oct only: k=2 +$1.1k, k=6 +$6.8k, k=8 +$9.0k. Picking by average profit instead of consistency gave bigger wins and bigger bad days (k=2 Oct -$1.5k).
 Found this session: 31 'samebar' variants (>30% of trades enter+exit in one bar, e.g. 5Q1KJZuZ XAUUSD scalper: 81% win, 0-min hold) are excluded: bar-based fills can't know stop/target order. Scramble test (change only day D after 10:00, compare D's early entries): 3kv64PEa leaks (3/6 days change), 3k4TWbWm and 6XPbhz9C do not (0/6).
Next: (1) finish pass 2 (x2 costs store) then `features build` into it and rerun T14; (2) audit the top variants for lookahead; (3) Atlas prior for T12; (4) conversion backlog.
Setup/decisions:
- Project in `strategy-selector/`; PINE_REPO_PATH=..; `src/config.setup_pinelib()` adds `$PINE_REPO_PATH/python` to sys.path. Data = Twelve Data 1m RTH (no pre-market on this plan), cache `data/cache/<SYM>/<YYYY-MM>.parquet`.
- Scope: 28 'Traded' watchlist symbols, 2025-10-01..2026-10-29 (1 year, 272 trading days). QNT, SPCX learn=false (short history).
- Bulk order: `data/wave_strategy_order.txt` (631 clean FULL strategies by Backtest Atlas realistic-fill score, from the backtest-atlas repo) and `_top250.txt` (the 250 actually run). Atlas covers only 17 of the 28 Traded symbols.
- Store `data/store.duckdb`: 750 variants x 28 symbols x 2 gates = 42,000 jobs; variant status: ok 1828, dead 6, error 8, lookahead 51. ~610 errored jobs not investigated.
- Pass 2 (`--db data/store_x2.duckdb --cost-mult 2`) was started and is PARTIAL; its trades are NOT yet size-fixed (apply the same rescale as below) and it has no features/events tables, so T14 cannot run.
Bugs found this session (both affected earlier results too):
1. Position sizing: scripts that size at % of equity ignored the fixed $10k notional (e.g. 276k IONQ shares). Fix: `run_day_trades` rescales qty/pnl/commission to cfg notional; existing store rescaled in place (unscaled backup: data/store_raw_unscaled.duckdb, gitignored).
2. Lookahead: 3kv64PEa (HTF Candle Direction) reads the current 12h candle with lookahead ON and was the "best" variant. 58 strategies with lookahead_on in Pine or lookahead=True in Python are now variants.status='lookahead' and excluded (backtest, ranker, bulk top). Other top variants (5Q1KJZuZ, 6XPbhz9C) were not audited line by line; sharpe 25 in the neutral run is suspicious.
T13 result (2026-01-02..2026-10-29, open+10, top-3, 208 test days, after fixes, lookahead variants excluded):
- Watchlist universe (26 symbols): selector +$106k on $30k allocated, sharpe-like 3.4, maxDD -47%, win 57%, 1585 trades. Best single variant chosen in-sample (6XPbhz9C|10m) +$98k, so the selector does not beat it. Rank-only -$4.3k, random -$3.6k, oracle +$996k.
- Neutral universe (QQQ + mega-caps): selector +$25k, sharpe 5.4, maxDD -6.7%, win 77%; best single (5Q1KJZuZ|15m, an XAUUSD script) +$28k. Selector < best single again.
- These are far too good: costs are tier guesses, watchlist is hindsight-curated, 1 year only, no VIX/cpi/jobs/earnings (only 1/28 symbols), and top variants are unaudited.
T14: not rerun (needs pass 2 + features in the x2 store). Old H1-2024 verdict stays FRAGILE.
Pipeline notes:
- Planning step of `bulk run` is slow (loads bars, hashes, builds ~42k job keys): minutes before the start line; the DuckDB file is locked while a run writes, so stop the run to query. Pace ~4.4 s/job/worker at 16 workers.
- Windows: mark_degenerate no longer resets status 'lookahead'. `variant.load` and `ranker` only read status='ok' variants.
Tickets T04-T12, T16, T17: unchanged, see git history of this file (adapter gates + EOD flatten, bulk runner, features, events, 8 soft regimes, ridge ranker, shrinkage variant selector with abstain, report, service layer).
Known problems: pre-market + VIX unavailable; cpi/jobs dates empty; earnings only 1/28; costs per tier are guesses; Atlas prior for T12 not built; 11 Traded symbols not in Atlas.
