# T13 `backtest --from --to` (the product)
- For each day in range: features → rank stocks → pick variant → take that variant's gated per-day trades from the store (same code path as the adapter) → aggregate. Learning window = all eligible days before that day (walk-forward); error clearly if not enough history before --from.
- Options: --checkpoint, --top-k, --neutral (neutral universe control)
- Baselines: best single variant (chosen in-sample), equal-weight all, random pick, rank-only (no strategy choice), oracle
- Outputs: ≤15-line summary (net PnL after costs, return %, Sharpe-like, max DD, win rate, % days traded, candidates considered, bias notes) + runs/<id>/{summary.json, daily.csv, trades.csv, picks.csv, equity.csv}
Accept: run on a 1-month range prints summary and files; picks verified to use only earlier days. If selector doesn't beat baselines, say so in STATE.md.
