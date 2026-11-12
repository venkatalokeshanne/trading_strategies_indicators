"""
pinelib — Pine Script's execution model and built-ins in Python.

A converted script::

    from pinelib import Script, ta, pmath, na, nz, div, S

    class MyStrategy(Script):
        TITLE = "EMA Cross"
        STRATEGY = dict(initial_capital=10_000, default_qty_type="percent_of_equity",
                        default_qty_value=100)

        def init(self):
            self.fast_len = self.input.int(9, "Fast")

        def on_bar(self):
            fast = ta.ema(self.close, self.fast_len)
            if ta.crossover(fast, ta.ema(self.close, 21)):
                self.strategy.entry("L", self.strategy.long)
"""

from . import color, metrics, parray, pmath, pstr, ta
from . import draw
from .broker import LONG, SHORT, StrategyConfig
from .core import NA, S, div, fixnan, fl, iff, na, nz, truthy
from .runner import RunResult, Script, run, tf_seconds
from .symbols import SymbolInfo

__all__ = [
    "Script", "run", "RunResult", "SymbolInfo", "StrategyConfig", "ta", "pmath", "color", "parray", "pstr", "draw",
    "metrics", "na", "nz", "div", "iff", "fixnan", "fl", "truthy", "S", "NA", "LONG",
    "SHORT", "tf_seconds",
]
