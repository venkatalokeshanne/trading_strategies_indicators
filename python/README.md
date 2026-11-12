# python/ — Pine-faithful engine + TradeSearch backend

| Folder | What it is |
|---|---|
| `pinelib/` | Pine Script's execution model and built-ins in Python: per-call-site state, history, `ta.*`, `request.security`, the strategy broker emulator, metrics |
| `strategies/`, `indicators/` | hand-converted scripts, one file per TradingView script, same id and slug as `TradingView/` |
| `tradesearch/` | the TradeSearcher-style backend: data, pipeline, repaint audit, scoring, search, API |
| `tests/` | every `ta` function vs an independent implementation, Pine semantics, hand-computed broker scenarios, `request.security` timing |

Design and the TradeSearcher feature map: [ARCHITECTURE.md](ARCHITECTURE.md).

```bash
cd python
pip install -e .[dev]
python -m pytest
```

A converted script:

```python
from pinelib import Script, ta

class EmaCross(Script):
    TITLE = "EMA Cross"
    STRATEGY = dict(initial_capital=10_000, default_qty_type="percent_of_equity", default_qty_value=100)

    def init(self):
        self.fast = self.input.int(9, "Fast")
        self.slow = self.input.int(21, "Slow")

    def on_bar(self):
        f, s = ta.ema(self.close, self.fast), ta.ema(self.close, self.slow)
        if ta.crossover(f, s):
            self.strategy.entry("L", self.strategy.long)
        if ta.crossunder(f, s):
            self.strategy.close("L")
```

## Verifying a conversion (`checks/`)

Every converted strategy has `checks/<id>.py`: an independent numpy re-implementation of the strategy plus a reference broker (`tools/indep.py`), run over synthetic bars with 2-6 parameter variants and compared trade by trade with the pinelib run (`python tools/run_checks.py <id>`). A conversion is marked FULL only after `lint_python`, `py_check` and the check all pass.

Reference brokers (they share no code with pinelib, they are written from Pine's documented order rules):

| function | use |
|---|---|
| `simulate` | one net position, market orders, bracket stop / target, `on_close` |
| `simulate_pyr` | pyramiding > 1 |
| `simulate_ord` | pending-order book: stop / limit entries, exits by entry id, `cancel`, `cancel_all`, `close`, `close_all`, `close_part`, `on_close`, and an optional third `orders(i, pos, info)` argument carrying the open trade (`ep`, `eb`) |

Conventions the checks rely on (all documented as `[VERIFY]` where TradingView itself was not available):
- market orders fill at the next open (the signal close with `process_orders_on_close`); an exit issued together with an entry works from the fill bar, one issued while the position is open at script time from the next bar; `close` / `close_all` are ignored when nothing is open at script time;
- `strategy.cancel(id)` removes pending entry / order / exit orders by id, **not** the market order made by `strategy.close(id)`;
- stateful `ta.*` calls are keyed per call site (a helper called from different lines is fine, a loop is not); compute `ta.cross*` unconditionally (Pine v6 `and`/`or` short-circuit, v5 does not);
- `ta.hma` rounds `sqrt(length)` (Hull's definition); `hour(time, tz)` / `minute(time, tz)` honour `tz` also without a `time` argument; `time_close` is open + period for intraday bars;
- a series stored on `self` is live: wrap it in `float()` (the lint rule P13b catches the usual forms, but not `list.append(series)`).
