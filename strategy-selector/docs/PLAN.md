# Plan (2–3 tickets per session)
## A Foundation
- T01 Scaffold, config, install pinelib, smoke-run an existing converted strategy
- T02 Twelve Data client (6 keys), cache, resumable
- T03 Calendar, data quality, universe coverage
## B Engine + strategy supply
- T04 Day-trade adapter around pinelib (gate, EOD flat, costs, per-day extraction)
- T05 Triage of 1022 pending Pine strategies → priority catalog
- T06 Conversion wave 1 (repeat T06.n; done in the TV repo with its skill)
## C Data for decisions
- T07 Bulk runner + DuckDB store (variant × symbol × day × gate), resumable, parallel
- T08 Day features per checkpoint
- T09 Event/news flags
- T10 Regimes
## D Selection + the product
- T11 Stock ranker ("in play")
- T12 Strategy selector (shrinkage, abstain)
- T13 `backtest --from --to`: walk-forward end-to-end, trades the picks, results + baselines
- T14 Robustness (costs, bias control, bootstrap, shuffle)
- T15 Selector v2 ML (only if justified)
## E Output
- T16 Reports (compact CLI + files)
- T17 Service layer for future frontend
Too big for one session? Split it, note in STATE.md.
