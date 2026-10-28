# STATE (rewrite each session, ≤40 lines)
Last tickets done: T01, T02 (T02 client verified against a fake HTTP layer only, see problems)
Next ticket: T03 (calendar, data quality, coverage) — but first run the real T02 acceptance (below)
Decisions:
- Project lives in `strategy-selector/` inside the helper repo (`trading_strategies_indicators`); PINE_REPO_PATH=.. (repo root).
- helper `python/pyproject.toml` is not pip-installable (multi-package flat layout), so `src/config.setup_pinelib()` adds `$PINE_REPO_PATH/python` to sys.path instead of `pip install -e`.
- Cache: `data/cache/<SYM>/<YYYY-MM>.parquet` (UTC `time`, OHLCV) + `coverage.json` (weekdays already requested, so rerun fetches nothing). Today is never marked covered.
- Pre-market: requested with `prepost=true`; if the plan rejects it the client falls back to RTH only and prints it.
- Universe = 70 symbols (union of 3 lists, incl. QQQ). Cost tiers in config/default.yaml are my first guess (mega/large/volatile) — review.
- Smoke: `python -m src.cli smoke` -> 999 trades on synthetic bars via the converted "Buy at open" strategy.
Known problems:
- api.twelvedata.com is blocked by this cloud sandbox's egress proxy, so real fetch was NOT run. Plan limits / history depth / pre-market availability still unknown.
- To finish T02 acceptance, run locally: `python -m src.cli data fetch --symbols AAPL,IONQ --start 2024-03-01 --end 2024-03-29` twice (2nd must fetch 0), then record plan limits here. Or allow the host in the environment's network policy.
Open questions: Twelve Data plan limits/history/pre-market.
