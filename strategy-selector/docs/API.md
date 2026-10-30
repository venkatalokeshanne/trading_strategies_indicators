# Service API (`src/service.py`) — plain functions, DataFrames/dicts, no CLI types
| function | returns |
|---|---|
| `run_backtest(d_from, d_to, checkpoint="open+10", top_k=3, neutral=False)` | summary dict (also written to `runs/<id>/`) |
| `list_runs()` | DataFrame: run_id, window, checkpoint, top_k, universe, net, sharpe, max_dd |
| `get_run(run_id="latest")` | dict: summary + daily / picks / trades / equity DataFrames |
| `get_variant_stats(gate="open+10", day=None)` | per variant: symbol_days, trades, net, win (whole store or one day) |
| `get_regime_table(day=None, top=3, gate=None)` | one day: 8 soft-regime weights per symbol; else per-regime days + best variants |
Data lives in `data/store.duckdb` (runs, trades, daily_pnl, variants, features, events) and `runs/<id>/`. A UI/FastAPI layer should only wrap these functions (add FastAPI when a frontend starts).
