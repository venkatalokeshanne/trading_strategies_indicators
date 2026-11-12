import numpy as np
import pandas as pd

from src import config


def run() -> tuple[int, float]:
    config.load_env()
    config.setup_pinelib()
    import importlib.util
    from pinelib.runner import run as pine_run
    from pinelib.symbols import SymbolInfo

    f = next((config.pine_repo() / "python/strategies").glob("7qUtuiBt-*.py"))
    spec = importlib.util.spec_from_file_location("smoke_strat", f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cls = m.BuyAtOpenSellAtCloseEveryBar
    rng = np.random.default_rng(0)
    c = 100 + np.cumsum(rng.normal(0, 0.2, 2000))
    t = pd.date_range("2024-01-02 14:30", periods=2000, freq="5min", tz="UTC").as_unit("ms").asi8
    bars = pd.DataFrame({"time": t, "open": np.r_[c[0], c[:-1]], "high": c + 0.1, "low": c - 0.1,
                         "close": c, "volume": 1e5})
    r = pine_run(cls, bars, symbol=SymbolInfo(), timeframe="5")
    tr = r.broker.closed
    return len(tr), float(sum(x.profit for x in tr))
