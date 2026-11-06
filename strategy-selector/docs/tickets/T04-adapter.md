# T04 Day-trade adapter around pinelib
- run(script, symbol, timeframe, gate) over continuous resampled bars (warm-up included); output per-day trades and pnl
- Gate: block strategy.entry/order before gate time each day; EOD flatten (close_all on the last bar); no overnight; max entries/day
- Costs → strategy_overrides (commission, slippage ticks by liquidity tier from price/volume)
- Pre-market bars never fed to strategies (features only); strategy sees RTH bars
- Parallel per core; result cache key = (script hash, params, symbol, tf, gate, data hash)
Accept: 3 converted strategies × 2 symbols × 1 month run; per-day PnL table; second run served from cache.
Tests (justified): no entry before gate (compare vs ungated), EOD flat, cost mapping.
