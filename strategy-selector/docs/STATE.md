# STATE (rewrite each session, ≤40 lines)
Last tickets done: T01-T05 (all acceptance-tested on real data)
Next ticket: T06 (conversion wave 1 — done in the TV repo with its pine-to-python skill, 2-5 scripts/session from runs/triage_top100.csv) or T07 (bulk runner)
Decisions:
- Project lives in `strategy-selector/` inside the helper repo; PINE_REPO_PATH=.. (repo root).
- helper `python/pyproject.toml` is not pip-installable, so `src/config.setup_pinelib()` adds `$PINE_REPO_PATH/python` to sys.path.
- Cache: `data/cache/<SYM>/<YYYY-MM>.parquet` (UTC `time`, OHLCV) + `coverage.json` (weekdays already requested; rerun fetches nothing). Today never marked covered.
- Twelve Data returns the NEWEST `outputsize` bars of a range, so the client pages backward (moves end_date). Found by the real run, not by mocks.
- Universe = 70 symbols (union of 3 lists incl. QQQ). Cost tiers in config/default.yaml are a first guess — review.
Twelve Data plan facts (T02):
- Pre/post-market NOT available (needs Pro) -> RTH only (09:30–15:59 ET). "premarket" checkpoint features must come from daily/prior-day data or another source.
- Auth works on 6 keys; per-minute credit limit hit while probing (client backs off 61s per key on 429).
- 1-min history reaches at least 2020-06 (AAPL), none at 2018-06 -> depth between; exact start not measured.
- Acceptance run: AAPL, IONQ 2024-03: 7799/7795 rows, 20 days each; rerun 0 requests.
T03: NYSE calendar via `exchange_calendars` (XNYS, early closes ok: 2023-11-24 = 210 min). `cli data check` -> table + data/bad_days.csv + data/coverage.csv (`learn` = days >= min_history_days=120). Flags: no_data, missing(>2%), zero_volume, dups, outside, jump(>25%/min, within day), gap(>40% overnight). Days before first bar are not judged.
Real-data findings: Twelve Data has ~1-4% missing minutes on thin days (INFQ 10-24/390); IPO-day partial sessions flagged `missing` (expected). Real run caught nothing for split-like gaps (vendor bars are split-adjusted).
T04 adapter (`src/adapter/daytrade.py`, `cli run`): subclass of the strategy; `strategy.entry/order` blocked unless bar-close >= gate and not on/after the day's penultimate bar, and entries/day < max (2); EOD = `cancel_all`+`close_all` on the penultimate bar so it fills at the OPEN of the day's last bar (15:55 for 5m) — no overnight. Bars are RTH 1m resampled to 5/10/15m aligned to 09:30, 30-day warmup before --start. Cache: data/results/<hash>.parquet keyed by script bytes, params, symbol, tf, gate, dates, costs, 1m data hash. Parallel via ProcessPoolExecutor.
Costs: $0.005/share + slippage in bps by tier (mega 1, large 2, volatile 5; ticks = bps*median price, min 1) — REVIEW these guesses. Sizing overridden to $10k cash per entry so strategies compare on one scale (strategies' own qty is ignored unless they pass explicit qty).
Real run: 3 strategies x AAPL,IONQ x gates open/open+10, Mar 2024: 12 jobs, rerun 12/12 cached, 1.2s. First run with 5-tick slippage made IONQ -38%/month — that was a cost-model artefact, fixed by the bps model.
Caveat: a gated run differs from an ungated one for strategies that track state themselves (they think they entered). Inherent to gating.
T05 triage (`src/pine/triage.py`, `cli pine triage`): static regex scan of 1053 strategies -> data/catalog.json (committed) + runs/triage_top100.csv. Status synced from progress.json python_status + python/strategies files: pending 1022, FULL 27, PARTIAL 2, NOT CONVERTIBLE 2. Pending: easy 492, medium 288, hard 235, skip 7 (dead/no entries/request.financial etc). 95 near-duplicates (5-gram Jaccard>=0.9) get priority x0.3. Priority = convertibility + intraday hints + US-market hints (-25 for crypto/forex/futures/India) + both directions + short + no request.security + has SL/TP. Heuristic: the top 100 are all US/index intraday, 45 explicit intraday, 93 both-direction. Re-run triage after each conversion wave to refresh status.
Known problems: full-universe fetch NOT run yet (70 symbols x years = many credits); do it before T07. Only AAPL/IONQ/SPCX/INFQ cached so far.
Open questions: pre-market source (T02 limitation); exact history depth + credit/min limit per key.
