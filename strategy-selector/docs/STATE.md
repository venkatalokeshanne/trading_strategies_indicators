# STATE (rewrite each session, ≤40 lines)
Last tickets done: T01, T02, T03 (all acceptance-tested on real data)
Next ticket: T05 (triage) or T04 (adapter) — T04 first per PLAN
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
Known problems: full-universe fetch NOT run yet (70 symbols x years = many credits); do it before T07. Only AAPL/IONQ/SPCX/INFQ cached so far.
Open questions: pre-market source (T02 limitation); exact history depth + credit/min limit per key.
