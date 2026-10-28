# T07 Bulk runner + store
- Run every usable variant (strategy × timeframe × small param set) × symbol (learn=true) × gate; resumable; process-parallel
- DuckDB: daily_pnl(variant, symbol, date, gate, pnl, n_trades), trades, runs
- Drop degenerate variants (never trade/error); compute budget estimate printed before large runs
Accept: 3 months × 10 symbols completes; rerun no-op; query returns top/bottom variants per day.
