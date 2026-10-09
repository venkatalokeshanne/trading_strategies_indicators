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
