# T02 Twelve Data client + cache
- 1-min bars; multi-key rotation (TWELVEDATA_API_KEYS); per-key backoff; resumable; only missing ranges; parquet per symbol/month
- Pre-market bars if plan allows (else RTH only; note in STATE.md); record plan limits + history depth
- `cli data fetch --universe|--symbols --start --end`
Accept: 2 symbols × 1 month; rerun fetches nothing; summary rows/days per symbol.
