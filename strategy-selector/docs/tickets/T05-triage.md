# T05 Triage of pending Pine strategies
- Static scan of TradingView/strategies (1022 pending): declared/typical timeframe, uses request.security/varip/calc_on_every_tick, external libs/symbols, line count, direction, intraday & US-stock suitability, similarity dedupe
- Priority score favouring simple, intraday-capable, long/short-equity-friendly, parity-testable
- Write data/catalog.json (id, file, convertibility easy/medium/hard/skip, priority, status synced from progress.json + python/strategies); top-100 list in runs/
Accept: summary counts by convertibility; top-30 printed (id+title).
Do NOT read every script with the model.
